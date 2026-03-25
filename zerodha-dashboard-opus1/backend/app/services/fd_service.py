"""
Fixed Deposit service for parsing Excel files and managing FD holdings.
"""
import pandas as pd
from datetime import datetime, date
from decimal import Decimal
from app.models.holding import Holding
from app.models.snapshot import Snapshot
from app.database import db
import logging

logger = logging.getLogger(__name__)


class FDService:
    """Service for managing Fixed Deposit holdings"""

    @staticmethod
    def calculate_fd_returns(investment_amount, investment_date, interest_rate, maturity_date=None):
        """
        Calculate FD returns and current value.

        Args:
            investment_amount: Principal amount invested
            investment_date: Date of investment (datetime or date object)
            interest_rate: Annual interest rate (as percentage, e.g., 7.5 for 7.5%)
            maturity_date: Optional maturity date (if None, calculates till today)

        Returns:
            dict: {
                'days_elapsed': int,
                'years_elapsed': float,
                'interest_earned': float,
                'current_value': float
            }
        """
        try:
            # Convert to date if datetime
            if isinstance(investment_date, datetime):
                investment_date = investment_date.date()

            # Calculate till maturity or today
            if maturity_date:
                if isinstance(maturity_date, datetime):
                    maturity_date = maturity_date.date()
                end_date = maturity_date
            else:
                end_date = date.today()

            # Calculate days elapsed
            days_elapsed = (end_date - investment_date).days

            # Handle negative days (future investment date)
            if days_elapsed < 0:
                return {
                    'days_elapsed': 0,
                    'years_elapsed': 0,
                    'interest_earned': 0,
                    'current_value': float(investment_amount)
                }

            # Calculate years (for interest calculation)
            years_elapsed = days_elapsed / 365.0

            # Calculate simple interest: P * R * T / 100
            interest_earned = (
                float(investment_amount) *
                float(interest_rate) *
                years_elapsed / 100.0
            )

            current_value = float(investment_amount) + interest_earned

            return {
                'days_elapsed': days_elapsed,
                'years_elapsed': round(years_elapsed, 2),
                'interest_earned': round(interest_earned, 2),
                'current_value': round(current_value, 2)
            }

        except Exception as e:
            logger.error(f"Error calculating FD returns: {str(e)}")
            return {
                'days_elapsed': 0,
                'years_elapsed': 0,
                'interest_earned': 0,
                'current_value': float(investment_amount)
            }

    def parse_excel_file(self, file_path):
        """
        Parse Excel file and return list of FD holdings.

        Expected columns: Bank Name, Investment Amount, Investment Date, Interest Rate, Maturity Date (optional)

        Args:
            file_path: Path to Excel file

        Returns:
            list: List of FD dictionaries

        Raises:
            ValueError: If required columns are missing or data is invalid
        """
        try:
            df = pd.read_excel(file_path)

            # Validate required columns
            required_cols = ['Bank Name', 'Investment Amount', 'Investment Date', 'Interest Rate']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")

            fds = []
            for idx, row in df.iterrows():
                # Skip empty rows
                if pd.isna(row['Bank Name']):
                    continue

                try:
                    # Parse investment date
                    if isinstance(row['Investment Date'], datetime):
                        investment_date = row['Investment Date']
                    else:
                        investment_date = pd.to_datetime(row['Investment Date'])

                    # Parse maturity date (optional)
                    maturity_date = None
                    if 'Maturity Date' in df.columns and not pd.isna(row['Maturity Date']):
                        if isinstance(row['Maturity Date'], datetime):
                            maturity_date = row['Maturity Date']
                        else:
                            try:
                                maturity_date = pd.to_datetime(row['Maturity Date'])
                            except:
                                logger.warning(f"Row {idx + 2}: Could not parse maturity date")

                    fd = {
                        'bank_name': str(row['Bank Name']).strip(),
                        'investment_amount': float(row['Investment Amount']),
                        'investment_date': investment_date,
                        'interest_rate': float(row['Interest Rate']),
                        'maturity_date': maturity_date
                    }

                    # Validate data
                    if fd['investment_amount'] <= 0:
                        logger.warning(f"Row {idx + 2}: Invalid investment amount ({fd['investment_amount']}), skipping")
                        continue

                    if fd['interest_rate'] <= 0 or fd['interest_rate'] > 100:
                        logger.warning(f"Row {idx + 2}: Invalid interest rate ({fd['interest_rate']}), skipping")
                        continue

                    fds.append(fd)

                except (ValueError, TypeError) as e:
                    logger.warning(f"Row {idx + 2}: Error parsing data - {str(e)}, skipping")
                    continue

            if not fds:
                raise ValueError("No valid FD records found in file. Please check the data format.")

            logger.info(f"Parsed {len(fds)} FD records from Excel file")
            return fds

        except Exception as e:
            logger.error(f"Failed to parse Excel file: {str(e)}")
            raise Exception(f"Failed to parse Excel file: {str(e)}")

    def create_fd_holdings(self, account_id, parsed_fds):
        """
        Create FD holdings in database with calculated returns.

        Args:
            account_id: Account ID to associate FDs with
            parsed_fds: List of parsed FD dictionaries

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

            # Create FD holdings
            created_holdings = []
            for fd_data in parsed_fds:
                # Calculate current returns
                returns = self.calculate_fd_returns(
                    investment_amount=fd_data['investment_amount'],
                    investment_date=fd_data['investment_date'],
                    interest_rate=fd_data['interest_rate'],
                    maturity_date=fd_data.get('maturity_date')
                )

                # Create holding record
                holding = Holding(
                    account_id=account_id,
                    snapshot_id=snapshot.id,
                    tradingsymbol=fd_data['bank_name'],  # Use bank name as symbol
                    exchange='FD',
                    instrument_type='fd',
                    market='IN',
                    quantity=1,  # FDs are single units
                    average_price=fd_data['investment_amount'],
                    last_price=returns['current_value'],  # Current value
                    current_value=returns['current_value'],
                    pnl=returns['interest_earned'],  # Interest earned is P&L
                    pnl_percentage=(returns['interest_earned'] / fd_data['investment_amount'] * 100) if fd_data['investment_amount'] > 0 else 0,
                    day_change=0,  # FDs don't have day-to-day changes
                    day_change_percentage=0,
                    purchase_date=fd_data['investment_date'],
                    sector=f"{fd_data['interest_rate']}% p.a."  # Store interest rate in sector field
                )
                db.session.add(holding)
                created_holdings.append(holding)

            db.session.commit()
            logger.info(f"Created {len(created_holdings)} FD holdings in database")
            return created_holdings

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create FD holdings: {str(e)}")
            raise Exception(f"Failed to create FD holdings: {str(e)}")

    def refresh_fd_values(self, account_id=None):
        """
        Recalculate interest for existing FD holdings.

        Args:
            account_id: Optional account ID to filter FDs

        Returns:
            int: Number of FDs updated
        """
        try:
            # Get latest snapshot for FD holdings
            query = Holding.query.filter_by(instrument_type='fd')
            if account_id:
                query = query.filter_by(account_id=account_id)

            # Get latest snapshot
            latest_snapshot = Snapshot.query.order_by(Snapshot.snapshot_date.desc()).first()
            if latest_snapshot:
                query = query.filter_by(snapshot_id=latest_snapshot.id)

            fd_holdings = query.all()

            if not fd_holdings:
                return 0

            updated_count = 0
            for holding in fd_holdings:
                # Extract interest rate from sector field
                try:
                    interest_rate = float(holding.sector.replace('% p.a.', ''))
                except:
                    logger.warning(f"Could not parse interest rate for {holding.tradingsymbol}")
                    continue

                # Recalculate returns
                returns = self.calculate_fd_returns(
                    investment_amount=holding.average_price,
                    investment_date=holding.purchase_date,
                    interest_rate=interest_rate
                )

                # Update holding
                holding.last_price = returns['current_value']
                holding.current_value = returns['current_value']
                holding.pnl = returns['interest_earned']
                holding.pnl_percentage = (returns['interest_earned'] / holding.average_price * 100) if holding.average_price > 0 else 0

                updated_count += 1

            db.session.commit()
            logger.info(f"Updated {updated_count} FD holdings")
            return updated_count

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to refresh FD values: {str(e)}")
            raise Exception(f"Failed to refresh FD values: {str(e)}")
