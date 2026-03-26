"""
Tests for bank statement routes and file upload functionality.
Following TDD approach - these tests are written BEFORE implementation.
"""
import pytest
import json
import os
import io
from datetime import date
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
