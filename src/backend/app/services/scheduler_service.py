"""Background scheduling and atomic Zerodha portfolio synchronization."""
from datetime import datetime
import logging
import uuid

from apscheduler.schedulers.background import BackgroundScheduler
from kiteconnect.exceptions import TokenException

from app.database import db
from app.models import Account, Holding, Snapshot
from app.services.kite_service import KiteService
from app.services.portfolio_service import PortfolioService
from app.utils.encryption import get_encryptor


logger = logging.getLogger(__name__)


class SchedulerService:
    """Coordinate explicit and scheduled account-scoped sync batches."""

    def __init__(self, app=None):
        self.scheduler = BackgroundScheduler(timezone='Asia/Kolkata')
        self.app = None
        self._configured = False
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Attach an app without starting a worker thread."""
        self.app = app

    def start(self):
        """Configure and start the scheduler exactly once."""
        if self.scheduler.running:
            return
        if self.app is None:
            raise RuntimeError('Scheduler must be initialized with a Flask app')
        if self.app.config.get('TESTING'):
            return

        interval = self.app.config.get('SYNC_INTERVAL_HOURS', 12)
        if not self._configured:
            self.scheduler.add_job(
                func=self._sync_all_accounts_wrapper,
                trigger='interval',
                hours=interval,
                id='sync_holdings',
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
            self._configured = True
        self.scheduler.start()
        logger.info('Scheduler started. Syncing every %s hours.', interval)

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def _sync_all_accounts_wrapper(self):
        if self.app is not None:
            with self.app.app_context():
                self.sync_all_accounts()

    def sync_all_accounts(self):
        """Sync each user's family independently."""
        user_ids = [
            user_id
            for (user_id,) in (
                db.session.query(Account.user_id)
                .filter(Account.is_active.is_(True))
                .distinct()
                .all()
            )
            if user_id is not None
        ]
        results = []
        for user_id in user_ids:
            try:
                results.append(
                    self.sync_user_accounts(user_id, trigger='scheduled')
                )
            except Exception:
                logger.error('Scheduled sync failed for user %s', user_id, exc_info=True)
                db.session.rollback()
        return results

    def sync_user_accounts(self, user_id, account_id=None, trigger='manual'):
        """Run one timestamped batch for selected accounts owned by a user."""
        query = Account.query.filter_by(user_id=user_id, is_active=True)
        if account_id is not None:
            query = query.filter_by(id=account_id)
        accounts = query.order_by(Account.id.asc()).all()

        if account_id is not None and not accounts:
            raise ValueError('Account not found')
        if not accounts:
            raise ValueError('No active accounts found')

        batch_id = str(uuid.uuid4())
        batch_date = datetime.utcnow()
        synced = 0
        failed = 0
        snapshots = []
        reauth_required = []
        encryptor = get_encryptor()

        for account in accounts:
            try:
                # A savepoint ensures a database error for one account cannot
                # leak half-written holdings into another account's snapshot.
                with db.session.begin_nested():
                    snapshot, count = self.sync_account(
                        account,
                        batch_id=batch_id,
                        batch_date=batch_date,
                        trigger=trigger,
                        encryptor=encryptor,
                    )
                # Clear stale reauth flag on success
                account.needs_reauth = False
                snapshots.append(snapshot)
                synced += 1
                logger.info(
                    'Synced %s holdings for account %s',
                    count,
                    account.account_name,
                )
            except TokenException as exc:
                failed += 1
                reauth_required.append(account.id)
                account.needs_reauth = True
                logger.error(
                    'Sync failed for account %s — Kite access token expired or invalid: %s',
                    account.id, exc,
                )
                with db.session.begin_nested():
                    failed_snapshot = Snapshot(
                        account_id=account.id,
                        batch_id=batch_id,
                        snapshot_date=batch_date,
                        status='failed',
                        trigger=trigger,
                        error_message=f'Kite token expired — please re-authenticate: {exc}',
                    )
                    db.session.add(failed_snapshot)
            except Exception:
                failed += 1
                logger.error('Sync failed for account %s', account.id, exc_info=True)
                with db.session.begin_nested():
                    failed_snapshot = Snapshot(
                        account_id=account.id,
                        batch_id=batch_id,
                        snapshot_date=batch_date,
                        status='failed',
                        trigger=trigger,
                        error_message='Portfolio refresh failed',
                    )
                    db.session.add(failed_snapshot)

        db.session.commit()
        return {
            'batch_id': batch_id,
            'snapshot_date': batch_date.isoformat(),
            'accounts_total': len(accounts),
            'accounts_succeeded': synced,
            'accounts_failed': failed,
            'reauth_required': reauth_required,
            'status': (
                'completed'
                if failed == 0
                else 'failed'
                if synced == 0
                else 'partial'
            ),
            'snapshots': [snapshot.to_dict() for snapshot in snapshots],
        }

    def sync_account(
        self,
        account,
        *,
        batch_id,
        batch_date,
        trigger,
        encryptor,
    ):
        """Fetch first, then atomically replace an account's Kite assets."""
        api_key = encryptor.decrypt(account.api_key_encrypted)
        api_secret = encryptor.decrypt(account.api_secret_encrypted)
        access_token = (
            encryptor.decrypt(account.access_token_encrypted)
            if account.access_token_encrypted
            else None
        )
        if not access_token:
            raise ValueError('Account access token is missing')

        kite = KiteService(
            api_key=api_key,
            api_secret=api_secret,
            access_token=access_token,
        )
        holdings_data = kite.get_holdings()

        snapshot = PortfolioService.create_account_snapshot(
            account,
            trigger=trigger,
            batch_id=batch_id,
            snapshot_date=batch_date,
            exclude_types=('equity', 'mf'),
        )
        for data in holdings_data:
            symbol = data.get('tradingsymbol')
            if not symbol:
                continue
            holding = Holding(
                account_id=account.id,
                snapshot_id=snapshot.id,
                holding_key=str(data['holding_key'])[:255],
                tradingsymbol=str(symbol)[:100],
                instrument_type=data['instrument_type'],
                market=data.get('market', 'IN'),
                exchange=data.get('exchange'),
                isin=data.get('isin'),
                folio=data.get('folio'),
                currency=data.get('currency', 'INR'),
                quantity=data.get('quantity', 0),
                average_price=data.get('average_price', 0),
                last_price=data.get('last_price', 0),
                last_price_date=data.get('last_price_date'),
                pnl=data.get('pnl', 0),
                pnl_percentage=data.get('pnl_percentage', 0),
                day_change=data.get('day_change', 0),
                day_change_percentage=data.get('day_change_percentage', 0),
                current_value=data.get('current_value', 0),
                sector=(
                    None
                    if data['instrument_type'] == 'mf'
                    else self._get_sector_for_symbol(symbol)
                ),
                source=data.get('source'),
                valued_at=batch_date,
            )
            db.session.add(holding)

        PortfolioService.finalize_snapshot(snapshot)
        account.last_synced_at = batch_date
        return snapshot, len(holdings_data)

    @staticmethod
    def _get_sector_for_symbol(symbol):
        sector_mappings = {
            'INFY': 'Information Technology',
            'TCS': 'Information Technology',
            'WIPRO': 'Information Technology',
            'HDFCBANK': 'Banking',
            'ICICIBANK': 'Banking',
            'SBIN': 'Banking',
            'RELIANCE': 'Energy',
            'ONGC': 'Energy',
            'ITC': 'FMCG',
            'HINDUNILVR': 'FMCG',
        }
        return sector_mappings.get(symbol, 'Other')

    def trigger_manual_sync(self, user_id, account_id=None):
        return self.sync_user_accounts(
            user_id=user_id,
            account_id=account_id,
            trigger='manual',
        )
