"""EU-holdings spreadsheet import and price refresh service."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import logging
import re

import pandas as pd

from app.database import db
from app.models.holding import Holding
from app.models.snapshot import Snapshot
from app.services.eu_price_service import EUPriceService
from app.services.portfolio_service import PortfolioService


logger = logging.getLogger(__name__)
MAX_EU_HOLDINGS = 100
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
    quantum = Decimal('1').scaleb(-max_decimals)
    return result.quantize(quantum)


class EUHoldingsService:
    """Manage imported EU positions without mutating historical snapshots."""

    def __init__(self, price_service=None):
        self._price_service = price_service

    @property
    def price_service(self):
        if self._price_service is None:
            self._price_service = EUPriceService()
        return self._price_service

    _COLUMN_ALIASES = {
        # Generic / manual format
        'stock symbol': 'Symbol',
        'ticker': 'Symbol',
        'symbol': 'Symbol',
        'isin': 'ISIN',
        'isin:': 'ISIN',
        'qty': 'Quantity',
        'quantity': 'Quantity',
        'shares': 'Quantity',
        'avg. price (€)': 'Average Price',
        'avg price (€)': 'Average Price',
        'average price': 'Average Price',
        'average price (€)': 'Average Price',
        'avg price': 'Average Price',
        'cost basis': 'Average Price',
        'exchange': 'Exchange',
        'market': 'Exchange',
        'holding since': 'Purchase Date',
        'purchase date': 'Purchase Date',
        'buy date': 'Purchase Date',
        'date': 'Purchase Date',
        # Broker export format (Flatex / Trade Republic / Scalable)
        'pcs. / nominal': 'Quantity',
        'pcs./nominal': 'Quantity',
        'nominal': 'Quantity',
        'security name': 'Security Name',
        'name': 'Security Name',
        'description': 'Security Name',
        'price per piece': 'Average Price',
        'price per unit': 'Average Price',
        'current price': 'Average Price',
        'value in eur': 'Current Value',
        'market value': 'Current Value',
        'value (eur)': 'Current Value',
    }

    # Broker-export quantity cells look like "5.580914 Pcs." or "11 Stk."
    _QTY_RE = re.compile(r'^\s*([\d.,]+)\s*(?:pcs?\.?|stk\.?|units?|shares?)?\s*$', re.IGNORECASE)

    @classmethod
    def _find_header_row(cls, file_path):
        raw = pd.read_excel(file_path, header=None, nrows=20)
        # Standard format: row contains symbol-like column name
        symbol_keys = {'stock symbol', 'ticker', 'symbol'}
        # Broker export format: row contains "pcs. / nominal" or "security name"
        broker_keys = {'pcs. / nominal', 'pcs./nominal', 'nominal', 'security name'}
        for i, row in raw.iterrows():
            cells = {str(v).strip().lower() for v in row if pd.notna(v)}
            if cells & (symbol_keys | broker_keys):
                return int(i)
        return 0

    @classmethod
    def _normalise_columns(cls, df):
        rename = {}
        for col in df.columns:
            key = str(col).strip().lower()
            if key in cls._COLUMN_ALIASES:
                rename[col] = cls._COLUMN_ALIASES[key]
        return df.rename(columns=rename)

    @classmethod
    def _parse_quantity_cell(cls, raw):
        """Parse a quantity that may be a plain number or a broker string like '5.580914 Pcs.'"""
        if pd.isna(raw):
            raise ValueError('Quantity is empty')
        text = str(raw).strip().replace(',', '')
        match = cls._QTY_RE.match(text)
        if match:
            return _decimal(match.group(1))
        # Try plain numeric fallback
        return _decimal(raw)

    @staticmethod
    def _symbol_from_isin(isin):
        """Return the ISIN itself as a safe trading symbol (accepts 11–12 char codes)."""
        cleaned = re.sub(r'[^A-Z0-9]', '', isin.strip().upper())
        if not (11 <= len(cleaned) <= 12):
            raise ValueError(f'Invalid ISIN: {isin!r}')
        return cleaned

    @staticmethod
    def _symbol_from_name(name):
        """Derive a short symbol from a security name (max 20 chars, alphanumeric + hyphen)."""
        # Keep only words made of letters/digits, uppercase, join with hyphen, cap at 20
        words = re.findall(r'[A-Za-z0-9]+', str(name))
        symbol = '-'.join(w.upper() for w in words[:4])
        return symbol[:20] or 'UNKNOWN'

    @staticmethod
    def _parse_purchase_date(value):
        if pd.isna(value):
            return None
        if isinstance(value, (datetime, date)):
            return value.date() if isinstance(value, datetime) else value
        text = str(value).strip()
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
            nrows=header_row + MAX_EU_HOLDINGS + 1,
        )
        df = self._normalise_columns(df)

        if len(df.index) > MAX_EU_HOLDINGS:
            raise ValueError(
                f'An EU-holdings workbook may contain at most '
                f'{MAX_EU_HOLDINGS} positions'
            )

        # Detect broker-export format: no Symbol column but has ISIN + Security Name
        is_broker_format = (
            'Symbol' not in df.columns
            and 'ISIN' in df.columns
            and 'Security Name' in df.columns
        )

        if not is_broker_format:
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

            # ── Derive symbol ──────────────────────────────────────────
            if is_broker_format:
                raw_isin = row.get('ISIN')
                if pd.isna(raw_isin):
                    # summary/footer row (e.g. "NUMBER OF POSITIONS: N")
                    continue
                try:
                    symbol = self._symbol_from_isin(str(raw_isin))
                except ValueError:
                    continue
            else:
                raw_symbol = row.get('Symbol')
                if pd.isna(raw_symbol):
                    continue
                symbol = str(raw_symbol).strip().upper()
                if not re.fullmatch(r'[A-Z0-9.:/-]+', symbol) or len(symbol) > 50:
                    continue

            try:
                # ── Quantity ───────────────────────────────────────────
                quantity = self._parse_quantity_cell(row['Quantity'])
                if quantity <= 0:
                    raise ValueError('Quantity must be positive')

                # ── Price ──────────────────────────────────────────────
                # Broker format: PRICE PER PIECE is the current market price;
                # no separate cost basis is available, so average = last.
                average_price = _decimal(row['Average Price'])
                if average_price <= 0:
                    raise ValueError('Average Price must be positive')

                if (
                    not _fits_decimal(quantity, DB_POSITION_INPUT_MAX, 6)
                    or not _fits_decimal(average_price, DB_POSITION_INPUT_MAX, 6)
                    or quantity * average_price > DB_MONEY_MAX
                ):
                    raise ValueError('Position exceeds database precision')
                if symbol in seen_symbols:
                    raise ValueError(f'Duplicate symbol {symbol}')

                purchase_date = None
                if 'Purchase Date' in df.columns:
                    purchase_date = self._parse_purchase_date(row['Purchase Date'])

                exchange = None
                if 'Exchange' in df.columns and pd.notna(row.get('Exchange')):
                    exchange = str(row['Exchange']).strip().upper()

                # ISIN: prefer explicit ISIN column; for broker format it's
                # already the symbol so always populate it.
                isin = None
                if 'ISIN' in df.columns and pd.notna(row.get('ISIN')):
                    isin = str(row['ISIN']).strip().upper()
                # For generic format: if Symbol looks like an ISIN, record it as isin too
                if not isin and not is_broker_format:
                    _clean = re.sub(r'[^A-Z0-9]', '', symbol)
                    if re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9,10}', _clean):
                        isin = _clean

                # Capture human-readable name from any format that includes a
                # Security Name / Name / Description column so ISINs and opaque
                # ticker codes are never shown raw in the UI.
                security_name = None
                if 'Security Name' in df.columns and pd.notna(row.get('Security Name')):
                    security_name = str(row['Security Name']).strip() or None

                seen_symbols.add(symbol)
                holdings.append({
                    'symbol': symbol,
                    'quantity': quantity,
                    'average_price': average_price,
                    'purchase_date': purchase_date,
                    'exchange': exchange,
                    'isin': isin,
                    'security_name': security_name,
                    'source_row': row_number,
                })
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
                'Live EU prices unavailable; imported positions remain valued at cost',
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
            trigger='eu_upload',
            snapshot_date=now,
            exclude_types=('eu_equity',),
        )

        created = []
        for data in parsed_holdings:
            symbol = data['symbol']
            quote = prices.get(symbol, {})
            has_live_price = 'current_price' in quote
            last_price = _decimal(
                quote['current_price'] if has_live_price else data['average_price']
            )
            quantity = data['quantity']
            average_price = data['average_price']
            current_value = quantity * last_price
            invested = quantity * average_price
            pnl = current_value - invested

            exchange = data.get('exchange') or 'EU'

            # Prefer the human-readable security name if available (covers broker
            # export rows where the internal symbol is an ISIN, and generic rows
            # where the user included a Name / Security Name column).
            display_name = data.get('security_name') or symbol

            holding = Holding(
                account_id=account.id,
                snapshot_id=snapshot.id,
                holding_key=f'eu_equity:EU:{symbol}',
                tradingsymbol=display_name[:100],
                exchange=exchange,
                instrument_type='eu_equity',
                market='EU',
                currency='EUR',
                isin=data.get('isin'),
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
                source='finnhub_eu' if has_live_price else 'upload_eu_at_cost',
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
        eu_holdings = (
            [holding for holding in previous.holdings if holding.instrument_type == 'eu_equity']
            if previous
            else []
        )
        if not eu_holdings:
            return 0

        # Extract the original ISIN/symbol from holding_key ("eu_equity:EU:SYM")
        # rather than tradingsymbol, which may now be a human-readable name.
        def _sym(holding):
            parts = (holding.holding_key or '').split(':')
            return parts[-1] if len(parts) >= 3 else holding.tradingsymbol

        symbols = sorted({_sym(h) for h in eu_holdings})
        prices = self.fetch_current_prices(symbols)
        unavailable = [
            symbol
            for symbol in symbols
            if not isinstance(prices.get(symbol), dict)
            or 'current_price' not in prices[symbol]
        ]
        if unavailable:
            raise RuntimeError(
                'Live prices are unavailable for one or more EU holdings'
            )

        now = datetime.utcnow()
        snapshot = PortfolioService.create_account_snapshot(
            account,
            trigger='eu_refresh',
            snapshot_date=now,
            exclude_types=('eu_equity',),
        )

        updated = 0
        for old in eu_holdings:
            quote = prices.get(_sym(old), {})
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
                    currency='EUR',
                    isin=old.isin,
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
                    source='finnhub_eu' if has_live_price else old.source,
                    valued_at=now if has_live_price else old.valued_at,
                )
            )
            updated += 1

        PortfolioService.finalize_snapshot(snapshot)
        db.session.commit()
        return updated
