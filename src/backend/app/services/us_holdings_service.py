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


def _decimal(value, max_decimals=6):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError('Expected a valid number')
    if not result.is_finite():
        raise ValueError('Expected a finite number')
    # Round to max_decimals to absorb binary floating-point representation noise
    # (e.g. 293.062118 read from XLS may become 293.06211800000002).
    quantum = Decimal('1').scaleb(-max_decimals)
    return result.quantize(quantum)


class USHoldingsService:
    """Manage imported US positions without mutating historical snapshots."""

    def __init__(self, price_service=None):
        self._price_service = price_service

    @property
    def price_service(self):
        if self._price_service is None:
            self._price_service = FinnhubService()
        return self._price_service

    # Alternative column names from known broker export formats (e.g. Alpaca).
    # Maps broker column name -> canonical column name.
    _COLUMN_ALIASES = {
        'stock symbol': 'Symbol',
        'ticker': 'Symbol',
        'symbol': 'Symbol',
        'qty': 'Quantity',
        'quantity': 'Quantity',
        'shares': 'Quantity',
        'avg. price ($)': 'Average Price',
        'avg price ($)': 'Average Price',
        'average price': 'Average Price',
        'average price ($)': 'Average Price',
        'avg price': 'Average Price',
        'cost basis': 'Average Price',
        'holding since': 'Purchase Date',
        'purchase date': 'Purchase Date',
        'buy date': 'Purchase Date',
        'date': 'Purchase Date',
        # Human-readable name columns (broker exports)
        'security name': 'Security Name',
        'company name': 'Security Name',
        'company': 'Security Name',
        'name': 'Security Name',
        'description': 'Security Name',
    }

    @classmethod
    def _find_header_row(cls, file_path):
        """Return the 0-based row index whose cells contain stock column headers.

        Scans up to the first 20 rows looking for a row that, after lowercasing,
        contains a known symbol-column alias. Returns 0 if none is found (treats
        the first row as the header, matching legacy behaviour).
        """
        raw = pd.read_excel(file_path, header=None, nrows=20)
        symbol_keys = {'stock symbol', 'ticker', 'symbol'}
        for i, row in raw.iterrows():
            cells = {str(v).strip().lower() for v in row if pd.notna(v)}
            if cells & symbol_keys:
                return int(i)
        return 0

    @classmethod
    def _normalise_columns(cls, df):
        """Rename columns using _COLUMN_ALIASES (case-insensitive, stripped)."""
        rename = {}
        for col in df.columns:
            key = str(col).strip().lower()
            if key in cls._COLUMN_ALIASES:
                rename[col] = cls._COLUMN_ALIASES[key]
        return df.rename(columns=rename)

    @staticmethod
    def _parse_purchase_date(value):
        """Parse a purchase-date cell that may carry a time component.

        Handles formats such as:
        - "29 Jun 2022, 10:31 PM"  (Alpaca)
        - "2022-06-29"
        - datetime / Timestamp objects
        Returns a date or None on failure.
        """
        if pd.isna(value):
            return None
        if isinstance(value, (datetime, date)):
            return value.date() if isinstance(value, datetime) else value
        text = str(value).strip()
        # Strip time portion after a comma (Alpaca format)
        if ',' in text:
            text = text.split(',')[0].strip()
        try:
            return pd.to_datetime(text, errors='raise').date()
        except Exception:
            return None

    def parse_excel_file(self, file_path):
        header_row = self._find_header_row(file_path)
        df = pd.read_excel(
            file_path,
            header=header_row,
            nrows=header_row + MAX_US_HOLDINGS + 1,
        )
        df = self._normalise_columns(df)

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
            row_number = int(index) + header_row + 2
            if row.isna().all():
                continue
            raw_symbol = row['Symbol']
            if pd.isna(raw_symbol):
                continue
            symbol = str(raw_symbol).strip().upper()
            # Skip footer/disclaimer rows — any cell whose content is clearly
            # not a stock ticker (contains spaces, colons, asterisks, or
            # exceeds 32 characters) is treated as a non-data row.
            if not re.fullmatch(r'[A-Z0-9.-]+', symbol) or len(symbol) > 32:
                continue
            try:
                quantity = _decimal(row['Quantity'])
                average_price = _decimal(row['Average Price'])
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
                if 'Purchase Date' in df.columns:
                    purchase_date = self._parse_purchase_date(
                        row['Purchase Date']
                    )

                security_name = None
                if 'Security Name' in df.columns and pd.notna(row.get('Security Name')):
                    security_name = str(row['Security Name']).strip() or None

                seen_symbols.add(symbol)
                holdings.append(
                    {
                        'symbol': symbol,
                        'quantity': quantity,
                        'average_price': average_price,
                        'purchase_date': purchase_date,
                        'security_name': security_name,
                        'source_row': row_number,
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

            # Prefer human-readable name so ISINs / opaque tickers are never shown raw.
            display_name = data.get('security_name') or symbol

            holding = Holding(
                account_id=account.id,
                snapshot_id=snapshot.id,
                holding_key=f'us_equity:US:{symbol}',
                tradingsymbol=display_name[:100],
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

        # Extract the original ticker from holding_key ("us_equity:US:TICKER")
        # rather than tradingsymbol, which may now be a human-readable name.
        def _ticker(holding):
            parts = (holding.holding_key or '').split(':')
            return parts[-1] if len(parts) >= 3 else holding.tradingsymbol

        symbols = sorted({_ticker(h) for h in us_holdings})
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
            quote = prices.get(_ticker(old), {})
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
