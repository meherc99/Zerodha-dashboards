"""
Tests for PDF parsing service.
"""
import os
import pytest
from datetime import date
from decimal import Decimal
from io import BytesIO
import pdfplumber
from app.services.pdf_parser_service import PDFParserService
from app.models.bank_statement import BankStatement
from app.models.bank_account import BankAccount
from app.models.user import User
from app.database import db


@pytest.fixture
def test_user(app):
    """Create a test user"""
    with app.app_context():
        user = User(email='test@example.com', full_name='Test User')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def test_bank_account(app, test_user):
    """Create a test bank account"""
    with app.app_context():
        account = BankAccount(
            user_id=test_user.id,
            bank_name='HDFC Bank',
            account_number='1234567890',
            account_type='savings'
        )
        db.session.add(account)
        db.session.commit()
        yield account
        db.session.delete(account)
        db.session.commit()


@pytest.fixture
def sample_hdfc_statement(app, test_bank_account, tmp_path):
    """Create a sample bank statement record with PDF file"""
    with app.app_context():
        # Create a minimal test PDF file
        pdf_path = tmp_path / "test_hdfc_statement.pdf"

        # We'll create a real PDF using reportlab for testing
        # For now, just create a placeholder - we'll mock pdfplumber in tests
        pdf_path.write_bytes(b"%PDF-1.4\ntest")

        statement = BankStatement(
            bank_account_id=test_bank_account.id,
            statement_period_start=date(2024, 1, 1),
            statement_period_end=date(2024, 1, 31),
            pdf_file_path=str(pdf_path),
            status='uploaded'
        )
        db.session.add(statement)
        db.session.commit()
        yield statement
        db.session.delete(statement)
        db.session.commit()


