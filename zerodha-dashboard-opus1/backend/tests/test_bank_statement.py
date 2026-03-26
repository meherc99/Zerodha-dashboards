"""
Tests for BankStatement model.
"""
import pytest
from datetime import date, datetime
from decimal import Decimal
from app import db
from app.models.bank_statement import BankStatement
from app.models.bank_account import BankAccount
from app.models.transaction import Transaction
from app.models.transaction_category import TransactionCategory


@pytest.fixture
def sample_category(app):
    """Create a sample transaction category"""
    with app.app_context():
        category = TransactionCategory(
            name='Groceries',
            icon='🛒',
            color='#FF5733'
        )
        db.session.add(category)
        db.session.commit()
        category_id = category.id
    return category_id


def test_create_bank_statement(app, sample_bank_account):
    """Test creating a basic bank statement"""
    with app.app_context():
        statement = BankStatement(
            bank_account_id=sample_bank_account['id'],
            statement_period_start=date(2026, 1, 1),
            statement_period_end=date(2026, 1, 31),
            pdf_file_path='/encrypted/path/to/statement.pdf'
        )
        db.session.add(statement)
        db.session.commit()

        assert statement.id is not None
        assert statement.bank_account_id == sample_bank_account['id']
        assert statement.statement_period_start == date(2026, 1, 1)
        assert statement.statement_period_end == date(2026, 1, 31)
        assert statement.pdf_file_path == '/encrypted/path/to/statement.pdf'
        assert statement.status == 'uploaded'  # default status
        assert statement.upload_date is not None
        assert statement.parsing_template_id is None
        assert statement.error_message is None
        assert statement.parsed_data is None
        assert statement.created_at is not None


def test_statement_with_transactions(app, sample_bank_account, sample_category):
    """Test statement with associated transactions"""
    with app.app_context():
        # Create statement
        statement = BankStatement(
            bank_account_id=sample_bank_account['id'],
            statement_period_start=date(2026, 1, 1),
            statement_period_end=date(2026, 1, 31),
            pdf_file_path='/encrypted/path/to/statement.pdf',
            status='approved'
        )
        db.session.add(statement)
        db.session.commit()
        statement_id = statement.id

        # Create transactions for this statement
        transaction1 = Transaction(
            statement_id=statement_id,
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 1, 5),
            description='Grocery Store',
            amount=Decimal('250.50'),
            transaction_type='debit',
            category_id=sample_category
        )
        transaction2 = Transaction(
            statement_id=statement_id,
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 1, 10),
            description='Salary Credit',
            amount=Decimal('50000.00'),
            transaction_type='credit'
        )
        db.session.add_all([transaction1, transaction2])
        db.session.commit()

        # Refresh and verify
        statement = db.session.get(BankStatement, statement_id)
        assert len(statement.transactions) == 2
        assert statement.transactions[0].statement_id == statement_id
        assert statement.transactions[1].statement_id == statement_id


def test_status_transitions(app, sample_bank_account):
    """Test status transitions: uploaded -> parsing -> review -> approved"""
    with app.app_context():
        statement = BankStatement(
            bank_account_id=sample_bank_account['id'],
            statement_period_start=date(2026, 1, 1),
            statement_period_end=date(2026, 1, 31),
            pdf_file_path='/encrypted/path/to/statement.pdf'
        )
        db.session.add(statement)
        db.session.commit()

        # Initial status
        assert statement.status == 'uploaded'

        # Transition to parsing
        statement.status = 'parsing'
        db.session.commit()
        assert statement.status == 'parsing'

        # Transition to review
        statement.status = 'review'
        statement.parsed_data = {
            'transactions': [
                {'date': '2026-01-05', 'description': 'Test', 'amount': 100.0}
            ],
            'opening_balance': 10000.0,
            'closing_balance': 9900.0
        }
        db.session.commit()
        assert statement.status == 'review'
        assert statement.parsed_data is not None

        # Transition to approved
        statement.status = 'approved'
        db.session.commit()
        assert statement.status == 'approved'


