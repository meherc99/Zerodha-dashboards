"""US-holdings spreadsheet import and price refresh service."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import logging
import re

import pandas as pd

from app.database import db
from app.models.holding import Holding
from app.models.snapshot import Snapshot
from app.services.finnhub_service import FinnhubService
from app.services.portfolio_service import PortfolioService


logger = logging.getLogger(__name__)
MAX_US_HOLDINGS = 100
DB_MONEY_MAX = Decimal('9999999999999.99')
DB_POSITION_INPUT_MAX = Decimal('99999999999999.999999')


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


class USHoldingsService:
    """Manage imported US positions without mutating historical snapshots."""

    def __init__(self, price_service=None):
        self._price_service = price_service

    @property
    def price_service(self):
        if self._price_service is None:
            self._price_service = FinnhubService()
        return self._price_service

    def parse_excel_file(self, file_path):
        df = pd.read_excel(file_path, nrows=MAX_US_HOLDINGS + 1)
        if len(df.index) > MAX_US_HOLDINGS:
            raise ValueError(
                f'A US-holdings workbook may contain at most '
                f'{MAX_US_HOLDINGS} positions'
            )
        required = {'Symbol', 'Quantity', 'Average Price'}
        missing = sorted(required - set(df.columns))
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        holdings = []
        seen_symbols = set()
        errors = []
        for index, row in df.iterrows():
            row_number = int(index) + 2
            if row.isna().all():
                continue
            try:
                if pd.isna(row['Symbol']):
                    raise ValueError('Symbol is required')
                symbol = str(row['Symbol']).strip().upper()
                quantity = _decimal(row['Quantity'])
                average_price = _decimal(row['Average Price'])
                if not 1 <= len(symbol) <= 32 or not re.fullmatch(
                    r'[A-Z0-9.-]+',
                    symbol,
                ):
                    raise ValueError('Symbol must use 1-32 ticker characters')
                if quantity <= 0:
                    raise ValueError('Quantity must be positive')
                if average_price <= 0:
                    raise ValueError('Average Price must be positive')
                if (
                    not _fits_decimal(
                        quantity,
                        DB_POSITION_INPUT_MAX,
                        6,
                    )
                    or not _fits_decimal(
                        average_price,
                        DB_POSITION_INPUT_MAX,
                        6,
                    )
                    or quantity * average_price > DB_MONEY_MAX
                ):
                    raise ValueError(
                        'Position exceeds database precision'
                    )
                if symbol in seen_symbols:
                    raise ValueError(
                        f'Duplicate Symbol {symbol}'
                    )

                purchase_date = None
                if 'Purchase Date' in df.columns and not pd.isna(
                    row['Purchase Date']
                ):
                    parsed_date = pd.to_datetime(
                        row['Purchase Date'],
                        errors='raise',
                    )
                    if pd.isna(parsed_date):
                        raise ValueError('Purchase Date is invalid')
                    purchase_date = parsed_date.date()

                seen_symbols.add(symbol)
                holdings.append(
                    {
                        'symbol': symbol,
                        'quantity': quantity,
                        'average_price': average_price,
                        'purchase_date': purchase_date,
                        'source_row': int(index) + 2,
                    }
                )
            except (ValueError, TypeError) as error:
                errors.append(f'Row {row_number}: {error}')

        if errors:
            suffix = f' ({len(errors)} invalid rows)' if len(errors) > 1 else ''
            raise ValueError(f'Workbook validation failed{suffix}: {errors[0]}')

        if not holdings:
            raise ValueError('The spreadsheet contains no holdings')
        return holdings

    def fetch_current_prices(self, symbols):
        return self.price_service.get_quotes_batch(sorted(set(symbols)))

    def _prices_or_empty(self, symbols, fetch_prices):
        if not fetch_prices:
            return {}
        try:
            return self.fetch_current_prices(symbols)
        except Exception:
            logger.warning(
                'Live US prices unavailable; imported positions remain '
                'valued at cost',
            )
            return {}

    def create_holdings(self, account, parsed_holdings, fetch_prices=True):
        prices = self._prices_or_empty(
            [holding['symbol'] for holding in parsed_holdings],
            fetch_prices,
        )
        now = datetime.utcnow()
        snapshot = PortfolioService.create_account_snapshot(
            account,
            trigger='us_upload',
            snapshot_date=now,
            exclude_types=('us_equity',),
        )

        created = []
        for data in parsed_holdings:
            symbol = data['symbol']
            quote = prices.get(symbol, {})
            has_live_price = 'current_price' in quote
            last_price = _decimal(
                quote['current_price']
                if has_live_price
                else data['average_price']
            )
            quantity = data['quantity']
            average_price = data['average_price']
            current_value = quantity * last_price
            invested = quantity * average_price
            pnl = current_value - invested

            holding = Holding(
                account_id=account.id,
                snapshot_id=snapshot.id,
                holding_key=f'us_equity:US:{symbol}',
                tradingsymbol=symbol[:100],
                exchange='US',
                instrument_type='us_equity',
                market='US',
                currency='USD',
                quantity=quantity,
                average_price=average_price,
                last_price=last_price,
                last_price_date=date.today() if has_live_price else None,
                current_value=current_value,
                pnl=pnl,
                pnl_percentage=pnl / invested * 100 if invested else 0,
                day_change=_decimal(quote.get('change', 0)),
                day_change_percentage=_decimal(quote.get('change_percent', 0)),
                purchase_date=data.get('purchase_date'),
                sector='Other',
                source='finnhub' if has_live_price else 'upload_us_at_cost',
                valued_at=now,
            )
            db.session.add(holding)
            created.append(holding)

        PortfolioService.finalize_snapshot(snapshot)
        db.session.commit()
        return created

    def refresh_prices(self, account):
        previous = (
            Snapshot.query.filter_by(account_id=account.id, status='completed')
            .order_by(Snapshot.snapshot_date.desc())
            .first()
        )
        us_holdings = (
            [holding for holding in previous.holdings if holding.instrument_type == 'us_equity']
            if previous
            else []
        )
        if not us_holdings:
            return 0

        symbols = sorted({
            holding.tradingsymbol
            for holding in us_holdings
        })
        prices = self.fetch_current_prices(symbols)
        unavailable = [
            symbol
            for symbol in symbols
            if not isinstance(prices.get(symbol), dict)
            or 'current_price' not in prices[symbol]
        ]
        if unavailable:
            # A refresh is an all-or-nothing valuation event. Publishing a new
            # snapshot with silently carried-forward prices would make a
            # provider outage look like a successful market-data refresh.
            raise RuntimeError(
                'Live prices are unavailable for one or more US holdings'
            )

        now = datetime.utcnow()
        snapshot = PortfolioService.create_account_snapshot(
            account,
            trigger='us_refresh',
            snapshot_date=now,
            exclude_types=('us_equity',),
        )

        updated = 0
        for old in us_holdings:
            quote = prices.get(old.tradingsymbol, {})
            last_price = _decimal(quote.get('current_price', old.last_price))
            quantity = _decimal(old.quantity)
            average_price = _decimal(old.average_price)
            current_value = quantity * last_price
            invested = quantity * average_price
            pnl = current_value - invested
            has_live_price = True
            db.session.add(
                Holding(
                    account_id=account.id,
                    snapshot_id=snapshot.id,
                    holding_key=old.holding_key,
                    tradingsymbol=old.tradingsymbol,
                    exchange=old.exchange,
                    instrument_type=old.instrument_type,
                    market=old.market,
                    currency='USD',
                    quantity=quantity,
                    average_price=average_price,
                    last_price=last_price,
                    last_price_date=date.today() if has_live_price else old.last_price_date,
                    current_value=current_value,
                    pnl=pnl,
                    pnl_percentage=pnl / invested * 100 if invested else 0,
                    day_change=_decimal(quote.get('change', old.day_change)),
                    day_change_percentage=_decimal(
                        quote.get('change_percent', old.day_change_percentage)
                    ),
                    purchase_date=old.purchase_date,
                    sector=old.sector,
                    source='finnhub' if has_live_price else old.source,
                    valued_at=now if has_live_price else old.valued_at,
                )
            )
            updated += 1

        PortfolioService.finalize_snapshot(snapshot)
        db.session.commit()
        return updated
