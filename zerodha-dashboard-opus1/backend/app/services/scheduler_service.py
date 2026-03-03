"""
Background scheduler service for automated data syncing.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import logging
from app.database import db
from app.models import Account, Holding, Snapshot, PortfolioTimeseries, SectorAllocation
from app.services.kite_service import KiteService
from app.services.portfolio_service import PortfolioService
from app.utils.encryption import get_encryptor

logger = logging.getLogger(__name__)


class SchedulerService:
    """Background job scheduler for periodic portfolio syncing"""

    def __init__(self, app=None):
        """Initialize scheduler"""
        self.scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
        self.app = None

        if app:
            self.init_app(app)

    def init_app(self, app):
        """
        Initialize scheduler with Flask app context.

        Args:
            app: Flask application instance
        """
        self.app = app

        # Get sync interval from config
        sync_interval_hours = app.config.get('SYNC_INTERVAL_HOURS', 12)

        # Add sync job
        self.scheduler.add_job(
            func=self._sync_all_accounts_wrapper,
            trigger='interval',
            hours=sync_interval_hours,
            id='sync_holdings',
            replace_existing=True,
            max_instances=1  # Prevent overlapping runs
        )

        # Start scheduler
        self.scheduler.start()
        logger.info(f"Scheduler started. Syncing every {sync_interval_hours} hours.")

        # Register shutdown
        import atexit
        atexit.register(lambda: self.scheduler.shutdown())

    def _sync_all_accounts_wrapper(self):
        """Wrapper to sync all accounts with Flask app context"""
        if self.app:
            with self.app.app_context():
                self.sync_all_accounts()

    def sync_all_accounts(self):
        """
        Sync holdings for all active accounts.
        This is the main background job that runs every 12 hours.
        """
        logger.info("Starting scheduled sync for all accounts...")

        try:
            # Get all active accounts
            accounts = Account.query.filter_by(is_active=True).all()

            if not accounts:
                logger.warning("No active accounts found to sync")
                return

            # Create a new snapshot for this sync
            snapshot = Snapshot(
                snapshot_date=datetime.utcnow(),
                total_holdings=0,
                total_investment=0,
                current_value=0,
                total_pnl=0,
                total_pnl_percentage=0
            )
            db.session.add(snapshot)
            db.session.flush()  # Get snapshot ID

            encryptor = get_encryptor()
            total_synced = 0

            # Sync each account
            for account in accounts:
                try:
                    synced_count = self.sync_account(account, snapshot, encryptor)
                    total_synced += synced_count
                except Exception as e:
                    logger.error(f"Error syncing account {account.account_name}: {e}")
                    continue

            # Update snapshot totals
            self._update_snapshot_totals(snapshot)

            db.session.commit()

            logger.info(f"Sync completed. Total holdings synced: {total_synced}")

        except Exception as e:
            logger.error(f"Error during scheduled sync: {e}")
            db.session.rollback()
            raise

    def sync_account(self, account: Account, snapshot: Snapshot, encryptor) -> int:
        """
        Sync holdings for a single account.

        Args:
            account: Account object
            snapshot: Snapshot object
            encryptor: Encryption utility instance

        Returns:
            Number of holdings synced
        """
        logger.info(f"Syncing account: {account.account_name}")

        try:
            # Decrypt credentials
            api_key = encryptor.decrypt(account.api_key_encrypted)
            api_secret = encryptor.decrypt(account.api_secret_encrypted)
            access_token = encryptor.decrypt(account.access_token_encrypted) if account.access_token_encrypted else None

            if not access_token:
                logger.warning(f"No access token for account {account.account_name}. Skipping.")
                return 0

            # Initialize Kite service
            kite = KiteService(api_key=api_key, api_secret=api_secret, access_token=access_token)

            # Fetch holdings
            holdings_data = kite.get_holdings()

            # Store holdings in database
            holdings_count = 0
            for holding_data in holdings_data:
                holding = Holding(
                    account_id=account.id,
                    snapshot_id=snapshot.id,
                    tradingsymbol=holding_data.get('tradingsymbol'),
                    instrument_type=holding_data.get('instrument_type'),
                    exchange=holding_data.get('exchange'),
                    isin=holding_data.get('isin'),
                    quantity=holding_data.get('quantity', 0),
                    average_price=holding_data.get('average_price', 0),
                    last_price=holding_data.get('last_price', 0),
                    pnl=holding_data.get('pnl', 0),
                    pnl_percentage=holding_data.get('pnl_percentage', 0),
                    day_change=holding_data.get('day_change', 0),
                    day_change_percentage=holding_data.get('day_change_percentage', 0),
                    current_value=holding_data.get('current_value', 0),
                    sector=self._get_sector_for_symbol(holding_data.get('tradingsymbol'))
                )

                db.session.add(holding)
                holdings_count += 1

            # Create portfolio timeseries entry
            account_holdings = Holding.query.filter_by(
                account_id=account.id,
                snapshot_id=snapshot.id
            ).all()

            summary = PortfolioService.calculate_portfolio_summary(account_holdings)

            timeseries = PortfolioTimeseries(
                account_id=account.id,
                snapshot_id=snapshot.id,
                date=snapshot.snapshot_date,
                total_value=summary['current_value'],
                invested_value=summary['total_investment'],
                pnl=summary['total_pnl'],
                pnl_percentage=summary['total_pnl_percentage'],
                day_change=summary['day_change'],
                holdings_count=summary['total_holdings']
            )
            db.session.add(timeseries)

            # Create sector allocations
            sector_breakdown = PortfolioService.calculate_sector_breakdown(account_holdings)
            for sector_data in sector_breakdown:
                sector_alloc = SectorAllocation(
                    snapshot_id=snapshot.id,
                    account_id=account.id,
                    sector=sector_data['sector'],
                    allocation_percentage=sector_data['allocation_percentage'],
                    total_value=sector_data['total_value'],
                    pnl=sector_data['pnl']
                )
                db.session.add(sector_alloc)

            # Update account's last_synced_at
            account.last_synced_at = datetime.utcnow()

            logger.info(f"Synced {holdings_count} holdings for {account.account_name}")
            return holdings_count

        except Exception as e:
            logger.error(f"Error syncing account {account.account_name}: {e}")
            raise

    def _update_snapshot_totals(self, snapshot: Snapshot):
        """Update snapshot with aggregated totals from all accounts"""
        all_holdings = Holding.query.filter_by(snapshot_id=snapshot.id).all()

        summary = PortfolioService.calculate_portfolio_summary(all_holdings)

        snapshot.total_holdings = summary['total_holdings']
        snapshot.total_investment = summary['total_investment']
        snapshot.current_value = summary['current_value']
        snapshot.total_pnl = summary['total_pnl']
        snapshot.total_pnl_percentage = summary['total_pnl_percentage']

    def _get_sector_for_symbol(self, symbol: str) -> str:
        """
        Get sector classification for a symbol.
        This is a simplified version. In production, you'd maintain a mapping or use an API.

        Args:
            symbol: Trading symbol

        Returns:
            Sector name
        """
        # Simple sector mapping (expand this based on your needs)
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

    def trigger_manual_sync(self, account_id: int = None):
        """
        Trigger manual sync for specific account or all accounts.

        Args:
            account_id: Optional account ID. If None, syncs all accounts.
        """
        logger.info(f"Manual sync triggered for account {account_id or 'all'}")

        if account_id:
            account = Account.query.get(account_id)
            if not account:
                raise ValueError(f"Account {account_id} not found")

            snapshot = Snapshot(snapshot_date=datetime.utcnow())
            db.session.add(snapshot)
            db.session.flush()

            encryptor = get_encryptor()
            self.sync_account(account, snapshot, encryptor)
            self._update_snapshot_totals(snapshot)
            db.session.commit()
        else:
            self.sync_all_accounts()

        logger.info("Manual sync completed")
