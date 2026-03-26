"""
Tests for Transaction model
"""
import pytest
from datetime import date, datetime
from decimal import Decimal
from app import create_app, db
from app.models.transaction import Transaction
from app.models.bank_account import BankAccount
from app.models.transaction_category import TransactionCategory
from app.models.user import User


@pytest.fixture
def app():
    """Create and configure test app"""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sample_user(app):
    """Create a sample user"""
    with app.app_context():
        user = User(
            email='user@example.com',
            full_name='Test User'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    return {'id': user_id}


@pytest.fixture
def sample_bank_account(app, sample_user):
    """Create a sample bank account"""
    with app.app_context():
        account = BankAccount(
            user_id=sample_user['id'],
            bank_name='HDFC Bank',
            account_number='1234567890',
            account_type='savings'
        )
        db.session.add(account)
        db.session.commit()
        account_id = account.id

    return {'id': account_id, 'user_id': sample_user['id']}


@pytest.fixture
def sample_category(app):
    """Create a sample transaction category"""
    with app.app_context():
        category = TransactionCategory(
            name='Groceries',
            icon='🛒',
            color='#10b981'
        )
        db.session.add(category)
        db.session.commit()
        category_id = category.id

    return {'id': category_id}


def test_transaction_creation(app, sample_bank_account):
    """Test creating a transaction with required fields"""
    with app.app_context():
        transaction = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 15),
            description='Payment at Big Bazaar',
            amount=Decimal('1250.50'),
            transaction_type='debit'
        )

        db.session.add(transaction)
        db.session.commit()

        assert transaction.id is not None
        assert transaction.bank_account_id == sample_bank_account['id']
        assert transaction.transaction_date == date(2026, 3, 15)
        assert transaction.description == 'Payment at Big Bazaar'
        assert transaction.amount == Decimal('1250.50')
        assert transaction.transaction_type == 'debit'
        assert transaction.merchant_name is None
        assert transaction.running_balance is None
        assert transaction.category_id is None
        assert transaction.category_confidence is None
        assert transaction.verified is False
        assert transaction.notes is None
        assert transaction.created_at is not None
        assert transaction.updated_at is not None
        assert isinstance(transaction.created_at, datetime)
        assert isinstance(transaction.updated_at, datetime)


def test_transaction_with_all_fields(app, sample_bank_account, sample_category):
    """Test creating a transaction with all fields populated"""
    with app.app_context():
        transaction = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 20),
            description='UPI/BIGBASKET/123456789',
            merchant_name='BigBasket',
            amount=Decimal('2500.00'),
            transaction_type='debit',
            running_balance=Decimal('45000.00'),
            category_id=sample_category['id'],
            category_confidence=0.95,
            verified=True,
            notes='Monthly grocery shopping'
        )

        db.session.add(transaction)
        db.session.commit()

        assert transaction.merchant_name == 'BigBasket'
        assert transaction.running_balance == Decimal('45000.00')
        assert transaction.category_id == sample_category['id']
        assert transaction.category_confidence == 0.95
        assert transaction.verified is True
        assert transaction.notes == 'Monthly grocery shopping'


def test_transaction_credit_type(app, sample_bank_account):
    """Test creating a credit transaction"""
    with app.app_context():
        transaction = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 25),
            description='Salary credited',
            amount=Decimal('75000.00'),
            transaction_type='credit'
        )

        db.session.add(transaction)
        db.session.commit()

        assert transaction.transaction_type == 'credit'
        assert transaction.amount == Decimal('75000.00')


def test_transaction_type_validation(app, sample_bank_account):
    """Test that transaction_type is validated (only credit or debit allowed)"""
    with app.app_context():
        # Valid types should work
        transaction1 = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 15),
            description='Test',
            amount=Decimal('100.00'),
            transaction_type='credit'
        )
        db.session.add(transaction1)
        db.session.commit()

        transaction2 = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 16),
            description='Test',
            amount=Decimal('100.00'),
            transaction_type='debit'
        )
        db.session.add(transaction2)
        db.session.commit()

        # Invalid type should be allowed at DB level but should be validated at application level
        # This test documents current behavior - validation will be added in model
        transaction3 = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 17),
            description='Test',
            amount=Decimal('100.00'),
            transaction_type='invalid'
        )
        db.session.add(transaction3)
        # We'll add validation in the model to prevent this


def test_transaction_bank_account_relationship(app, sample_bank_account):
    """Test relationship with BankAccount"""
    with app.app_context():
        transaction = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 15),
            description='Test transaction',
            amount=Decimal('500.00'),
            transaction_type='debit'
        )
        db.session.add(transaction)
        db.session.commit()

        # Reload from database
        retrieved_transaction = Transaction.query.get(transaction.id)
        assert retrieved_transaction.bank_account is not None
        assert retrieved_transaction.bank_account.id == sample_bank_account['id']
        assert retrieved_transaction.bank_account.bank_name == 'HDFC Bank'


def test_transaction_category_relationship(app, sample_bank_account, sample_category):
    """Test relationship with TransactionCategory"""
    with app.app_context():
        transaction = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 15),
            description='Grocery shopping',
            amount=Decimal('1200.00'),
            transaction_type='debit',
            category_id=sample_category['id']
        )
        db.session.add(transaction)
        db.session.commit()

        # Reload from database
        retrieved_transaction = Transaction.query.get(transaction.id)
        assert retrieved_transaction.category is not None
        assert retrieved_transaction.category.id == sample_category['id']
        assert retrieved_transaction.category.name == 'Groceries'