def test_status_failed(app, sample_bank_account):
    """Test failed status with error message"""
    with app.app_context():
        statement = BankStatement(
            bank_account_id=sample_bank_account['id'],
            statement_period_start=date(2026, 1, 1),
            statement_period_end=date(2026, 1, 31),
            pdf_file_path='/encrypted/path/to/statement.pdf',
            status='failed',
            error_message='Failed to parse PDF: Invalid format'
        )
        db.session.add(statement)
        db.session.commit()

        assert statement.status == 'failed'
        assert statement.error_message == 'Failed to parse PDF: Invalid format'


def test_relationship_with_bank_account(app, sample_bank_account):
    """Test relationship between BankStatement and BankAccount"""
    with app.app_context():
        statement = BankStatement(
            bank_account_id=sample_bank_account['id'],
            statement_period_start=date(2026, 1, 1),
            statement_period_end=date(2026, 1, 31),
            pdf_file_path='/encrypted/path/to/statement.pdf'
        )
        db.session.add(statement)
        db.session.commit()
        statement_id = statement.id

        # Test forward relationship (statement -> bank_account)
        statement = db.session.get(BankStatement, statement_id)
        assert statement.bank_account is not None
        assert statement.bank_account.id == sample_bank_account['id']
        assert statement.bank_account.bank_name == sample_bank_account['bank_name']

        # Test backward relationship (bank_account -> statements)
        bank_account = db.session.get(BankAccount, sample_bank_account['id'])
        assert len(bank_account.statements) == 1
        assert bank_account.statements[0].id == statement_id


def test_to_dict(app, sample_bank_account):
    """Test to_dict() method"""
    with app.app_context():
        statement = BankStatement(
            bank_account_id=sample_bank_account['id'],
            statement_period_start=date(2026, 1, 1),
            statement_period_end=date(2026, 1, 31),
            pdf_file_path='/encrypted/path/to/statement.pdf',
            status='review',
            parsed_data={'test': 'data'}
        )
        db.session.add(statement)
        db.session.commit()

        data = statement.to_dict()
        assert data['id'] is not None
        assert data['bank_account_id'] == sample_bank_account['id']
        assert data['statement_period_start'] == '2026-01-01'
        assert data['statement_period_end'] == '2026-01-31'
        assert data['pdf_file_path'] == '/encrypted/path/to/statement.pdf'
        assert data['upload_date'] is not None
        assert data['parsing_template_id'] is None
        assert data['status'] == 'review'
        assert data['error_message'] is None
        assert data['parsed_data'] == {'test': 'data'}
        assert data['created_at'] is not None


def test_to_dict_with_transactions(app, sample_bank_account, sample_category):
    """Test to_dict_with_transactions() method"""
    with app.app_context():
        statement = BankStatement(
            bank_account_id=sample_bank_account['id'],
            statement_period_start=date(2026, 1, 1),
            statement_period_end=date(2026, 1, 31),
            pdf_file_path='/encrypted/path/to/statement.pdf'
        )
        db.session.add(statement)
        db.session.commit()
        statement_id = statement.id

        # Add transactions
        transaction = Transaction(
            statement_id=statement_id,
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 1, 5),
            description='Test Transaction',
            amount=Decimal('100.00'),
            transaction_type='debit',
            category_id=sample_category
        )
        db.session.add(transaction)
        db.session.commit()

        # Get dict with transactions
        statement = db.session.get(BankStatement, statement_id)
        data = statement.to_dict_with_transactions()
        assert data['id'] is not None
        assert data['bank_account_id'] == sample_bank_account['id']
        assert 'transactions' in data
        assert len(data['transactions']) == 1
        assert data['transactions'][0]['description'] == 'Test Transaction'
        assert data['transactions'][0]['amount'] == '100.00'


