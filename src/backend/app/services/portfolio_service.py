"""Portfolio calculations and account-scoped snapshot helpers."""
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Dict, Iterable, List, Optional, Sequence
import uuid

from sqlalchemy import and_, func, update

from app.database import db
from app.models import (
    Account,
    Holding,
    PortfolioTimeseries,
    SectorAllocation,
    Snapshot,
)


ZERO = Decimal('0')
DB_MONEY_MAX = Decimal('9999999999999.99')
DB_PRICE_MAX = Decimal('99999999999999.999999')
DB_PERCENT_MAX = Decimal('999999.99')
DB_RATE_MAX = Decimal('999.9999')
HOLDING_COPY_FIELDS = (
    'holding_key',
    'tradingsymbol',
    'instrument_type',
    'market',
    'exchange',
    'isin',
    'folio',
    'currency',
    'quantity',
    'average_price',
    'last_price',
    'last_price_date',
    'pnl',
    'pnl_percentage',
    'day_change',
    'day_change_percentage',
    'current_value',
    'purchase_date',
    'maturity_date',
    'interest_rate',
    'sector',
    'source',
    'valued_at',
)


def _decimal(value) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError('Portfolio values must be finite')
    return result


def _fits_numeric(value, maximum, decimal_places):
    """Check the value after the database column's normal rounding."""
    try:
        quantum = Decimal('1').scaleb(-decimal_places)
        rounded = _decimal(value).quantize(
            quantum,
            rounding=ROUND_HALF_UP,
        )
        return abs(rounded) <= maximum
    except (InvalidOperation, ValueError):
        return False


