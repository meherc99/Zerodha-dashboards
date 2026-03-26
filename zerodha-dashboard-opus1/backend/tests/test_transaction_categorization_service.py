"""
Tests for transaction categorization service.
"""
import pytest
from decimal import Decimal
from app.services.transaction_categorization_service import TransactionCategorizationService
from app.models.transaction_category import TransactionCategory
from app.database import db


@pytest.fixture
def sample_categories(app):
    """Create sample transaction categories with keywords"""
    with app.app_context():
        categories = [
            TransactionCategory(
                name='Groceries',
                icon='🛒',
                color='#4CAF50',
                keywords=['supermarket', 'grocery', 'walmart', 'target', 'costco', 'bigbazaar', 'dmart'],
                is_system=True
            ),
            TransactionCategory(
                name='Restaurants',
                icon='🍽️',
                color='#FF9800',
                keywords=['restaurant', 'cafe', 'swiggy', 'zomato', 'uber eats', 'dominos', 'mcdonald'],
                is_system=True
            ),
            TransactionCategory(
                name='Transport',
                icon='🚗',
                color='#2196F3',
                keywords=['uber', 'ola', 'lyft', 'taxi', 'petrol', 'gas', 'parking', 'toll'],
                is_system=True
            ),
            TransactionCategory(
                name='Salary',
                icon='💰',
                color='#8BC34A',
                keywords=['salary', 'payroll', 'income', 'wages'],
                is_system=True
            ),
            TransactionCategory(
                name='Bills & Utilities',
                icon='📱',
                color='#9C27B0',
                keywords=['electricity', 'water', 'internet', 'phone', 'mobile', 'recharge', 'bill payment'],
                is_system=True
            ),
            TransactionCategory(
                name='ATM Withdrawal',
                icon='🏧',
                color='#607D8B',
                keywords=['atm', 'cash withdrawal', 'withdrawal'],
                is_system=True
            ),
            TransactionCategory(
                name='Uncategorized',
                icon='❓',
                color='#9E9E9E',
                keywords=[],
                is_system=True
            )
        ]

        for cat in categories:
            db.session.add(cat)
        db.session.commit()

        yield categories

        # Cleanup
        for cat in categories:
            db.session.delete(cat)
        db.session.commit()


