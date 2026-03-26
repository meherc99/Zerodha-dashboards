"""
Tests for bank statement routes and file upload functionality.
Following TDD approach - these tests are written BEFORE implementation.
"""
import pytest
import json
import os
import io
from datetime import date
from decimal import Decimal
from app.models.bank_statement import BankStatement
from app.database import db


class TestUploadBankStatement:
    """Tests for POST /api/bank-accounts/:id/statements/upload endpoint"""

    def test_upload_valid_pdf_success(self, client, auth_headers, sample_bank_account, app):
        """Test successful PDF upload with valid file"""
        # Create a mock PDF file
        pdf_data = b'%PDF-1.4\n%Test PDF content'
        pdf_file = (io.BytesIO(pdf_data), 'test_statement.pdf')

        response = client.post(
            f'/api/bank-accounts/{sample_bank_account["id"]}/statements/upload',
            data={'file': pdf_file},
            content_type='multipart/form-data',
            headers=auth_headers
        )

        assert response.status_code == 202  # Accepted
        data = json.loads(response.data)

        assert 'statement_id' in data
        assert 'message' in data
        assert data['status'] == 'uploaded'

        # Verify in database
        with app.app_context():
            statement = BankStatement.query.filter_by(id=data['statement_id']).first()
            assert statement is not None
            assert statement.bank_account_id == sample_bank_account['id']
            assert statement.status == 'uploaded'
            assert statement.pdf_file_path is not None
            assert statement.pdf_file_path.endswith('.pdf')

    def test_upload_invalid_file_type(self, client, auth_headers, sample_bank_account):
        """Test upload with non-PDF file should fail"""
        # Create a text file instead of PDF
        txt_file = (io.BytesIO(b'Not a PDF'), 'test.txt')

        response = client.post(
            f'/api/bank-accounts/{sample_bank_account["id"]}/statements/upload',
            data={'file': txt_file},
            content_type='multipart/form-data',
            headers=auth_headers
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'PDF' in data['error'] or 'file type' in data['error'].lower()

    def test_upload_file_too_large(self, client, auth_headers, sample_bank_account):
        """Test upload with file larger than 10MB should fail"""
        # Create a mock large file (11MB of data)
        large_data = b'%PDF-1.4\n' + (b'x' * (11 * 1024 * 1024))
        large_file = (io.BytesIO(large_data), 'large.pdf')

        response = client.post(
            f'/api/bank-accounts/{sample_bank_account["id"]}/statements/upload',
            data={'file': large_file},
            content_type='multipart/form-data',
            headers=auth_headers
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'size' in data['error'].lower() or 'large' in data['error'].lower()

    def test_upload_no_file_provided(self, client, auth_headers, sample_bank_account):
        """Test upload without file should fail"""
        response = client.post(
            f'/api/bank-accounts/{sample_bank_account["id"]}/statements/upload',
            data={},
            content_type='multipart/form-data',
            headers=auth_headers
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_upload_empty_filename(self, client, auth_headers, sample_bank_account):
        """Test upload with empty filename should fail"""
        pdf_file = (io.BytesIO(b'%PDF-1.4\nContent'), '')

        response = client.post(
            f'/api/bank-accounts/{sample_bank_account["id"]}/statements/upload',
            data={'file': pdf_file},
            content_type='multipart/form-data',
            headers=auth_headers
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_upload_to_nonexistent_account(self, client, auth_headers):
        """Test uploading to non-existent bank account should fail"""
        pdf_file = (io.BytesIO(b'%PDF-1.4\nContent'), 'test.pdf')

        response = client.post(
            '/api/bank-accounts/99999/statements/upload',
            data={'file': pdf_file},
            content_type='multipart/form-data',
            headers=auth_headers
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_upload_to_other_user_account(self, client, auth_headers, other_user_bank_account):
        """Test uploading to another user's account should fail"""
        pdf_file = (io.BytesIO(b'%PDF-1.4\nContent'), 'test.pdf')

        response = client.post(
            f'/api/bank-accounts/{other_user_bank_account["id"]}/statements/upload',
            data={'file': pdf_file},
            content_type='multipart/form-data',
            headers=auth_headers
        )

        assert response.status_code == 404  # Returns 404 for security (don't reveal existence)
        data = json.loads(response.data)
        assert 'error' in data

    def test_upload_requires_authentication(self, client, sample_bank_account):
        """Test upload without authentication should fail"""
        pdf_file = (io.BytesIO(b'%PDF-1.4\nContent'), 'test.pdf')

        response = client.post(
            f'/api/bank-accounts/{sample_bank_account["id"]}/statements/upload',
            data={'file': pdf_file},
            content_type='multipart/form-data'
        )

        assert response.status_code == 401


class TestListBankStatements:
    """Tests for GET /api/bank-accounts/:id/statements endpoint"""

    def test_list_statements_for_account(self, client, auth_headers, sample_bank_account,
                                        app, sample_user):
        """Test listing all statements for a bank account"""
        # Create test statements
        with app.app_context():
            stmt1 = BankStatement(
                bank_account_id=sample_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file1.pdf',
                status='uploaded'
            )
            stmt2 = BankStatement(
                bank_account_id=sample_bank_account['id'],
                statement_period_start=date(2024, 2, 1),
                statement_period_end=date(2024, 2, 29),
                pdf_file_path='/path/to/file2.pdf',
                status='approved'
            )
            db.session.add_all([stmt1, stmt2])
            db.session.commit()

        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/statements',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert isinstance(data, list)
        assert len(data) == 2
        assert all('id' in stmt for stmt in data)
        assert all('status' in stmt for stmt in data)
        assert all('upload_date' in stmt for stmt in data)

    def test_list_statements_empty(self, client, auth_headers, sample_bank_account):
        """Test listing statements when none exist"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/statements',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_statements_for_nonexistent_account(self, client, auth_headers):
        """Test listing statements for non-existent account"""
        response = client.get(
            '/api/bank-accounts/99999/statements',
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_list_statements_other_user_account(self, client, auth_headers,
                                               other_user_bank_account):
        """Test listing statements for another user's account should fail"""
        response = client.get(
            f'/api/bank-accounts/{other_user_bank_account["id"]}/statements',
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_list_statements_requires_auth(self, client, sample_bank_account):
        """Test listing statements requires authentication"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/statements'
        )

        assert response.status_code == 401


class TestGetStatementDetails:
    """Tests for GET /api/statements/:id endpoint"""

    def test_get_statement_details_success(self, client, auth_headers,
                                          sample_bank_account, app):
        """Test getting details of a specific statement"""
        with app.app_context():
            stmt = BankStatement(
                bank_account_id=sample_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='uploaded'
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        response = client.get(
            f'/api/statements/{stmt_id}',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['id'] == stmt_id
        assert data['bank_account_id'] == sample_bank_account['id']
        assert data['status'] == 'uploaded'
        assert 'statement_period_start' in data
        assert 'statement_period_end' in data

    def test_get_statement_nonexistent(self, client, auth_headers):
        """Test getting non-existent statement"""
        response = client.get(
            '/api/statements/99999',
            headers=auth_headers
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_statement_other_user(self, client, auth_headers,
                                     other_user_bank_account, app):
        """Test getting statement from another user's account"""
        with app.app_context():
            stmt = BankStatement(
                bank_account_id=other_user_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='uploaded'
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        response = client.get(
            f'/api/statements/{stmt_id}',
            headers=auth_headers
        )

        assert response.status_code == 404  # Security: don't reveal existence

    def test_get_statement_requires_auth(self, client, sample_bank_account, app):
        """Test getting statement requires authentication"""
        with app.app_context():
            stmt = BankStatement(
                bank_account_id=sample_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='uploaded'
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        response = client.get(f'/api/statements/{stmt_id}')

        assert response.status_code == 401


class TestDeleteStatement:
    """Tests for DELETE /api/statements/:id endpoint"""

    def test_delete_statement_success(self, client, auth_headers,
                                     sample_bank_account, app):
        """Test successful statement deletion"""
        with app.app_context():
            stmt = BankStatement(
                bank_account_id=sample_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='uploaded'
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        response = client.delete(
            f'/api/statements/{stmt_id}',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

        # Verify deletion from database
        with app.app_context():
            stmt = BankStatement.query.get(stmt_id)
            assert stmt is None

    def test_delete_statement_nonexistent(self, client, auth_headers):
        """Test deleting non-existent statement"""
        response = client.delete(
            '/api/statements/99999',
            headers=auth_headers
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_delete_statement_other_user(self, client, auth_headers,
                                        other_user_bank_account, app):
        """Test deleting statement from another user's account"""
        with app.app_context():
            stmt = BankStatement(
                bank_account_id=other_user_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='uploaded'
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        response = client.delete(
            f'/api/statements/{stmt_id}',
            headers=auth_headers
        )

        assert response.status_code == 404

        # Verify statement still exists (wasn't deleted)
        with app.app_context():
            stmt = BankStatement.query.get(stmt_id)
            assert stmt is not None

    def test_delete_statement_requires_auth(self, client, sample_bank_account, app):
        """Test deleting statement requires authentication"""
        with app.app_context():
            stmt = BankStatement(
                bank_account_id=sample_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='uploaded'
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        response = client.delete(f'/api/statements/{stmt_id}')

        assert response.status_code == 401


class TestStatementPreview:
    """Tests for GET /api/statements/:id/preview endpoint"""

    def test_get_preview_success(self, client, auth_headers, sample_bank_account, app):
        """Test getting preview of a parsed statement ready for review"""
        with app.app_context():
            # Create statement with parsed data
            stmt = BankStatement(
                bank_account_id=sample_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='review',
                parsed_data={
                    'bank_name': 'HDFC Bank',
                    'transactions': [
                        {
                            'date': '2024-01-15',
                            'description': 'BigBasket Online',
                            'amount': '2500.00',
                            'transaction_type': 'debit',
                            'balance': '15000.00'
                        },
                        {
                            'date': '2024-01-20',
                            'description': 'Salary Credit',
                            'amount': '50000.00',
                            'transaction_type': 'credit',
                            'balance': '65000.00'
                        }
                    ],
                    'is_valid': True,
                    'validation_errors': []
                }
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        response = client.get(
            f'/api/statements/{stmt_id}/preview',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check statement details
        assert 'statement' in data
        assert data['statement']['id'] == stmt_id
        assert data['statement']['status'] == 'review'
        assert data['statement']['bank_account_id'] == sample_bank_account['id']

        # Check transactions with categorization
        assert 'transactions' in data
        assert len(data['transactions']) == 2

        # Each transaction should have category_id and category_confidence
        for txn in data['transactions']:
            assert 'date' in txn
            assert 'description' in txn
            assert 'amount' in txn
            assert 'transaction_type' in txn
            assert 'balance' in txn
            assert 'category_id' in txn
            assert 'category_confidence' in txn

        # Check validation warnings
        assert 'validation_warnings' in data
        assert isinstance(data['validation_warnings'], list)

    def test_get_preview_with_warnings(self, client, auth_headers, sample_bank_account, app):
        """Test preview with validation warnings"""
        with app.app_context():
            stmt = BankStatement(
                bank_account_id=sample_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='review',
                parsed_data={
                    'bank_name': 'HDFC Bank',
                    'transactions': [
                        {
                            'date': '2024-01-15',
                            'description': 'Transaction',
                            'amount': '1000.00',
                            'transaction_type': 'debit',
                            'balance': '10000.00'
                        },
                        {
                            'date': '2024-01-16',
                            'description': 'Another Transaction',
                            'amount': '500.00',
                            'transaction_type': 'debit',
                            'balance': '9000.00'  # Mismatch - should be 9500.00
                        }
                    ],
                    'is_valid': False,
                    'validation_errors': ['Balance mismatch at row 2']
                }
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        response = client.get(
            f'/api/statements/{stmt_id}/preview',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['validation_warnings']) > 0
        # Should have at least the balance mismatch warning
        assert any('balance' in str(w).lower() for w in data['validation_warnings'])

    def test_get_preview_not_ready_status(self, client, auth_headers, sample_bank_account, app):
        """Test preview with statement not in review status"""
        with app.app_context():
            stmt = BankStatement(
                bank_account_id=sample_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='uploaded'  # Not ready for review
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        response = client.get(
            f'/api/statements/{stmt_id}/preview',
            headers=auth_headers
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_preview_nonexistent(self, client, auth_headers):
        """Test preview for non-existent statement"""
        response = client.get(
            '/api/statements/99999/preview',
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_get_preview_other_user_statement(self, client, auth_headers,
                                             other_user_bank_account, app):
        """Test preview for another user's statement"""
        with app.app_context():
            stmt = BankStatement(
                bank_account_id=other_user_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='review',
                parsed_data={'transactions': []}
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        response = client.get(
            f'/api/statements/{stmt_id}/preview',
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_get_preview_requires_auth(self, client, sample_bank_account, app):
        """Test preview requires authentication"""
        with app.app_context():
            stmt = BankStatement(
                bank_account_id=sample_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='review',
                parsed_data={'transactions': []}
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        response = client.get(f'/api/statements/{stmt_id}/preview')

        assert response.status_code == 401


class TestApproveStatement:
    """Tests for POST /api/statements/:id/approve endpoint"""

    def test_approve_statement_success(self, client, auth_headers, sample_bank_account, app):
        """Test successful statement approval and transaction creation"""
        from app.models.transaction import Transaction

        with app.app_context():
            stmt = BankStatement(
                bank_account_id=sample_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='review',
                parsed_data={'transactions': []}
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        # Prepare approve request
        approve_data = {
            'transactions': [
                {
                    'transaction_date': '2024-01-15',
                    'description': 'BigBasket Online',
                    'amount': 2500.00,
                    'transaction_type': 'debit',
                    'running_balance': 15000.00,
                    'category_id': 1,
                    'notes': 'Weekly groceries'
                },
                {
                    'transaction_date': '2024-01-20',
                    'description': 'Salary Credit',
                    'amount': 50000.00,
                    'transaction_type': 'credit',
                    'running_balance': 65000.00,
                    'category_id': 2
                }
            ]
        }

        response = client.post(
            f'/api/statements/{stmt_id}/approve',
            json=approve_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'message' in data
        assert 'transaction_count' in data
        assert data['transaction_count'] == 2
        assert 'transaction_ids' in data
        assert len(data['transaction_ids']) == 2

        # Verify transactions were created
        with app.app_context():
            transactions = Transaction.query.filter_by(statement_id=stmt_id).all()
            assert len(transactions) == 2

            # Verify transaction details
            txn1 = transactions[0]
            assert txn1.bank_account_id == sample_bank_account['id']
            assert txn1.description == 'BigBasket Online'
            assert txn1.amount == Decimal('2500.00')
            assert txn1.transaction_type == 'debit'
            assert txn1.running_balance == Decimal('15000.00')
            assert txn1.category_id == 1

            # Verify statement status updated
            stmt = BankStatement.query.get(stmt_id)
            assert stmt.status == 'approved'

            # Verify bank account balance updated
            from app.models.bank_account import BankAccount
            account = BankAccount.query.get(sample_bank_account['id'])
            assert account.current_balance == Decimal('65000.00')  # Last transaction balance
            assert account.last_statement_date == date(2024, 1, 31)

    def test_approve_statement_empty_transactions(self, client, auth_headers,
                                                  sample_bank_account, app):
        """Test approval with no transactions should fail"""
        with app.app_context():
            stmt = BankStatement(
                bank_account_id=sample_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='review',
                parsed_data={'transactions': []}
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        approve_data = {'transactions': []}

        response = client.post(
            f'/api/statements/{stmt_id}/approve',
            json=approve_data,
            headers=auth_headers
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_approve_statement_invalid_data(self, client, auth_headers,
                                           sample_bank_account, app):
        """Test approval with missing required fields"""
        with app.app_context():
            stmt = BankStatement(
                bank_account_id=sample_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='review',
                parsed_data={'transactions': []}
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        # Missing required fields
        approve_data = {
            'transactions': [
                {
                    'description': 'Test',
                    # Missing transaction_date, amount, transaction_type
                }
            ]
        }

        response = client.post(
            f'/api/statements/{stmt_id}/approve',
            json=approve_data,
            headers=auth_headers
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_approve_statement_wrong_status(self, client, auth_headers,
                                           sample_bank_account, app):
        """Test approval when statement is not in review status"""
        with app.app_context():
            stmt = BankStatement(
                bank_account_id=sample_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='uploaded'  # Wrong status
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        approve_data = {
            'transactions': [
                {
                    'transaction_date': '2024-01-15',
                    'description': 'Test',
                    'amount': 100.00,
                    'transaction_type': 'debit',
                    'running_balance': 1000.00
                }
            ]
        }

        response = client.post(
            f'/api/statements/{stmt_id}/approve',
            json=approve_data,
            headers=auth_headers
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_approve_statement_nonexistent(self, client, auth_headers):
        """Test approval for non-existent statement"""
        approve_data = {
            'transactions': [
                {
                    'transaction_date': '2024-01-15',
                    'description': 'Test',
                    'amount': 100.00,
                    'transaction_type': 'debit',
                    'running_balance': 1000.00
                }
            ]
        }

        response = client.post(
            '/api/statements/99999/approve',
            json=approve_data,
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_approve_statement_other_user(self, client, auth_headers,
                                         other_user_bank_account, app):
        """Test approval for another user's statement"""
        with app.app_context():
            stmt = BankStatement(
                bank_account_id=other_user_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='review',
                parsed_data={'transactions': []}
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        approve_data = {
            'transactions': [
                {
                    'transaction_date': '2024-01-15',
                    'description': 'Test',
                    'amount': 100.00,
                    'transaction_type': 'debit',
                    'running_balance': 1000.00
                }
            ]
        }

        response = client.post(
            f'/api/statements/{stmt_id}/approve',
            json=approve_data,
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_approve_statement_requires_auth(self, client, sample_bank_account, app):
        """Test approval requires authentication"""
        with app.app_context():
            stmt = BankStatement(
                bank_account_id=sample_bank_account['id'],
                statement_period_start=date(2024, 1, 1),
                statement_period_end=date(2024, 1, 31),
                pdf_file_path='/path/to/file.pdf',
                status='review',
                parsed_data={'transactions': []}
            )
            db.session.add(stmt)
            db.session.commit()
            stmt_id = stmt.id

        approve_data = {'transactions': []}

        response = client.post(f'/api/statements/{stmt_id}/approve', json=approve_data)

        assert response.status_code == 401
