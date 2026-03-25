"""
Finnhub API service for US stock price data.
"""
import finnhub
import os
import logging

logger = logging.getLogger(__name__)


class FinnhubService:
    """Service for interacting with Finnhub API"""

    def __init__(self):
        self.api_key = os.getenv('FINNHUB_API_KEY')
        if not self.api_key or self.api_key == 'your_finnhub_api_key_here':
            raise ValueError("FINNHUB_API_KEY not found in environment or not configured. Get your API key from https://finnhub.io/register")
        self.client = finnhub.Client(api_key=self.api_key)

    def get_quote(self, symbol):
        """
        Fetch real-time quote for a single symbol.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')

        Returns:
            dict: {
                'current_price': float,
                'change': float,
                'change_percent': float,
                'high': float,
                'low': float,
                'open': float,
                'previous_close': float
            }
        """
        try:
            quote = self.client.quote(symbol)

            # Check if quote is valid (Finnhub returns 0 for invalid symbols)
            if quote['c'] == 0:
                raise Exception(f"Invalid symbol or no data available for {symbol}")

            return {
                'current_price': quote['c'],  # Current price
                'change': quote['d'],         # Change
                'change_percent': quote['dp'], # Percent change
                'high': quote['h'],           # Day high
                'low': quote['l'],            # Day low
                'open': quote['o'],           # Open price
                'previous_close': quote['pc'] # Previous close
            }
        except Exception as e:
            logger.error(f"Failed to fetch quote for {symbol}: {str(e)}")
            raise Exception(f"Failed to fetch quote for {symbol}: {str(e)}")

    def get_quotes_batch(self, symbols):
        """
        Fetch quotes for multiple symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            dict: {symbol: quote_data} for each symbol
        """
        quotes = {}
        for symbol in symbols:
            try:
                quotes[symbol] = self.get_quote(symbol)
                logger.info(f"Fetched quote for {symbol}: ${quotes[symbol]['current_price']}")
            except Exception as e:
                # Log error but continue with other symbols
                logger.warning(f"Error fetching {symbol}: {str(e)}")
                quotes[symbol] = {'error': str(e)}
        return quotes
