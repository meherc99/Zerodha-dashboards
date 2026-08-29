"""
European stock price service using Finnhub API (supports European exchanges).
"""
import os
import logging

try:
    import finnhub
except ImportError:
    finnhub = None

logger = logging.getLogger(__name__)


class EUPriceService:
    """Service for fetching European stock prices via Finnhub API.

    Finnhub supports European exchanges using exchange-prefixed symbols,
    e.g. 'LSE:BP' for BP on the London Stock Exchange.
    Common exchange prefixes:
      - LSE: (London)
      - XETRA: (Frankfurt)
      - EPA: (Paris/Euronext)
      - BIT: (Milan)
      - BME: (Madrid)
      - AMS: (Amsterdam/Euronext)
    """

    # Map of exchange codes to descriptive names
    EXCHANGES = {
        'LSE': 'London Stock Exchange',
        'XETRA': 'Frankfurt Stock Exchange',
        'EPA': 'Euronext Paris',
        'BIT': 'Borsa Italiana',
        'BME': 'Bolsa de Madrid',
        'AMS': 'Euronext Amsterdam',
        'SWX': 'SIX Swiss Exchange',
        'HEL': 'Nasdaq Helsinki',
        'CPH': 'Nasdaq Copenhagen',
        'OSL': 'Oslo Bors',
        'STO': 'Nasdaq Stockholm',
    }

    def __init__(self):
        if finnhub is None:
            raise RuntimeError(
                "finnhub-python is required for live EU price refreshes"
            )
        self.api_key = os.getenv('FINNHUB_API_KEY')
        if not self.api_key or self.api_key == 'your_finnhub_api_key_here':
            raise ValueError(
                "FINNHUB_API_KEY not found in environment or not configured. "
                "Get your API key from https://finnhub.io/register"
            )
        self.client = finnhub.Client(api_key=self.api_key)

    def get_quote(self, symbol):
        """
        Fetch real-time quote for a single European symbol.

        Args:
            symbol: Stock symbol, optionally with exchange prefix
                    (e.g., 'SAP' for XETRA, or 'LSE:BP')

        Returns:
            dict with current_price, change, change_percent, etc.
        """
        try:
            quote = self.client.quote(symbol)

            if quote['c'] == 0:
                raise Exception(
                    f"Invalid symbol or no data available for {symbol}"
                )
            return {
                'current_price': quote['c'],
                'change': quote['d'],
                'change_percent': quote['dp'],
                'high': quote['h'],
                'low': quote['l'],
                'open': quote['o'],
                'previous_close': quote['pc'],
            }
        except Exception as error:
            logger.error("EU quote fetch failed for symbol %s", symbol)
            raise RuntimeError(f'Quote unavailable for {symbol}') from error

    def get_quotes_batch(self, symbols):
        """Fetch quotes for a batch of European stock symbols."""
        quotes = {}
        for symbol in symbols:
            try:
                quotes[symbol] = self.get_quote(symbol)
                logger.info(
                    "Fetched EU quote for %s: €%s",
                    symbol,
                    quotes[symbol]['current_price'],
                )
            except Exception:
                logger.warning("EU quote unavailable for symbol %s", symbol)
                quotes[symbol] = {'error': 'Quote unavailable'}
        return quotes
