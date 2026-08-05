"""Fixed-deposit import and valuation service."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import logging

import pandas as pd

from app.database import db
from app.models.holding import Holding
from app.models.snapshot import Snapshot
from app.services.portfolio_service import PortfolioService


logger = logging.getLogger(__name__)
DB_MONEY_MAX = Decimal('9999999999999.99')
MONEY_QUANTUM = Decimal('0.01')


def _fits_decimal(value, maximum, decimal_places):
    quantum = Decimal('1').scaleb(-decimal_places)
    try:
        return abs(value) <= maximum and value == value.quantize(quantum)
    except InvalidOperation:
        return False


def _decimal(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError('Expected a valid number')
    if not result.is_finite():
        raise ValueError('Expected a finite number')
    return result


def _date(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = pd.to_datetime(value, errors='raise')
    if pd.isna(parsed):
        return None
    return parsed.date()


class FDService:
    """Manage fixed deposits as first-class INR holdings."""

    @staticmethod
    def calculate_fd_returns(
        investment_amount,
        investment_date,
        interest_rate,
        maturity_date=None,
        valuation_date=None,
    ):
        """Accrue simple interest only through today or maturity, whichever is first."""
        principal = _decimal(investment_amount)
        rate = _decimal(interest_rate)
        invested_on = _date(investment_date)
        maturity = _date(maturity_date)
        if principal <= 0:
            raise ValueError('Investment amount must be positive')
        if not _fits_decimal(principal, DB_MONEY_MAX, 2):
            raise ValueError('Investment amount exceeds database precision')
        if rate < 0 or rate > 100:
            raise ValueError('Interest rate must be between 0 and 100')
        if not _fits_decimal(rate, Decimal('999.9999'), 4):
            raise ValueError('Interest rate exceeds database precision')
        if invested_on is None:
            raise ValueError('Investment date is required')
        if maturity and maturity < invested_on:
            raise ValueError('Maturity date cannot precede investment date')
        valued_on = _date(valuation_date) or date.today()
        accrual_end = min(valued_on, maturity) if maturity else valued_on
        days_elapsed = max((accrual_end - invested_on).days, 0)
        years_elapsed = Decimal(days_elapsed) / Decimal('365')
        interest = (
            principal * rate * years_elapsed / Decimal('100')
        ).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        current_value = (principal + interest).quantize(
            MONEY_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
        if (
            not _fits_decimal(interest, DB_MONEY_MAX, 2)
            or not _fits_decimal(current_value, DB_MONEY_MAX, 2)
        ):
            raise ValueError(
                'Fixed-deposit value exceeds database precision'
            )
        return {
            'days_elapsed': days_elapsed,
            'years_elapsed': round(float(years_elapsed), 4),
            'interest_earned': interest,
            'current_value': current_value,
            'valuation_date': accrual_end.isoformat(),
            'is_matured': bool(maturity and valued_on >= maturity),
        }

    def parse_excel_file(self, file_path):
        df = pd.read_excel(file_path, nrows=5001)
        if len(df.index) > 5000:
            raise ValueError('A fixed-deposit workbook may contain at most 5000 rows')
        required = {
            'Bank Name',
            'Investment Amount',
            'Investment Date',
            'Interest Rate',
        }
        missing = sorted(required - set(df.columns))
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        deposits = []
        errors = []
        seen_deposit_ids = set()
        for index, row in df.iterrows():
            row_number = int(index) + 2
            if row.isna().all():
                continue
            try:
                if pd.isna(row['Bank Name']):
                    raise ValueError('Bank Name is required')
                bank_name = str(row['Bank Name']).strip()
                if not 1 <= len(bank_name) <= 100:
                    raise ValueError('Bank Name must contain 1-100 characters')
                principal = _decimal(row['Investment Amount'])
                rate = _decimal(row['Interest Rate'])
                if principal <= 0:
                    raise ValueError('Investment Amount must be positive')
                if rate <= 0 or rate > 100:
                    raise ValueError('Interest Rate must be between 0 and 100')
                if not _fits_decimal(principal, DB_MONEY_MAX, 2):
                    raise ValueError(
                        'Investment Amount exceeds database precision'
                    )
                if not _fits_decimal(rate, Decimal('999.9999'), 4):
                    raise ValueError(
                        'Interest Rate exceeds database precision'
                    )
                invested_on = _date(row['Investment Date'])
                if invested_on is None:
                    raise ValueError('Investment Date is required')
                maturity = None
                if 'Maturity Date' in df.columns and not pd.isna(
                    row['Maturity Date']
                ):
                    maturity = _date(row['Maturity Date'])
                    if maturity < invested_on:
                        raise ValueError(
                            'Maturity Date cannot precede Investment Date'
                        )

                deposit_id = None
                if 'Deposit ID' in df.columns and not pd.isna(row['Deposit ID']):
                    deposit_id = str(row['Deposit ID']).strip() or None
                    if deposit_id and len(deposit_id) > 200:
                        raise ValueError(
                            'Deposit ID must contain at most 200 characters'
                        )
                    if deposit_id in seen_deposit_ids:
                        raise ValueError(f'Duplicate Deposit ID {deposit_id}')
                    if deposit_id:
                        seen_deposit_ids.add(deposit_id)

                deposits.append(
                    {
                        'bank_name': bank_name,
                        'investment_amount': principal,
                        'investment_date': invested_on,
                        'interest_rate': rate,
                        'maturity_date': maturity,
                        'deposit_id': deposit_id,
                        'source_row': int(index) + 2,
                    }
                )
            except (ValueError, TypeError) as error:
                errors.append(f'Row {row_number}: {error}')

        if errors:
            suffix = f' ({len(errors)} invalid rows)' if len(errors) > 1 else ''
            raise ValueError(f'Workbook validation failed{suffix}: {errors[0]}')

        if not deposits:
            raise ValueError('The spreadsheet contains no fixed deposits')
        return deposits

    @staticmethod
    def _holding_key(data):
        external_id = data.get('deposit_id')
        if external_id:
            return f"fd:{external_id}"[:255]
        maturity = data.get('maturity_date')
        return (
            f"fd:{data['bank_name']}:{data['investment_date']}:"
            f"{maturity or 'open'}:{data.get('source_row', 0)}"
        )[:255]

    def create_fd_holdings(self, account, parsed_fds):
        now = datetime.utcnow()
        snapshot = PortfolioService.create_account_snapshot(
            account,
            trigger='fd_upload',
            snapshot_date=now,
            exclude_types=('fd',),
        )
        created = []
        for data in parsed_fds:
            returns = self.calculate_fd_returns(
                data['investment_amount'],
                data['investment_date'],
                data['interest_rate'],
                data.get('maturity_date'),
            )
            principal = data['investment_amount']
            current_value = _decimal(returns['current_value'])
            interest = _decimal(returns['interest_earned'])
            holding = Holding(
                account_id=account.id,
                snapshot_id=snapshot.id,
                holding_key=self._holding_key(data),
                tradingsymbol=data['bank_name'][:100],
                exchange='FD',
                instrument_type='fd',
                market='IN',
                currency='INR',
                quantity=1,
                average_price=principal,
                last_price=current_value,
                last_price_date=date.fromisoformat(returns['valuation_date']),
                current_value=current_value,
                pnl=interest,
                pnl_percentage=interest / principal * 100 if principal else 0,
                day_change=0,
                day_change_percentage=0,
                purchase_date=data['investment_date'],
                maturity_date=data.get('maturity_date'),
                interest_rate=data['interest_rate'],
                sector='Fixed Deposit',
                source='upload_fd',
                valued_at=now,
            )
            db.session.add(holding)
            created.append(holding)

        PortfolioService.finalize_snapshot(snapshot)
        db.session.commit()
        return created

    def refresh_fd_values(self, account):
        previous = (
            Snapshot.query.filter_by(account_id=account.id, status='completed')
            .order_by(Snapshot.snapshot_date.desc())
            .first()
        )
        deposits = (
            [holding for holding in previous.holdings if holding.instrument_type == 'fd']
            if previous
            else []
        )
        if not deposits:
            return 0

        now = datetime.utcnow()
        snapshot = PortfolioService.create_account_snapshot(
            account,
            trigger='fd_refresh',
            snapshot_date=now,
            exclude_types=('fd',),
        )
        for old in deposits:
            returns = self.calculate_fd_returns(
                old.average_price,
                old.purchase_date,
                old.interest_rate,
                old.maturity_date,
            )
            principal = _decimal(old.average_price)
            current_value = _decimal(returns['current_value'])
            interest = _decimal(returns['interest_earned'])
            db.session.add(
                Holding(
                    account_id=account.id,
                    snapshot_id=snapshot.id,
                    holding_key=old.holding_key,
                    tradingsymbol=old.tradingsymbol,
                    exchange='FD',
                    instrument_type='fd',
                    market='IN',
                    currency='INR',
                    quantity=1,
                    average_price=principal,
                    last_price=current_value,
                    last_price_date=date.fromisoformat(returns['valuation_date']),
                    current_value=current_value,
                    pnl=interest,
                    pnl_percentage=interest / principal * 100 if principal else 0,
                    day_change=0,
                    day_change_percentage=0,
                    purchase_date=old.purchase_date,
                    maturity_date=old.maturity_date,
                    interest_rate=old.interest_rate,
                    sector='Fixed Deposit',
                    source=old.source,
                    valued_at=now,
                )
            )

        PortfolioService.finalize_snapshot(snapshot)
        db.session.commit()
        return len(deposits)