class PortfolioService:
    """Service for portfolio calculations and tenant-safe current views."""

    @staticmethod
    def calculate_portfolio_summary(holdings: Iterable[Holding]) -> Dict:
        """Summarize holdings without ever mixing currencies."""
        holdings = list(holdings)
        groups = {}

        for holding in holdings:
            currency = (holding.currency or 'INR').upper()
            group = groups.setdefault(
                currency,
                {
                    'currency': currency,
                    'total_holdings': 0,
                    'total_investment': ZERO,
                    'current_value': ZERO,
                    'total_pnl': ZERO,
                    'day_change': ZERO,
                },
            )
            quantity = _decimal(holding.quantity)
            investment = quantity * _decimal(holding.average_price)
            current_value = (
                _decimal(holding.current_value)
                if holding.current_value is not None
                else quantity * _decimal(holding.last_price)
            )

            group['total_holdings'] += 1
            group['total_investment'] += investment
            group['current_value'] += current_value
            group['total_pnl'] += current_value - investment
            # Kite and Finnhub day_change values are per-unit price changes.
            group['day_change'] += quantity * _decimal(holding.day_change)

        by_currency = {}
        for currency, group in groups.items():
            invested = group['total_investment']
            pnl_percentage = group['total_pnl'] / invested * 100 if invested else ZERO
            by_currency[currency] = {
                'currency': currency,
                'total_holdings': group['total_holdings'],
                'total_investment': round(float(invested), 2),
                'current_value': round(float(group['current_value']), 2),
                'total_pnl': round(float(group['total_pnl']), 2),
                'total_pnl_percentage': round(float(pnl_percentage), 2),
                'day_change': round(float(group['day_change']), 2),
            }

        base = {
            'total_holdings': len(holdings),
            'by_currency': by_currency,
        }
        if not by_currency:
            return {
                **base,
                'currency': None,
                'total_investment': 0,
                'current_value': 0,
                'total_pnl': 0,
                'total_pnl_percentage': 0,
                'day_change': 0,
            }

        if len(by_currency) == 1:
            only = next(iter(by_currency.values()))
            return {**base, **only, 'total_holdings': len(holdings)}

        # Legacy scalar totals are intentionally unavailable for mixed currency
        # selections.  A caller must choose an explicit FX conversion policy.
        return {
            **base,
            'currency': 'MIXED',
            'total_investment': None,
            'current_value': None,
            'total_pnl': None,
            'total_pnl_percentage': None,
            'day_change': None,
        }

    @staticmethod
    def latest_snapshot_query(
        user_id: int,
        account_ids: Optional[Sequence[int]] = None,
    ):
        """Return a query selecting each owned account's latest good snapshot."""
        latest_dates = (
            db.session.query(
                Snapshot.account_id.label('account_id'),
                func.max(Snapshot.snapshot_date).label('snapshot_date'),
            )
            .join(Account, Account.id == Snapshot.account_id)
            .filter(
                Account.user_id == user_id,
                Account.is_active.is_(True),
                Snapshot.status == 'completed',
            )
        )
        if account_ids:
            latest_dates = latest_dates.filter(Snapshot.account_id.in_(account_ids))
        latest_dates = latest_dates.group_by(Snapshot.account_id).subquery()

        return Snapshot.query.join(
            latest_dates,
            and_(
                Snapshot.account_id == latest_dates.c.account_id,
                Snapshot.snapshot_date == latest_dates.c.snapshot_date,
            ),
        )
    @staticmethod
    def get_latest_holdings(
        user_id: int,
        account_ids: Optional[Sequence[int]] = None,
    ) -> List[Holding]:
        snapshot_ids = [
            snapshot.id
            for snapshot in PortfolioService.latest_snapshot_query(
                user_id, account_ids
            ).all()
        ]
        if not snapshot_ids:
            return []
        return (
            Holding.query.join(Account, Account.id == Holding.account_id)
            .filter(
                Holding.snapshot_id.in_(snapshot_ids),
                Account.user_id == user_id,
            )
            .all()
        )

    @staticmethod
    def aggregate_accounts(
        user_id: int,
        account_ids: Optional[Sequence[int]] = None,
    ) -> Dict:
        holdings = PortfolioService.get_latest_holdings(user_id, account_ids)
        summary = PortfolioService.calculate_portfolio_summary(holdings)
        summary['holdings'] = [holding.to_dict() for holding in holdings]
        return summary

    @staticmethod
    def create_account_snapshot(
        account: Account,
        *,
        trigger: str,
        batch_id: Optional[str] = None,
        snapshot_date: Optional[datetime] = None,
        exclude_types: Sequence[str] = (),
        copy_previous: bool = True,
    ) -> Snapshot:
        """Create an immutable account snapshot, optionally carrying data forward."""
        # Incrementing the owning row serializes every snapshot writer for this
        # account. PostgreSQL locks the row; SQLite acquires its write lock
        # before we read/copy the predecessor. Concurrent Kite, US, and FD
        # updates therefore cannot both derive from the same stale snapshot.
        db.session.execute(
            update(Account)
            .where(Account.id == account.id)
            .values(portfolio_version=Account.portfolio_version + 1)
        )

        snapshot = Snapshot(
            account_id=account.id,
            batch_id=batch_id or str(uuid.uuid4()),
            snapshot_date=snapshot_date or datetime.utcnow(),
            status='running',
            trigger=trigger,
        )
        db.session.add(snapshot)
        db.session.flush()

        if not copy_previous:
            return snapshot

        previous = (
            Snapshot.query.filter(
                Snapshot.account_id == account.id,
                Snapshot.status == 'completed',
                Snapshot.id != snapshot.id,
            )
            .order_by(Snapshot.snapshot_date.desc())
            .first()
        )
        if not previous:
            return snapshot

        excluded = set(exclude_types)
        for old_holding in previous.holdings:
            if old_holding.instrument_type in excluded:
                continue
            values = {
                field: getattr(old_holding, field)
                for field in HOLDING_COPY_FIELDS
            }
            db.session.add(
                Holding(
                    account_id=account.id,
                    snapshot_id=snapshot.id,
                    **values,
                )
            )
        return snapshot

    @staticmethod
    def finalize_snapshot(snapshot: Snapshot) -> Dict:
        """Persist account totals, currency time series, and sector allocations."""
        if snapshot.id is None:
            db.session.flush([snapshot])

        pending_holdings = [
            value
            for value in db.session.new
            if (
                isinstance(value, Holding)
                and value.account_id == snapshot.account_id
                and value.snapshot_id == snapshot.id
            )
        ]
        with db.session.no_autoflush:
            holdings = Holding.query.filter_by(
                account_id=snapshot.account_id,
                snapshot_id=snapshot.id,
            ).all()
        holdings.extend(pending_holdings)
        PortfolioService._validate_snapshot_numeric_bounds(holdings)
        summary = PortfolioService.calculate_portfolio_summary(holdings)
        sectors = PortfolioService.calculate_sector_breakdown(holdings)

        snapshot.total_holdings = summary['total_holdings']
        snapshot.total_investment = summary['total_investment']
        snapshot.current_value = summary['current_value']
        snapshot.total_pnl = summary['total_pnl']
        snapshot.total_pnl_percentage = summary['total_pnl_percentage']
        snapshot.currency = summary['currency']
        snapshot.status = 'completed'
        snapshot.error_message = None
        db.session.flush()

        current_currencies = set(summary['by_currency'])
        historical_currencies = {
            currency
            for (currency,) in (
                db.session.query(PortfolioTimeseries.currency)
                .filter(
                    PortfolioTimeseries.account_id == snapshot.account_id
                )
                .distinct()
                .all()
            )
            if currency
        }
        # Normalize to the start of the UTC day so that multiple syncs on the
        # same calendar day update a single authoritative row rather than
        # scattering many intra-day rows.  The unique constraint
        # (account_id, date, currency) then enforces exactly one data-point
        # per account-day-currency combination.
        ts_date = snapshot.snapshot_date.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        # An absent currency is a state transition, not "no update". Emit a
        # zero tombstone so family history stops carrying a sold/removed
        # position forever. Using every historical currency also repairs the
        # next snapshot after an older application version omitted the first
        # zero event.
        for currency in sorted(current_currencies | historical_currencies):
            currency_summary = summary['by_currency'].get(
                currency,
                {
                    'currency': currency,
                    'current_value': 0,
                    'total_investment': 0,
                    'total_pnl': 0,
                    'total_pnl_percentage': 0,
                    'day_change': 0,
                    'total_holdings': 0,
                },
            )
            # Upsert: update the existing row for this day if present, otherwise
            # insert a fresh one.  The no_autoflush block prevents SQLAlchemy
            # from flushing pending holdings while we query, which would cause
            # premature constraint checks.
            with db.session.no_autoflush:
                existing_ts = PortfolioTimeseries.query.filter_by(
                    account_id=snapshot.account_id,
                    date=ts_date,
                    currency=currency,
                ).first()
            if existing_ts is not None:
                existing_ts.snapshot_id = snapshot.id
                existing_ts.total_value = currency_summary['current_value']
                existing_ts.invested_value = currency_summary['total_investment']
                existing_ts.pnl = currency_summary['total_pnl']
                existing_ts.pnl_percentage = currency_summary['total_pnl_percentage']
                existing_ts.day_change = currency_summary['day_change']
                existing_ts.holdings_count = currency_summary['total_holdings']
            else:
                db.session.add(
                    PortfolioTimeseries(
                        account_id=snapshot.account_id,
                        snapshot_id=snapshot.id,
                        date=ts_date,
                        currency=currency,
                        total_value=currency_summary['current_value'],
                        invested_value=currency_summary['total_investment'],
                        pnl=currency_summary['total_pnl'],
                        pnl_percentage=currency_summary['total_pnl_percentage'],
                        day_change=currency_summary['day_change'],
                        holdings_count=currency_summary['total_holdings'],
                    )
                )

        for sector in sectors:
            db.session.add(
                SectorAllocation(
                    snapshot_id=snapshot.id,
                    account_id=snapshot.account_id,
                    currency=sector['currency'],
                    sector=sector['sector'],
                    allocation_percentage=sector['allocation_percentage'],
                    total_value=sector['total_value'],
                    pnl=sector['pnl'],
                )
            )
        return summary

    @staticmethod
    def _validate_snapshot_numeric_bounds(holdings):
        """Fail before flushing values that cannot fit the portfolio schema."""
        aggregate = {}
        sectors = {}
        for holding in holdings:
            numeric_fields = (
                (holding.quantity, DB_PRICE_MAX, 6),
                (holding.average_price, DB_PRICE_MAX, 6),
                (holding.last_price, DB_PRICE_MAX, 6),
                (holding.current_value, DB_MONEY_MAX, 2),
                (holding.pnl, DB_MONEY_MAX, 2),
                (holding.day_change, DB_MONEY_MAX, 2),
                (holding.pnl_percentage, DB_PERCENT_MAX, 2),
                (
                    holding.day_change_percentage,
                    DB_PERCENT_MAX,
                    2,
                ),
                (holding.interest_rate, DB_RATE_MAX, 4),
            )
            if any(
                value is not None
                and not _fits_numeric(value, maximum, places)
                for value, maximum, places in numeric_fields
            ):
                raise ValueError(
                    'A portfolio holding exceeds database precision'
                )

            currency = (holding.currency or 'INR').upper()
            values = aggregate.setdefault(
                currency,
                {
                    'investment': ZERO,
                    'current': ZERO,
                    'pnl': ZERO,
                    'day_change': ZERO,
                },
            )
            quantity = _decimal(holding.quantity)
            investment = quantity * _decimal(holding.average_price)
            current = (
                _decimal(holding.current_value)
                if holding.current_value is not None
                else quantity * _decimal(holding.last_price)
            )
            values['investment'] += investment
            values['current'] += current
            values['pnl'] += current - investment
            values['day_change'] += (
                quantity * _decimal(holding.day_change)
            )

            sector_key = (currency, holding.sector or 'Other')
            sector_values = sectors.setdefault(
                sector_key,
                {'current': ZERO, 'pnl': ZERO},
            )
            sector_values['current'] += current
            sector_values['pnl'] += _decimal(holding.pnl)

        aggregate_values = [
            value
            for totals in aggregate.values()
            for value in totals.values()
        ]
        sector_values = [
            value
            for totals in sectors.values()
            for value in totals.values()
        ]
        if any(
            not _fits_numeric(value, DB_MONEY_MAX, 2)
            for value in aggregate_values + sector_values
        ):
            raise ValueError(
                'Portfolio aggregate exceeds database precision'
            )

    @staticmethod
    def calculate_sector_breakdown(holdings: Iterable[Holding]) -> List[Dict]:
        """Calculate allocation within each currency, never across currencies."""
        holdings = list(holdings)
        totals = {}
        sector_data = {}
        for holding in holdings:
            currency = (holding.currency or 'INR').upper()
            value = _decimal(holding.current_value)
            totals[currency] = totals.get(currency, ZERO) + value
            key = (currency, holding.sector or 'Other')
            data = sector_data.setdefault(
                key,
                {
                    'currency': currency,
                    'sector': key[1],
                    'total_value': ZERO,
                    'pnl': ZERO,
                    'holdings_count': 0,
                },
            )
            data['total_value'] += value
            data['pnl'] += _decimal(holding.pnl)
            data['holdings_count'] += 1

        result = []
        for (currency, _sector), data in sector_data.items():
            total = totals[currency]
            allocation = data['total_value'] / total * 100 if total else ZERO
            result.append(
                {
                    **data,
                    'total_value': round(float(data['total_value']), 2),
                    'pnl': round(float(data['pnl']), 2),
                    'allocation_percentage': round(float(allocation), 2),
                }
            )
        return sorted(
            result,
            key=lambda item: (item['currency'], -item['allocation_percentage']),
        )

    @staticmethod
    def get_top_performers(holdings: Iterable[Holding], limit: int = 5) -> List[Dict]:
        sorted_holdings = sorted(
            holdings,
            key=lambda holding: _decimal(holding.pnl_percentage),
            reverse=True,
        )
        return [holding.to_dict() for holding in sorted_holdings[:limit]]

    @staticmethod
    def get_worst_performers(holdings: Iterable[Holding], limit: int = 5) -> List[Dict]:
        sorted_holdings = sorted(
            holdings,
            key=lambda holding: _decimal(holding.pnl_percentage),
        )
        return [holding.to_dict() for holding in sorted_holdings[:limit]]

    @staticmethod
    def get_portfolio_allocation(holdings: Iterable[Holding]) -> List[Dict]:
        """Return per-currency instrument allocation."""
        holdings = list(holdings)
        totals = {}
        for holding in holdings:
            currency = (holding.currency or 'INR').upper()
            totals[currency] = totals.get(currency, ZERO) + _decimal(
                holding.current_value
            )

        allocation = []
        for holding in holdings:
            currency = (holding.currency or 'INR').upper()
            value = _decimal(holding.current_value)
            total = totals[currency]
            allocation.append(
                {
                    'tradingsymbol': holding.tradingsymbol,
                    'currency': currency,
                    'value': round(float(value), 2),
                    'percentage': round(
                        float(value / total * 100) if total else 0,
                        2,
                    ),
                }
            )
        return sorted(
            allocation,
            key=lambda item: (item['currency'], -item['percentage']),
        )