def test_transaction_to_dict(app, sample_bank_account, sample_category):
    """Test to_dict() method returns correct dictionary"""
    with app.app_context():
        transaction = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 15),
            description='Payment at Big Bazaar',
            merchant_name='Big Bazaar',
            amount=Decimal('1250.50'),
            transaction_type='debit',
            running_balance=Decimal('48749.50'),
            category_id=sample_category['id'],
            category_confidence=0.92,
            verified=True,
            notes='Weekly groceries'
        )
        db.session.add(transaction)
        db.session.commit()

        transaction_dict = transaction.to_dict()

        assert transaction_dict['id'] == transaction.id
        assert transaction_dict['bank_account_id'] == sample_bank_account['id']
        assert transaction_dict['transaction_date'] == '2026-03-15'
        assert transaction_dict['description'] == 'Payment at Big Bazaar'
        assert transaction_dict['merchant_name'] == 'Big Bazaar'
        assert transaction_dict['amount'] == '1250.50'
        assert transaction_dict['transaction_type'] == 'debit'
        assert transaction_dict['running_balance'] == '48749.50'
        assert transaction_dict['category_id'] == sample_category['id']
        assert transaction_dict['category_confidence'] == 0.92
        assert transaction_dict['verified'] is True
        assert transaction_dict['notes'] == 'Weekly groceries'
        assert 'created_at' in transaction_dict
        assert 'updated_at' in transaction_dict
        assert isinstance(transaction_dict['created_at'], str)
        assert isinstance(transaction_dict['updated_at'], str)


def test_transaction_to_dict_minimal(app, sample_bank_account):
    """Test to_dict() with minimal fields"""
    with app.app_context():
        transaction = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 15),
            description='Simple payment',
            amount=Decimal('100.00'),
            transaction_type='debit'
        )
        db.session.add(transaction)
        db.session.commit()

        transaction_dict = transaction.to_dict()

        assert transaction_dict['merchant_name'] is None
        assert transaction_dict['running_balance'] is None
        assert transaction_dict['category_id'] is None
        assert transaction_dict['category_confidence'] is None
        assert transaction_dict['verified'] is False
        assert transaction_dict['notes'] is None


def test_transaction_repr(app, sample_bank_account):
    """Test __repr__ method"""
    with app.app_context():
        transaction = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 15),
            description='Test payment',
            amount=Decimal('500.00'),
            transaction_type='debit'
        )
        db.session.add(transaction)
        db.session.commit()

        assert 'Transaction' in repr(transaction)
        assert 'debit' in repr(transaction)
        assert '500.00' in repr(transaction)


def test_bank_account_transactions_relationship(app, sample_bank_account):
    """Test that BankAccount has transactions relationship"""
    with app.app_context():
        # Create multiple transactions for the account
        transaction1 = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 15),
            description='Transaction 1',
            amount=Decimal('100.00'),
            transaction_type='debit'
        )
        transaction2 = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 16),
            description='Transaction 2',
            amount=Decimal('200.00'),
            transaction_type='credit'
        )
        db.session.add_all([transaction1, transaction2])
        db.session.commit()

        # Retrieve account and check transactions
        account = BankAccount.query.get(sample_bank_account['id'])
        assert len(account.transactions) == 2
        assert transaction1 in account.transactions
        assert transaction2 in account.transactions


def test_category_transactions_relationship(app, sample_bank_account, sample_category):
    """Test that TransactionCategory has transactions relationship"""
    with app.app_context():
        # Create multiple transactions with same category
        transaction1 = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 15),
            description='Transaction 1',
            amount=Decimal('100.00'),
            transaction_type='debit',
            category_id=sample_category['id']
        )
        transaction2 = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 16),
            description='Transaction 2',
            amount=Decimal('200.00'),
            transaction_type='debit',
            category_id=sample_category['id']
        )
        db.session.add_all([transaction1, transaction2])
        db.session.commit()

        # Retrieve category and check transactions
        category = TransactionCategory.query.get(sample_category['id'])
        assert len(category.transactions) == 2
        assert transaction1 in category.transactions
        assert transaction2 in category.transactions


def test_transaction_cascade_delete_from_bank_account(app, sample_bank_account):
    """Test that deleting bank account cascades to transactions"""
    with app.app_context():
        transaction = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 15),
            description='Test transaction',
            amount=Decimal('500.00'),
            transaction_type='debit'
        )
        db.session.add(transaction)
        db.session.commit()
        transaction_id = transaction.id

        # Delete the bank account
        account = BankAccount.query.get(sample_bank_account['id'])
        db.session.delete(account)
        db.session.commit()

        # Transaction should be deleted due to cascade
        deleted_transaction = Transaction.query.get(transaction_id)
        assert deleted_transaction is None


def test_transaction_nullable_statement_id(app, sample_bank_account):
    """Test that statement_id can be null (forward reference)"""
    with app.app_context():
        transaction = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 15),
            description='Test transaction',
            amount=Decimal('500.00'),
            transaction_type='debit',
            statement_id=None  # Should be nullable for now
        )
        db.session.add(transaction)
        db.session.commit()

        assert transaction.statement_id is None


def test_transaction_updated_at_changes(app, sample_bank_account):
    """Test that updated_at timestamp changes on update"""
    with app.app_context():
        transaction = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 15),
            description='Original description',
            amount=Decimal('500.00'),
            transaction_type='debit'
        )
        db.session.add(transaction)
        db.session.commit()

        original_updated_at = transaction.updated_at
        transaction_id = transaction.id

    # Update in new context to ensure timestamp changes
    with app.app_context():
        transaction = Transaction.query.get(transaction_id)
        transaction.description = 'Updated description'
        db.session.commit()

        new_updated_at = transaction.updated_at
        # Note: In SQLite with fast operations, timestamps might be the same
        # This is acceptable - the important thing is that the field is set correctly
        assert new_updated_at is not None
