"""
Bank Analytics Service for generating spending patterns and trends.
"""
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import func, and_
from app.database import db
from app.models.transaction import Transaction
from app.models.transaction_category import TransactionCategory
from app.models.bank_account import BankAccount


class BankAnalyticsService:
    """Service for bank account analytics and insights"""

    @staticmethod
    def verify_ownership(bank_account_id, user_id):
        """Verify that the user owns the bank account"""
        account = BankAccount.query.filter_by(
            id=bank_account_id,
            user_id=user_id
        ).first()
        return account is not None

    @staticmethod
    def get_balance_trend(bank_account_id, days, user_id):
        """
        Get balance trend over specified number of days.
        Returns last transaction balance for each day.

        Args:
            bank_account_id: ID of the bank account
            days: Number of days to analyze (default: 30)
            user_id: ID of the requesting user (for ownership verification)

        Returns:
            {
                'dates': ['2024-01-01', '2024-01-02', ...],
                'balances': [10000, 9500, 12000, ...],
                'period_days': 30
            }
        """
        # Verify ownership
        if not BankAnalyticsService.verify_ownership(bank_account_id, user_id):
            return None

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Get last transaction per day with running balance
        # Using subquery to get last transaction ID per day
        subquery = db.session.query(
            Transaction.transaction_date,
            func.max(Transaction.id).label('max_id')
        ).filter(
            Transaction.bank_account_id == bank_account_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.verified == True,
            Transaction.running_balance.isnot(None)
        ).group_by(
            Transaction.transaction_date
        ).subquery()

        # Join to get the actual transactions
        results = db.session.query(
            Transaction.transaction_date,
            Transaction.running_balance
        ).join(
            subquery,
            and_(
                Transaction.id == subquery.c.max_id,
                Transaction.transaction_date == subquery.c.transaction_date
            )
        ).order_by(
            Transaction.transaction_date
        ).all()

        dates = [result.transaction_date.isoformat() for result in results]
        balances = [float(result.running_balance) for result in results]

        return {
            'dates': dates,
            'balances': balances,
            'period_days': days
        }

    @staticmethod
    def get_category_breakdown(bank_account_id, period_days, user_id):
        """
        Get spending breakdown by category (debit transactions only).

        Args:
            bank_account_id: ID of the bank account
            period_days: Number of days to analyze (default: 30)
            user_id: ID of the requesting user

        Returns:
            {
                'categories': [
                    {
                        'id': 4,
                        'name': 'Groceries',
                        'icon': '🛒',
                        'color': '#10b981',
                        'total': 15000.00,
                        'percentage': 25.5,
                        'transaction_count': 12
                    }
                ],
                'total_spending': 58800.00,
                'period_days': 30
            }
        """
        # Verify ownership
        if not BankAnalyticsService.verify_ownership(bank_account_id, user_id):
            return None

        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)

        # Get category-wise spending (only debits)
        results = db.session.query(
            TransactionCategory.id,
            TransactionCategory.name,
            TransactionCategory.icon,
            TransactionCategory.color,
            func.sum(Transaction.amount).label('total'),
            func.count(Transaction.id).label('count')
        ).join(
            Transaction,
            Transaction.category_id == TransactionCategory.id
        ).filter(
            Transaction.bank_account_id == bank_account_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.transaction_type == 'debit',
            Transaction.verified == True
        ).group_by(
            TransactionCategory.id,
            TransactionCategory.name,
            TransactionCategory.icon,
            TransactionCategory.color
        ).all()

        # Calculate total spending
        total_spending = sum(float(result.total) for result in results)

        # Build categories list with percentages
        categories = []
        for result in results:
            total_amount = float(result.total)
            percentage = (total_amount / total_spending * 100) if total_spending > 0 else 0

            categories.append({
                'id': result.id,
                'name': result.name,
                'icon': result.icon,
                'color': result.color,
                'total': total_amount,
                'percentage': round(percentage, 2),
                'transaction_count': result.count
            })

        # Sort by total spending (descending)
        categories.sort(key=lambda x: x['total'], reverse=True)

        return {
            'categories': categories,
            'total_spending': total_spending,
            'period_days': period_days
        }

    @staticmethod
    def get_cashflow_analysis(bank_account_id, period_days, user_id):
        """
        Get cashflow analysis (credits vs debits) grouped by week.

        Args:
            bank_account_id: ID of the bank account
            period_days: Number of days to analyze (default: 30)
            user_id: ID of the requesting user

        Returns:
            {
                'periods': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                'credits': [50000, 0, 5000, 0],
                'debits': [12000, 15000, 13000, 18000],
                'net': [38000, -15000, -8000, -18000],
                'period_days': 30
            }
        """
        # Verify ownership
        if not BankAnalyticsService.verify_ownership(bank_account_id, user_id):
            return None

        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)

        # Calculate number of weeks (round up)
        num_weeks = (period_days + 6) // 7

        periods = []
        credits = []
        debits = []
        net = []

        # Group transactions by week
        for week_num in range(num_weeks):
            week_start = start_date + timedelta(days=week_num * 7)
            week_end = min(week_start + timedelta(days=6), end_date)

            # Get credits for this week
            credit_sum = db.session.query(
                func.sum(Transaction.amount)
            ).filter(
                Transaction.bank_account_id == bank_account_id,
                Transaction.transaction_date >= week_start,
                Transaction.transaction_date <= week_end,
                Transaction.transaction_type == 'credit',
                Transaction.verified == True
            ).scalar() or Decimal('0')

            # Get debits for this week
            debit_sum = db.session.query(
                func.sum(Transaction.amount)
            ).filter(
                Transaction.bank_account_id == bank_account_id,
                Transaction.transaction_date >= week_start,
                Transaction.transaction_date <= week_end,
                Transaction.transaction_type == 'debit',
                Transaction.verified == True
            ).scalar() or Decimal('0')

            credit_amount = float(credit_sum)
            debit_amount = float(debit_sum)
            net_amount = credit_amount - debit_amount

            periods.append(f'Week {week_num + 1}')
            credits.append(credit_amount)
            debits.append(debit_amount)
            net.append(net_amount)

        return {
            'periods': periods,
            'credits': credits,
            'debits': debits,
            'net': net,
            'period_days': period_days
        }

    @staticmethod
    def extract_merchant(description, merchant_name=None):
        """
        Extract merchant name from transaction description or use provided merchant_name.

        Args:
            description: Transaction description
            merchant_name: Pre-extracted merchant name (if available)

        Returns:
            str: Merchant name
        """
        # Use merchant_name if provided
        if merchant_name:
            return merchant_name

        # Simple keyword matching
        description_upper = description.upper()

        # Common patterns
        if 'AMAZON' in description_upper:
            return 'Amazon'
        elif 'SWIGGY' in description_upper:
            return 'Swiggy'
        elif 'ZOMATO' in description_upper:
            return 'Zomato'
        elif 'BIGBASKET' in description_upper or 'BIG BASKET' in description_upper:
            return 'BigBasket'
        elif 'GROFER' in description_upper or 'BLINKIT' in description_upper:
            return 'Blinkit/Grofers'
        elif 'FLIPKART' in description_upper:
            return 'Flipkart'
        elif 'MYNTRA' in description_upper:
            return 'Myntra'
        elif 'UBER' in description_upper:
            return 'Uber'
        elif 'OLA' in description_upper:
            return 'Ola'
        elif 'PAYTM' in description_upper:
            return 'Paytm'
        elif 'PHONEPE' in description_upper:
            return 'PhonePe'
        elif 'GOOGLE PAY' in description_upper or 'GOOGLEPAY' in description_upper:
            return 'Google Pay'
        elif 'NETFLIX' in description_upper:
            return 'Netflix'
        elif 'PRIME' in description_upper and 'AMAZON' in description_upper:
            return 'Amazon Prime'
        elif 'SPOTIFY' in description_upper:
            return 'Spotify'
        else:
            # Take first 20 chars as merchant name
            return description[:20].strip()

    @staticmethod
    def get_top_merchants(bank_account_id, limit, user_id):
        """
        Get top spending merchants (debit transactions only).

        Args:
            bank_account_id: ID of the bank account
            limit: Number of top merchants to return (default: 10)
            user_id: ID of the requesting user

        Returns:
            {
                'merchants': [
                    {
                        'merchant': 'Amazon',
                        'total': 25000.00,
                        'count': 15,
                        'avg_transaction': 1666.67
                    }
                ],
                'limit': 10
            }
        """
        # Verify ownership
        if not BankAnalyticsService.verify_ownership(bank_account_id, user_id):
            return None

        # Get all debit transactions with merchant info
        transactions = db.session.query(
            Transaction.description,
            Transaction.merchant_name,
            Transaction.amount
        ).filter(
            Transaction.bank_account_id == bank_account_id,
            Transaction.transaction_type == 'debit',
            Transaction.verified == True
        ).all()

        # Group by merchant
        merchant_data = {}
        for txn in transactions:
            merchant = BankAnalyticsService.extract_merchant(
                txn.description,
                txn.merchant_name
            )

            if merchant not in merchant_data:
                merchant_data[merchant] = {
                    'total': 0,
                    'count': 0
                }

            merchant_data[merchant]['total'] += float(txn.amount)
            merchant_data[merchant]['count'] += 1

        # Convert to list and calculate averages
        merchants = []
        for merchant_name, data in merchant_data.items():
            merchants.append({
                'merchant': merchant_name,
                'total': data['total'],
                'count': data['count'],
                'avg_transaction': round(data['total'] / data['count'], 2)
            })

        # Sort by total spending (descending) and limit
        merchants.sort(key=lambda x: x['total'], reverse=True)
        merchants = merchants[:limit]

        return {
            'merchants': merchants,
            'limit': limit
        }