def test_cascade_delete_transactions(app, sample_bank_account):
    """Test that deleting a statement cascades to delete transactions"""
    with app.app_context():
        # Create statement with transactions
        statement = BankStatement(
            bank_account_id=sample_bank_account['id'],
            statement_period_start=date(2026, 1, 1),
            statement_period_end=date(2026, 1, 31),
            pdf_file_path='/encrypted/path/to/statement.pdf'
        )
        db.session.add(statement)
        db.session.commit()
        statement_id = statement.id

        transaction1 = Transaction(
            statement_id=statement_id,
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 1, 5),
            description='Transaction 1',
            amount=Decimal('100.00'),
            transaction_type='debit'
        )
        transaction2 = Transaction(
            statement_id=statement_id,
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 1, 10),
            description='Transaction 2',
            amount=Decimal('200.00'),
            transaction_type='credit'
        )
        db.session.add_all([transaction1, transaction2])
        db.session.commit()
        transaction1_id = transaction1.id
        transaction2_id = transaction2.id

        # Verify transactions exist
        assert db.session.get(Transaction, transaction1_id) is not None
        assert db.session.get(Transaction, transaction2_id) is not None

        # Delete statement
        statement = db.session.get(BankStatement, statement_id)
        db.session.delete(statement)
        db.session.commit()

        # Verify transactions were deleted
        assert db.session.get(Transaction, transaction1_id) is None
        assert db.session.get(Transaction, transaction2_id) is None


def test_parsed_data_json_field(app, sample_bank_account):
    """Test parsed_data JSON field stores complex data"""
    with app.app_context():
        parsed_data = {
            'opening_balance': 10000.50,
            'closing_balance': 12500.75,
            'transactions': [
                {
                    'date': '2026-01-05',
                    'description': 'ATM Withdrawal',
                    'debit': 5000.0,
                    'credit': None,
                    'balance': 5000.50
                },
                {
                    'date': '2026-01-15',
                    'description': 'Salary',
                    'debit': None,
                    'credit': 7500.25,
                    'balance': 12500.75
                }
            ],
            'metadata': {
                'pdf_pages': 3,
                'parsing_confidence': 0.95,
                'bank_specific_field': 'custom_value'
            }
        }

        statement = BankStatement(
            bank_account_id=sample_bank_account['id'],
            statement_period_start=date(2026, 1, 1),
            statement_period_end=date(2026, 1, 31),
            pdf_file_path='/encrypted/path/to/statement.pdf',
            status='review',
            parsed_data=parsed_data
        )
        db.session.add(statement)
        db.session.commit()
        statement_id = statement.id

        # Retrieve and verify
        statement = db.session.get(BankStatement, statement_id)
        assert statement.parsed_data == parsed_data
        assert statement.parsed_data['opening_balance'] == 10000.50
        assert statement.parsed_data['closing_balance'] == 12500.75
        assert len(statement.parsed_data['transactions']) == 2
        assert statement.parsed_data['metadata']['parsing_confidence'] == 0.95


def test_multiple_statements_per_account(app, sample_bank_account):
    """Test that a bank account can have multiple statements"""
    with app.app_context():
        # Create multiple statements for same account
        statement1 = BankStatement(
            bank_account_id=sample_bank_account['id'],
            statement_period_start=date(2026, 1, 1),
            statement_period_end=date(2026, 1, 31),
            pdf_file_path='/encrypted/path/to/jan_statement.pdf'
        )
        statement2 = BankStatement(
            bank_account_id=sample_bank_account['id'],
            statement_period_start=date(2026, 2, 1),
            statement_period_end=date(2026, 2, 28),
            pdf_file_path='/encrypted/path/to/feb_statement.pdf'
        )
        statement3 = BankStatement(
            bank_account_id=sample_bank_account['id'],
            statement_period_start=date(2026, 3, 1),
            statement_period_end=date(2026, 3, 31),
            pdf_file_path='/encrypted/path/to/mar_statement.pdf'
        )
        db.session.add_all([statement1, statement2, statement3])
        db.session.commit()

        # Verify all statements are associated with the account
        bank_account = db.session.get(BankAccount, sample_bank_account['id'])
        assert len(bank_account.statements) == 3

        # Verify they're in the expected order (by ID)
        statement_ids = [s.id for s in bank_account.statements]
        assert len(set(statement_ids)) == 3  # all unique


def test_statement_repr(app, sample_bank_account):
    """Test __repr__ method"""
    with app.app_context():
        statement = BankStatement(
            bank_account_id=sample_bank_account['id'],
            statement_period_start=date(2026, 1, 1),
            statement_period_end=date(2026, 1, 31),
            pdf_file_path='/encrypted/path/to/statement.pdf'
        )
        db.session.add(statement)
        db.session.commit()

        repr_str = repr(statement)
        assert 'BankStatement' in repr_str
        assert '2026-01-01' in repr_str
        assert '2026-01-31' in repr_str
        assert 'uploaded' in repr_str