class TestPDFParserService:
    """Test cases for PDF parser service"""

    def test_extract_text_basic(self, app, sample_hdfc_statement, monkeypatch):
        """Test basic text extraction from PDF"""
        with app.app_context():
            # Mock pdfplumber
            mock_text = "HDFC Bank\nStatement of Account\nTransaction Details"

            class MockPage:
                def extract_text(self):
                    return mock_text

            class MockPDF:
                pages = [MockPage()]
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass

            def mock_open(*args, **kwargs):
                return MockPDF()

            monkeypatch.setattr(pdfplumber, 'open', mock_open)

            result = PDFParserService.extract_text(sample_hdfc_statement.pdf_file_path)
            assert "HDFC Bank" in result
            assert "Transaction Details" in result

    def test_detect_bank_name_hdfc(self, app):
        """Test bank name detection for HDFC Bank"""
        with app.app_context():
            text = "HDFC Bank Limited\nStatement of Account"
            bank_name = PDFParserService.detect_bank_name(text)
            assert bank_name == "HDFC Bank"

    def test_detect_bank_name_sbi(self, app):
        """Test bank name detection for SBI"""
        with app.app_context():
            text = "State Bank of India\nAccount Statement"
            bank_name = PDFParserService.detect_bank_name(text)
            assert bank_name == "SBI"

    def test_detect_bank_name_icici(self, app):
        """Test bank name detection for ICICI Bank"""
        with app.app_context():
            text = "ICICI Bank Ltd\nStatement"
            bank_name = PDFParserService.detect_bank_name(text)
            assert bank_name == "ICICI Bank"

    def test_detect_bank_name_axis(self, app):
        """Test bank name detection for Axis Bank"""
        with app.app_context():
            text = "AXIS BANK\nSavings Account Statement"
            bank_name = PDFParserService.detect_bank_name(text)
            assert bank_name == "Axis Bank"

    def test_detect_bank_name_unknown(self, app):
        """Test bank name detection for unknown bank"""
        with app.app_context():
            text = "Random Bank\nStatement"
            bank_name = PDFParserService.detect_bank_name(text)
            assert bank_name == "Unknown"

    def test_identify_transaction_table(self, app):
        """Test identifying transaction table from extracted tables"""
        with app.app_context():
            # Table without date column (not a transaction table)
            table1 = [
                ['Description', 'Amount', 'Balance'],
                ['Payment', '1000', '5000']
            ]

            # Transaction table with date column
            table2 = [
                ['Date', 'Description', 'Debit', 'Credit', 'Balance'],
                ['01/01/2024', 'Salary', '', '50000', '50000'],
                ['05/01/2024', 'ATM Withdrawal', '5000', '', '45000']
            ]

            tables = [table1, table2]
            result = PDFParserService.identify_transaction_table(tables)
            assert result == table2

    def test_identify_transaction_table_none_found(self, app):
        """Test when no transaction table is found"""
        with app.app_context():
            tables = [
                [['Header1', 'Header2'], ['Value1', 'Value2']],
                [['Col1', 'Col2'], ['Data1', 'Data2']]
            ]
            result = PDFParserService.identify_transaction_table(tables)
            assert result is None

    def test_identify_transaction_tables_preserves_page_order(self, app):
        """All compatible page tables are returned in extraction order."""
        with app.app_context():
            headers = ['Date', 'Description', 'Debit', 'Credit', 'Balance']
            first_page = [
                headers,
                ['01/01/2024', 'Salary', '', '1000', '1000'],
            ]
            account_summary = [
                ['Label', 'Value', 'Other'],
                ['Opening', '0', ''],
            ]
            second_page = [
                headers,
                ['02/01/2024', 'Groceries', '100', '', '900'],
            ]

            result = PDFParserService.identify_transaction_tables([
                account_summary,
                first_page,
                second_page,
            ])

            assert result == [first_page, second_page]

    def test_extract_with_pdfplumber_combines_tables_and_skips_headers(
        self,
        app,
        monkeypatch,
    ):
        """Multi-page rows are parsed once in order, without repeated headers."""
        with app.app_context():
            headers = ['Date', 'Description', 'Debit', 'Credit', 'Balance']
            first_page = [
                headers,
                ['01/01/2024', 'Salary', '', '1000', '1000'],
                ['02/01/2024', 'Groceries', '100', '', '900'],
            ]
            second_page = [
                headers,
                ['03/01/2024', 'Refund', '', '50', '950'],
                headers,
                ['04/01/2024', 'Transport', '25', '', '925'],
            ]
            monkeypatch.setattr(
                PDFParserService,
                'extract_tables_from_pdf',
                staticmethod(lambda _path: [first_page, second_page]),
            )

            parsed_rows = []
            original_parse = PDFParserService.parse_transaction_row

            def parse_once(row, table_headers):
                parsed_rows.append(row)
                return original_parse(row, table_headers)

            monkeypatch.setattr(
                PDFParserService,
                'parse_transaction_row',
                staticmethod(parse_once),
            )

            transactions, confidence = PDFParserService.extract_with_pdfplumber(
                'two-page-statement.pdf'
            )

            assert [txn['description'] for txn in transactions] == [
                'Salary',
                'Groceries',
                'Refund',
                'Transport',
            ]
            assert len(parsed_rows) == 4
            assert all(row != headers for row in parsed_rows)
            assert confidence == 0.8

    def test_extract_with_pdfplumber_reads_every_pdf_page(
        self,
        app,
        monkeypatch,
    ):
        """The standard parser must retain transactions from every PDF page."""
        with app.app_context():
            headers = ['Date', 'Description', 'Debit', 'Credit', 'Balance']

            class MockPage:
                def __init__(self, tables):
                    self.tables = tables

                def extract_tables(self):
                    return self.tables

            class MockPDF:
                pages = [
                    MockPage([
                        [
                            headers,
                            ['01/01/2024', 'Salary', '', '1000', '1000'],
                        ],
                    ]),
                    MockPage([
                        [
                            ['Label', 'Value', 'Other'],
                            ['Closing balance', '900', ''],
                        ],
                        [
                            headers,
                            ['02/01/2024', 'Groceries', '100', '', '900'],
                        ],
                    ]),
                ]

                def __enter__(self):
                    return self

                def __exit__(self, *_args):
                    pass

            monkeypatch.setattr(
                pdfplumber,
                'open',
                lambda *_args, **_kwargs: MockPDF(),
            )

            transactions, confidence = PDFParserService.extract_with_pdfplumber(
                'two-page-statement.pdf'
            )

            assert [txn['description'] for txn in transactions] == [
                'Salary',
                'Groceries',
            ]
            assert confidence == 0.8

    def test_extract_with_pdfplumber_accepts_headerless_page_continuation(
        self,
        app,
        monkeypatch,
    ):
        """A continuation page may safely inherit the first page's headers."""
        with app.app_context():
            headers = ['Date', 'Description', 'Debit', 'Credit', 'Balance']
            first_page = [
                headers,
                ['01/01/2024', 'Salary', '', '1000', '1000'],
            ]
            second_page = [
                ['02/01/2024', 'Groceries', '100', '', '900'],
                ['03/01/2024', 'Refund', '', '50', '950'],
            ]
            monkeypatch.setattr(
                PDFParserService,
                'extract_tables_from_pdf',
                staticmethod(lambda _path: [first_page, second_page]),
            )

            transactions, confidence = PDFParserService.extract_with_pdfplumber(
                'headerless-continuation.pdf'
            )

            assert [txn['description'] for txn in transactions] == [
                'Salary',
                'Groceries',
                'Refund',
            ]
            assert confidence == 0.8

    def test_parse_transaction_row_debit_credit_columns(self, app):
        """Test parsing a transaction row with separate debit/credit columns"""
        with app.app_context():
            row = ['01/01/2024', 'ATM Withdrawal', '5000', '', '45000']
            headers = ['Date', 'Description', 'Debit', 'Credit', 'Balance']

            transaction = PDFParserService.parse_transaction_row(row, headers)

            assert transaction is not None
            assert transaction['date'] == date(2024, 1, 1)
            assert transaction['description'] == 'ATM Withdrawal'
            assert transaction['amount'] == Decimal('5000')
            assert transaction['transaction_type'] == 'debit'
            assert transaction['balance'] == Decimal('45000')

    def test_parse_transaction_row_credit(self, app):
        """Test parsing a credit transaction"""
        with app.app_context():
            row = ['05/01/2024', 'Salary Credit', '', '50000', '95000']
            headers = ['Date', 'Description', 'Debit', 'Credit', 'Balance']

            transaction = PDFParserService.parse_transaction_row(row, headers)

            assert transaction is not None
            assert transaction['date'] == date(2024, 1, 5)
            assert transaction['description'] == 'Salary Credit'
            assert transaction['amount'] == Decimal('50000')
            assert transaction['transaction_type'] == 'credit'
            assert transaction['balance'] == Decimal('95000')

    def test_parse_transaction_row_parses_date_once(self, app, monkeypatch):
        """A row's date should not be parsed redundantly."""
        with app.app_context():
            parse_calls = []
            original_parse_date = PDFParserService._parse_date

            def count_parse(date_value):
                parse_calls.append(date_value)
                return original_parse_date(date_value)

            monkeypatch.setattr(
                PDFParserService,
                '_parse_date',
                staticmethod(count_parse),
            )

            transaction = PDFParserService.parse_transaction_row(
                ['05/01/2024', 'Salary Credit', '', '50000', '95000'],
                ['Date', 'Description', 'Debit', 'Credit', 'Balance'],
            )

            assert transaction is not None
            assert parse_calls == ['05/01/2024']

    def test_parse_transaction_row_invalid_date(self, app):
        """Test parsing row with invalid date returns None"""
        with app.app_context():
            row = ['Invalid Date', 'Some Transaction', '1000', '', '5000']
            headers = ['Date', 'Description', 'Debit', 'Credit', 'Balance']

            transaction = PDFParserService.parse_transaction_row(row, headers)
            assert transaction is None

    def test_validate_transactions_valid(self, app):
        """Test validation of transactions with consistent balances"""
        with app.app_context():
            transactions = [
                {
                    'date': date(2024, 1, 1),
                    'description': 'Opening Balance',
                    'amount': Decimal('0'),
                    'transaction_type': 'credit',
                    'balance': Decimal('50000')
                },
                {
                    'date': date(2024, 1, 5),
                    'description': 'ATM Withdrawal',
                    'amount': Decimal('5000'),
                    'transaction_type': 'debit',
                    'balance': Decimal('45000')
                },
                {
                    'date': date(2024, 1, 10),
                    'description': 'Salary',
                    'amount': Decimal('30000'),
                    'transaction_type': 'credit',
                    'balance': Decimal('75000')
                }
            ]

            is_valid, errors = PDFParserService.validate_transactions(transactions)
            assert is_valid is True
            assert len(errors) == 0

    def test_validate_transactions_balance_mismatch(self, app):
        """Test validation catches balance inconsistencies"""
        with app.app_context():
            transactions = [
                {
                    'date': date(2024, 1, 1),
                    'description': 'Opening Balance',
                    'amount': Decimal('0'),
                    'transaction_type': 'credit',
                    'balance': Decimal('50000')
                },
                {
                    'date': date(2024, 1, 5),
                    'description': 'ATM Withdrawal',
                    'amount': Decimal('5000'),
                    'transaction_type': 'debit',
                    'balance': Decimal('40000')  # Should be 45000
                }
            ]

            is_valid, errors = PDFParserService.validate_transactions(transactions)
            assert is_valid is False
            assert len(errors) > 0
            assert 'balance mismatch' in errors[0].lower()

    def test_validate_transactions_empty_list(self, app):
        """Test validation with empty transaction list"""
        with app.app_context():
            transactions = []
            is_valid, errors = PDFParserService.validate_transactions(transactions)
            assert is_valid is False
            assert 'no transactions found' in errors[0].lower()

    def test_parse_statement_success(self, app, sample_hdfc_statement, monkeypatch):
        """Test complete statement parsing flow"""
        with app.app_context():
            # Mock pdfplumber to return structured data
            mock_table = [
                ['Date', 'Description', 'Debit', 'Credit', 'Balance'],
                ['01/01/2024', 'Opening Balance', '', '', '50000'],
                ['05/01/2024', 'ATM Withdrawal', '5000', '', '45000'],
                ['10/01/2024', 'Salary Credit', '', '30000', '75000']
            ]

            class MockPage:
                def extract_text(self):
                    return "HDFC Bank\nStatement of Account"

                def extract_tables(self):
                    return [mock_table]

            class MockPDF:
                pages = [MockPage()]
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass

            def mock_open(*args, **kwargs):
                return MockPDF()

            monkeypatch.setattr(pdfplumber, 'open', mock_open)

            result = PDFParserService.parse_statement(sample_hdfc_statement.id)

            assert result is not None
            assert 'bank_name' in result
            assert result['bank_name'] == 'HDFC Bank'
            assert 'transactions' in result
            assert len(result['transactions']) > 0
            assert result['is_valid'] is True

            # Check that statement status was updated (re-query from database)
            updated_statement = db.session.get(
                BankStatement,
                sample_hdfc_statement.id,
            )
            assert updated_statement.status == 'review'
            assert updated_statement.parsed_data is not None

    def test_parse_statement_no_tables_found(self, app, sample_hdfc_statement, monkeypatch):
        """Test parsing when no tables are found in PDF"""
        with app.app_context():
            class MockPage:
                def extract_text(self):
                    return "HDFC Bank\nStatement"

                def extract_tables(self):
                    return []

            class MockPDF:
                pages = [MockPage()]
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass

            def mock_open(*args, **kwargs):
                return MockPDF()

            monkeypatch.setattr(pdfplumber, 'open', mock_open)

            with pytest.raises(ValueError, match="No transaction table found"):
                PDFParserService.parse_statement(sample_hdfc_statement.id)

            # Check that statement status was updated to failed (re-query from database)
            updated_statement = db.session.get(
                BankStatement,
                sample_hdfc_statement.id,
            )
            assert updated_statement.status == 'failed'

    def test_parse_statement_invalid_statement_id(self, app):
        """Test parsing with invalid statement ID"""
        with app.app_context():
            with pytest.raises(ValueError, match="Statement not found"):
                PDFParserService.parse_statement(99999)
