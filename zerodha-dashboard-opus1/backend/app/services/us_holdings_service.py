"""
US Holdings service for parsing Excel files and managing US stock holdings.
"""
import pandas as pd
from datetime import datetime
from app.models.holding import Holding
from app.models.snapshot import Snapshot
from app.database import db
from app.services.finnhub_service import FinnhubService
import logging

logger = logging.getLogger(__name__)


class USHoldingsService:
    """Service for managing US stock holdings"""

    def __init__(self):
        self.finnhub = FinnhubService()

    def parse_excel_file(self, file_path):
        """
        Parse Excel file and return list of holdings.

        Expected columns: Symbol, Quantity, Average Price, Purchase Date (optional)

        Args:
            file_path: Path to Excel file

        Returns:
            list: List of holding dictionaries

        Raises:
            ValueError: If required columns are missing or data is invalid
        """
        try:
            df = pd.read_excel(file_path)

            # Validate required columns
            required_cols = ['Symbol', 'Quantity', 'Average Price']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")

            holdings = []
            for idx, row in df.iterrows():
                # Skip empty rows
                if pd.isna(row['Symbol']):
                    continue

                try:
                    holding = {
                        'symbol': str(row['Symbol']).strip().upper(),
                        'quantity': float(row['Quantity']),
                        'average_price': float(row['Average Price']),
                        'purchase_date': None
                    }

                    # Validate data
                    if holding['quantity'] <= 0:
                        logger.warning(f"Row {idx + 2}: Invalid quantity ({holding['quantity']}), skipping")
                        continue

                    if holding['average_price'] <= 0:
                        logger.warning(f"Row {idx + 2}: Invalid average price ({holding['average_price']}), skipping")
                        continue

                    # Parse optional purchase date
                    if 'Purchase Date' in df.columns and not pd.isna(row['Purchase Date']):
                        if isinstance(row['Purchase Date'], datetime):
                            holding['purchase_date'] = row['Purchase Date']
                        else:
                            # Try to parse as string
                            try:
                                holding['purchase_date'] = pd.to_datetime(row['Purchase Date'])
                            except:
                                logger.warning(f"Row {idx + 2}: Could not parse purchase date: {row['Purchase Date']}")

                    holdings.append(holding)

                except (ValueError, TypeError) as e:
                    logger.warning(f"Row {idx + 2}: Error parsing data - {str(e)}, skipping")
                    continue

            if not holdings:
                raise ValueError("No valid holdings found in file. Please check the data format.")

            logger.info(f"Parsed {len(holdings)} holdings from Excel file")
            return holdings

        except Exception as e:
            logger.error(f"Failed to parse Excel file: {str(e)}")
            raise Exception(f"Failed to parse Excel file: {str(e)}")

    def fetch_current_prices(self, symbols):
        """
        Fetch current prices for list of symbols using Finnhub.

        Args:
            symbols: List of stock symbols

        Returns:
            dict: {symbol: price_data}
        """
        return self.finnhub.get_quotes_batch(symbols)

    def create_holdings(self, account_id, parsed_holdings, fetch_prices=True):
        """
        Create US holdings in database with optional price fetching.

        Args:
            account_id: Account ID to associate holdings with
            parsed_holdings: List of parsed holding dictionaries
            fetch_prices: Whether to fetch current prices from Finnhub

        Returns:
            list: Created Holding objects

        Raises:
            Exception: If database operation fails
        """
        try:
            # Create new snapshot
            snapshot = Snapshot(
                account_id=account_id,
                snapshot_date=datetime.utcnow()
            )
            db.session.add(snapshot)
            db.session.flush()  # Get snapshot ID

            # Fetch current prices if requested
            prices = {}
            if fetch_prices:
                symbols = [h['symbol'] for h in parsed_holdings]
                logger.info(f"Fetching prices for {len(symbols)} symbols from Finnhub...")
                prices = self.fetch_current_prices(symbols)

            # Create holdings
            created_holdings = []
            for holding_data in parsed_holdings:
                symbol = holding_data['symbol']

                # Get current price or use average price
                if symbol in prices and 'current_price' in prices[symbol]:
                    last_price = prices[symbol]['current_price']
                    day_change = prices[symbol].get('change', 0)
                    day_change_percentage = prices[symbol].get('change_percent', 0)
                else:
                    # Use average price if Finnhub fetch failed
                    logger.warning(f"Using average price for {symbol} as current price fetch failed")
                    last_price = holding_data['average_price']
                    day_change = 0
                    day_change_percentage = 0

                # Calculate values
                quantity = holding_data['quantity']
                average_price = holding_data['average_price']
                current_value = quantity * last_price
                investment = quantity * average_price
                pnl = current_value - investment
                pnl_percentage = (pnl / investment * 100) if investment > 0 else 0

                holding = Holding(
                    account_id=account_id,
                    snapshot_id=snapshot.id,
                    tradingsymbol=symbol,
                    exchange='US',  # Generic US exchange
                    instrument_type='us_equity',
                    market='US',
                    quantity=int(quantity),
                    average_price=average_price,
                    last_price=last_price,
                    current_value=current_value,
                    pnl=pnl,
                    pnl_percentage=pnl_percentage,
                    day_change=day_change,
                    day_change_percentage=day_change_percentage,
                    purchase_date=holding_data.get('purchase_date'),
                    sector='Unknown'  # Could fetch from Finnhub company profile
                )
                db.session.add(holding)
                created_holdings.append(holding)

            db.session.commit()
            logger.info(f"Created {len(created_holdings)} US holdings in database")
            return created_holdings

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create holdings: {str(e)}")
            raise Exception(f"Failed to create holdings: {str(e)}")
