"""
Zerodha Kite Connect API integration service.
Handles authentication, data fetching, and API interactions.
"""
from kiteconnect import KiteConnect
from datetime import datetime, timedelta, date
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
        except Exception as e:
            logger.error(f"Error generating session: {e}")
            raise

    def get_holdings(self) -> List[Dict]:
        """
        Fetch all holdings (stocks and mutual funds).

        Returns:
            List of holding dictionaries
        """
        if not self.access_token:
            raise ValueError("Access token not set. Call generate_session first.")

        try:
            # Fetch equity holdings
            holdings = self.kite.holdings()
            logger.info(f"Fetched {len(holdings)} holdings")

            # Process and normalize holdings data
            processed_holdings = []
            for holding in holdings:
                processed_holding = {
                    'tradingsymbol': holding.get('tradingsymbol'),
                    'exchange': holding.get('exchange'),
                    'isin': holding.get('isin'),
                    'instrument_type': 'equity',
                    'quantity': holding.get('quantity', 0),
                    'average_price': holding.get('average_price', 0),
                    'last_price': holding.get('last_price', 0),
                    'pnl': holding.get('pnl', 0),
                    'day_change': holding.get('day_change', 0),
                    'day_change_percentage': holding.get('day_change_percentage', 0),
                }

                # Calculate current value and P&L percentage
                current_value = processed_holding['quantity'] * processed_holding['last_price']
                invested_value = processed_holding['quantity'] * processed_holding['average_price']
                processed_holding['current_value'] = current_value

                if invested_value > 0:
                    processed_holding['pnl_percentage'] = ((current_value - invested_value) / invested_value) * 100
                else:
                    processed_holding['pnl_percentage'] = 0

                processed_holdings.append(processed_holding)

            return processed_holdings

        except Exception as e:
            logger.error(f"Error fetching holdings: {e}")
            raise

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
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
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

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
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
        except Exception as e:
            logger.error(f"Error fetching instruments: {e}")
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
        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
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
        except Exception as e:
            logger.error(f"Error fetching profile: {e}")
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
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                wait_time = delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
