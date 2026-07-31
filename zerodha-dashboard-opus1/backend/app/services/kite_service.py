"""
Zerodha Kite Connect API integration service.
Handles authentication, data fetching, and API interactions.
"""
from kiteconnect import KiteConnect
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
import time
import logging
from typing import List, Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class KiteService:
    """Service for interacting with Zerodha Kite Connect API"""

    def __init__(self, api_key: str, api_secret: str, access_token: Optional[str] = None):
        """
        Initialize Kite Connect client.

        Args:
            api_key: Zerodha API key
            api_secret: Zerodha API secret
            access_token: Optional access token (if already generated)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.kite = KiteConnect(api_key=api_key)

        if access_token:
            self.kite.set_access_token(access_token)
            self.access_token = access_token
        else:
            self.access_token = None

    def get_login_url(self) -> str:
        """Return the Zerodha login URL for the configured API key."""
        return self.kite.login_url()

    def generate_session(self, request_token: str) -> str:
        """
        Generate access token from request token.

        Args:
            request_token: Request token from Kite login flow

        Returns:
            Access token string
        """
        try:
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            self.access_token = data["access_token"]
            self.kite.set_access_token(self.access_token)
            logger.info("Access token generated successfully")
            return self.access_token
        except Exception:
            logger.error("Kite session generation failed")
            raise

    @staticmethod
    def _decimal(value) -> Decimal:
        try:
            result = Decimal(str(value or 0))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal('0')
        return result if result.is_finite() else Decimal('0')

    @staticmethod
    def _date(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return datetime.fromisoformat(str(value)).date()
        except ValueError:
            return None

    def get_equity_holdings(self) -> List[Dict]:
        """Fetch and normalize delivery equity holdings."""
        if not self.access_token:
            raise ValueError("Access token not set. Call generate_session first.")

        try:
            holdings = self.kite.holdings()
            processed_holdings = []
            for holding in holdings:
                symbol = str(holding.get('tradingsymbol') or '').strip()
                if not symbol:
                    logger.warning("Skipping equity holding without tradingsymbol")
                    continue

                quantity = self._decimal(holding.get('quantity'))
                average_price = self._decimal(holding.get('average_price'))
                last_price = self._decimal(holding.get('last_price'))
                current_value = quantity * last_price
                investment = quantity * average_price
                pnl = self._decimal(holding.get('pnl'))
                if holding.get('pnl') is None:
                    pnl = current_value - investment

                exchange = str(holding.get('exchange') or 'NSE').upper()
                isin = holding.get('isin')
                processed_holdings.append({
                    'holding_key': f"equity:{exchange}:{isin or symbol}",
                    'tradingsymbol': symbol,
                    'exchange': exchange,
                    'isin': isin,
                    'instrument_type': 'equity',
                    'market': 'IN',
                    'currency': 'INR',
                    'quantity': quantity,
                    'average_price': average_price,
                    'last_price': last_price,
                    'last_price_date': None,
                    'pnl': pnl,
                    'pnl_percentage': pnl / investment * 100 if investment else 0,
                    'day_change': self._decimal(holding.get('day_change')),
                    'day_change_percentage': self._decimal(
                        holding.get('day_change_percentage')
                    ),
                    'current_value': current_value,
                    'folio': None,
                    'source': 'kite_equity',
                })
            logger.info("Fetched %s equity holdings", len(processed_holdings))
            return processed_holdings
        except Exception:
            logger.error("Kite equity-holdings fetch failed")
            raise

    def get_mutual_fund_holdings(self) -> List[Dict]:
        """Fetch and normalize Coin mutual-fund holdings."""
        if not self.access_token:
            raise ValueError("Access token not set. Call generate_session first.")

        try:
            holdings = self.kite.mf_holdings()
            processed_holdings = []
            for holding in holdings:
                raw_symbol = (
                    holding.get('tradingsymbol')
                    or holding.get('fund')
                    or holding.get('isin')
                )
                symbol = str(raw_symbol or '').strip()
                if not symbol:
                    logger.warning("Skipping mutual-fund holding without identity")
                    continue

                folio = str(holding.get('folio') or '').strip() or None
                quantity = self._decimal(holding.get('quantity'))
                average_price = self._decimal(holding.get('average_price'))
                last_price = self._decimal(holding.get('last_price'))
                current_value = quantity * last_price
                investment = quantity * average_price
                pnl = self._decimal(holding.get('pnl'))
                if holding.get('pnl') is None:
                    pnl = current_value - investment

                identity = holding.get('isin') or symbol
                processed_holdings.append({
                    'holding_key': f"mf:{folio or 'no-folio'}:{identity}",
                    'tradingsymbol': symbol[:100],
                    'exchange': 'MF',
                    'isin': holding.get('isin'),
                    'folio': folio,
                    'instrument_type': 'mf',
                    'market': 'IN',
                    'currency': 'INR',
                    'quantity': quantity,
                    'average_price': average_price,
                    'last_price': last_price,
                    'last_price_date': self._date(holding.get('last_price_date')),
                    'pnl': pnl,
                    'pnl_percentage': pnl / investment * 100 if investment else 0,
                    'day_change': 0,
                    'day_change_percentage': 0,
                    'current_value': current_value,
                    'source': 'kite_mf',
                })
            logger.info("Fetched %s mutual-fund holdings", len(processed_holdings))
            return processed_holdings
        except Exception:
            logger.error("Kite mutual-fund fetch failed")
            raise

    def get_holdings(self) -> List[Dict]:
        """Fetch equities and Coin mutual funds through their distinct APIs."""
        return self.get_equity_holdings() + self.get_mutual_fund_holdings()

    def get_positions(self) -> Dict:
        """
        Fetch current day positions.

        Returns:
            Dictionary with 'net' and 'day' positions
        """
        if not self.access_token:
            raise ValueError("Access token not set")

        try:
            positions = self.kite.positions()
            logger.info("Fetched positions successfully")
            return positions
        except Exception:
            logger.error("Kite positions fetch failed")
            raise

    def get_historical_data(
        self,
        instrument_token: str,
        from_date: date,
        to_date: date,
        interval: str = "day"
    ) -> pd.DataFrame:
        """
        Fetch historical OHLC data for correlation analysis.

        Args:
            instrument_token: Instrument token or trading symbol
            from_date: Start date
            to_date: End date
            interval: Candle interval (minute, day, 3minute, 5minute, etc.)

        Returns:
            DataFrame with OHLC data
        """
        if not self.access_token:
            raise ValueError("Access token not set")

        try:
            # Convert dates to datetime if needed
            if isinstance(from_date, date) and not isinstance(from_date, datetime):
                from_date = datetime.combine(from_date, datetime.min.time())
            if isinstance(to_date, date) and not isinstance(to_date, datetime):
                to_date = datetime.combine(to_date, datetime.max.time())

            historical_data = self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )

            # Convert to DataFrame
            df = pd.DataFrame(historical_data)
            logger.info(f"Fetched {len(df)} historical records for {instrument_token}")
            return df

        except Exception:
            logger.error("Kite historical-data fetch failed")
            raise

    def get_instruments(self, exchange: str = "NSE") -> pd.DataFrame:
        """
        Fetch instruments list for an exchange.

        Args:
            exchange: Exchange name (NSE, BSE, NFO, etc.)

        Returns:
            DataFrame with instrument data
        """
        try:
            instruments = self.kite.instruments(exchange)
            df = pd.DataFrame(instruments)
            logger.info(f"Fetched {len(df)} instruments for {exchange}")
            return df
        except Exception:
            logger.error("Kite instruments fetch failed")
            raise

    def get_quote(self, symbols: List[str]) -> Dict:
        """
        Fetch current quotes for given symbols.

        Args:
            symbols: List of symbols in format "exchange:tradingsymbol"

        Returns:
            Dictionary of quotes
        """
        if not self.access_token:
            raise ValueError("Access token not set")

        try:
            quotes = self.kite.quote(symbols)
            return quotes
        except Exception:
            logger.error("Kite quote fetch failed")
            raise

    def get_profile(self) -> Dict:
        """
        Fetch user profile information.

        Returns:
            User profile dictionary
        """
        if not self.access_token:
            raise ValueError("Access token not set")

        try:
            profile = self.kite.profile()
            return profile
        except Exception:
            logger.error("Kite profile fetch failed")
            raise

    @staticmethod
    def retry_on_failure(func, max_attempts=3, delay=2):
        """
        Retry decorator for API calls with exponential backoff.

        Args:
            func: Function to retry
            max_attempts: Maximum retry attempts
            delay: Initial delay in seconds

        Returns:
            Function result or raises exception
        """
        for attempt in range(max_attempts):
            try:
                return func()
            except Exception:
                if attempt == max_attempts - 1:
                    raise
                wait_time = delay * (2 ** attempt)
                logger.warning(
                    "Kite request attempt %s failed; retrying in %ss",
                    attempt + 1,
                    wait_time,
                )
                time.sleep(wait_time)