class TestTransactionCategorizationService:
    """Test cases for transaction categorization service"""

    def test_auto_categorize_groceries(self, app, sample_categories):
        """Test auto-categorization for grocery transaction"""
        with app.app_context():
            description = "Payment to BigBazaar Supermarket"
            amount = Decimal('2500.00')

            category_id, confidence = TransactionCategorizationService.auto_categorize(
                description, amount
            )

            assert category_id is not None
            category = TransactionCategory.query.get(category_id)
            assert category.name == 'Groceries'
            assert confidence == 0.8

    def test_auto_categorize_restaurant(self, app, sample_categories):
        """Test auto-categorization for restaurant transaction"""
        with app.app_context():
            description = "SWIGGY ONLINE ORD"
            amount = Decimal('450.00')

            category_id, confidence = TransactionCategorizationService.auto_categorize(
                description, amount
            )

            category = TransactionCategory.query.get(category_id)
            assert category.name == 'Restaurants'
            assert confidence == 0.8

    def test_auto_categorize_transport(self, app, sample_categories):
        """Test auto-categorization for transport transaction"""
        with app.app_context():
            description = "UPI-OLA CABS-PAYMENT"
            amount = Decimal('250.00')

            category_id, confidence = TransactionCategorizationService.auto_categorize(
                description, amount
            )

            category = TransactionCategory.query.get(category_id)
            assert category.name == 'Transport'
            assert confidence == 0.8

    def test_auto_categorize_salary(self, app, sample_categories):
        """Test auto-categorization for salary credit"""
        with app.app_context():
            description = "SALARY CREDIT FOR JAN 2024"
            amount = Decimal('75000.00')

            category_id, confidence = TransactionCategorizationService.auto_categorize(
                description, amount
            )

            category = TransactionCategory.query.get(category_id)
            assert category.name == 'Salary'
            assert confidence == 0.8

    def test_auto_categorize_bills(self, app, sample_categories):
        """Test auto-categorization for utility bills"""
        with app.app_context():
            description = "ELECTRICITY BILL PAYMENT"
            amount = Decimal('1200.00')

            category_id, confidence = TransactionCategorizationService.auto_categorize(
                description, amount
            )

            category = TransactionCategory.query.get(category_id)
            assert category.name == 'Bills & Utilities'
            assert confidence == 0.8

    def test_auto_categorize_atm_withdrawal(self, app, sample_categories):
        """Test auto-categorization for ATM withdrawal"""
        with app.app_context():
            description = "ATM WDL 123456 HDFC BANK"
            amount = Decimal('5000.00')

            category_id, confidence = TransactionCategorizationService.auto_categorize(
                description, amount
            )

            category = TransactionCategory.query.get(category_id)
            assert category.name == 'ATM Withdrawal'
            assert confidence == 0.8

    def test_auto_categorize_uncategorized(self, app, sample_categories):
        """Test auto-categorization defaults to Uncategorized for unknown transaction"""
        with app.app_context():
            description = "UNKNOWN MERCHANT XYZ123"
            amount = Decimal('999.00')

            category_id, confidence = TransactionCategorizationService.auto_categorize(
                description, amount
            )

            category = TransactionCategory.query.get(category_id)
            assert category.name == 'Uncategorized'
            assert confidence == 0.5

    def test_auto_categorize_case_insensitive(self, app, sample_categories):
        """Test that keyword matching is case-insensitive"""
        with app.app_context():
            # Test with different cases
            descriptions = [
                "payment to walmart",
                "PAYMENT TO WALMART",
                "Payment To WalMart",
                "pAyMeNt tO wAlMaRt"
            ]

            for desc in descriptions:
                category_id, confidence = TransactionCategorizationService.auto_categorize(
                    desc, Decimal('100.00')
                )
                category = TransactionCategory.query.get(category_id)
                assert category.name == 'Groceries'
                assert confidence == 0.8

    def test_auto_categorize_partial_match(self, app, sample_categories):
        """Test that partial keyword matches work"""
        with app.app_context():
            description = "UPI-ZOMATO-FOOD ORDER 12345"
            amount = Decimal('350.00')

            category_id, confidence = TransactionCategorizationService.auto_categorize(
                description, amount
            )

            category = TransactionCategory.query.get(category_id)
            assert category.name == 'Restaurants'
            assert confidence == 0.8

    def test_bulk_categorize(self, app, sample_categories):
        """Test bulk categorization of multiple transactions"""
        with app.app_context():
            transactions = [
                {
                    'description': 'SALARY CREDIT',
                    'amount': Decimal('50000.00'),
                    'transaction_type': 'credit'
                },
                {
                    'description': 'ATM WITHDRAWAL',
                    'amount': Decimal('5000.00'),
                    'transaction_type': 'debit'
                },
                {
                    'description': 'SWIGGY PAYMENT',
                    'amount': Decimal('450.00'),
                    'transaction_type': 'debit'
                },
                {
                    'description': 'UNKNOWN MERCHANT',
                    'amount': Decimal('100.00'),
                    'transaction_type': 'debit'
                }
            ]

            categorized = TransactionCategorizationService.bulk_categorize(transactions)

            assert len(categorized) == 4

            # Check first transaction (Salary)
            assert 'category_id' in categorized[0]
            assert 'category_confidence' in categorized[0]
            cat1 = TransactionCategory.query.get(categorized[0]['category_id'])
            assert cat1.name == 'Salary'
            assert categorized[0]['category_confidence'] == 0.8

            # Check second transaction (ATM)
            cat2 = TransactionCategory.query.get(categorized[1]['category_id'])
            assert cat2.name == 'ATM Withdrawal'
            assert categorized[1]['category_confidence'] == 0.8

            # Check third transaction (Restaurant)
            cat3 = TransactionCategory.query.get(categorized[2]['category_id'])
            assert cat3.name == 'Restaurants'
            assert categorized[2]['category_confidence'] == 0.8

            # Check fourth transaction (Uncategorized)
            cat4 = TransactionCategory.query.get(categorized[3]['category_id'])
            assert cat4.name == 'Uncategorized'
            assert categorized[3]['category_confidence'] == 0.5

    def test_bulk_categorize_empty_list(self, app, sample_categories):
        """Test bulk categorization with empty list"""
        with app.app_context():
            transactions = []
            categorized = TransactionCategorizationService.bulk_categorize(transactions)
            assert categorized == []

    def test_auto_categorize_first_match_priority(self, app, sample_categories):
        """Test that first matching category is returned when multiple keywords match"""
        with app.app_context():
            # "uber" is in both Transport and Restaurants (uber eats)
            # Should match Transport first (comes first in our sample categories)
            description = "UBER RIDE PAYMENT"
            amount = Decimal('200.00')

            category_id, confidence = TransactionCategorizationService.auto_categorize(
                description, amount
            )

            category = TransactionCategory.query.get(category_id)
            # This will match Transport because "uber" appears in Transport keywords
            assert category.name == 'Transport'
            assert confidence == 0.8
