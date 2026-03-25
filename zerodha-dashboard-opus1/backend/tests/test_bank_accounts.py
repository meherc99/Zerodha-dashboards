"""
Tests for bank account routes
"""
import pytest
import json
from datetime import date
from app.models.bank_account import BankAccount
from app.database import db


class TestCreateBankAccount:
    """Tests for POST /api/bank-accounts endpoint"""

    def test_create_bank_account_success(self, client, auth_headers, sample_user, app):
        """Test successful bank account creation"""
        response = client.post('/api/bank-accounts',
                              data=json.dumps({
                                  'bank_name': 'State Bank of India',
                                  'account_number': '11223344556677',
                                  'account_type': 'savings',
                                  'current_balance': 25000.50,
                                  'currency': 'INR'
                              }),
                              content_type='application/json',
                              headers=auth_headers)

        assert response.status_code == 201
        data = json.loads(response.data)

        assert data['bank_name'] == 'State Bank of India'
        assert data['account_number'] == '11223344556677'
        assert data['account_type'] == 'savings'
        assert float(data['current_balance']) == 25000.50
        assert data['currency'] == 'INR'
        assert data['is_active'] is True
        assert 'id' in data
        assert 'created_at' in data

        # Verify in database
        with app.app_context():
            account = BankAccount.query.filter_by(id=data['id']).first()
            assert account is not None
            assert account.user_id == sample_user['id']
            assert account.bank_name == 'State Bank of India'

    def test_create_bank_account_minimal_fields(self, client, auth_headers, app):
        """Test bank account creation with only required fields"""
        response = client.post('/api/bank-accounts',
                              data=json.dumps({
                                  'bank_name': 'Axis Bank',
                                  'account_number': '9988776655'
                              }),
                              content_type='application/json',
                              headers=auth_headers)

        assert response.status_code == 201
        data = json.loads(response.data)

        assert data['bank_name'] == 'Axis Bank'
        assert data['account_number'] == '9988776655'
        assert data['account_type'] == 'savings'  # Default value
        assert float(data['current_balance']) == 0.0  # Default value
        assert data['currency'] == 'INR'  # Default value

    def test_create_bank_account_missing_bank_name(self, client, auth_headers):
        """Test creation without bank_name should fail"""
        response = client.post('/api/bank-accounts',
                              data=json.dumps({
                                  'account_number': '1234567890'
                              }),
                              content_type='application/json',
                              headers=auth_headers)

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_bank_account_missing_account_number(self, client, auth_headers):
        """Test creation without account_number should fail"""
        response = client.post('/api/bank-accounts',
                              data=json.dumps({
                                  'bank_name': 'HDFC Bank'
                              }),
                              content_type='application/json',
                              headers=auth_headers)

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_bank_account_requires_auth(self, client):
        """Test that creating bank account requires authentication"""
        response = client.post('/api/bank-accounts',
                              data=json.dumps({
                                  'bank_name': 'HDFC Bank',
                                  'account_number': '1234567890'
                              }),
                              content_type='application/json')

        assert response.status_code == 401


class TestListBankAccounts:
    """Tests for GET /api/bank-accounts endpoint"""

    def test_list_bank_accounts(self, client, auth_headers, sample_bank_account, app):
        """Test listing user's bank accounts"""
        response = client.get('/api/bank-accounts', headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)

        assert isinstance(data, list)
        assert len(data) >= 1

        # Find our sample account
        account = next((a for a in data if a['id'] == sample_bank_account['id']), None)
        assert account is not None
        assert account['bank_name'] == 'HDFC Bank'
        assert account['account_number'] == '1234567890'

    def test_list_only_user_accounts(self, client, auth_headers, sample_bank_account,
                                     other_user_bank_account):
        """Test that users can only see their own bank accounts"""
        response = client.get('/api/bank-accounts', headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should contain sample_bank_account but not other_user_bank_account
        account_ids = [a['id'] for a in data]
        assert sample_bank_account['id'] in account_ids
        assert other_user_bank_account['id'] not in account_ids

    def test_list_only_active_accounts(self, client, auth_headers, app, sample_user):
        """Test that only active accounts are returned"""
        # Create an inactive account
        with app.app_context():
            inactive_account = BankAccount(
                user_id=sample_user['id'],
                bank_name='Inactive Bank',
                account_number='0000000000',
                is_active=False
            )
            db.session.add(inactive_account)
            db.session.commit()
            inactive_id = inactive_account.id

        response = client.get('/api/bank-accounts', headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should not contain inactive account
        account_ids = [a['id'] for a in data]
        assert inactive_id not in account_ids

    def test_list_bank_accounts_requires_auth(self, client):
        """Test that listing accounts requires authentication"""
        response = client.get('/api/bank-accounts')

        assert response.status_code == 401


class TestGetBankAccount:
    """Tests for GET /api/bank-accounts/:id endpoint"""

    def test_get_bank_account_success(self, client, auth_headers, sample_bank_account):
        """Test retrieving a specific bank account"""
        response = client.get(f'/api/bank-accounts/{sample_bank_account["id"]}',
                             headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['id'] == sample_bank_account['id']
        assert data['bank_name'] == 'HDFC Bank'
        assert data['account_number'] == '1234567890'
        assert data['account_type'] == 'savings'

    def test_get_bank_account_not_found(self, client, auth_headers):
        """Test getting non-existent account returns 404"""
        response = client.get('/api/bank-accounts/99999', headers=auth_headers)

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_other_user_account_returns_404(self, client, auth_headers,
                                                 other_user_bank_account):
        """Test that accessing another user's account returns 404 (not 403)"""
        response = client.get(f'/api/bank-accounts/{other_user_bank_account["id"]}',
                             headers=auth_headers)

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_bank_account_requires_auth(self, client, sample_bank_account):
        """Test that getting account requires authentication"""
        response = client.get(f'/api/bank-accounts/{sample_bank_account["id"]}')

        assert response.status_code == 401


class TestUpdateBankAccount:
    """Tests for PUT /api/bank-accounts/:id endpoint"""

    def test_update_bank_account_success(self, client, auth_headers, sample_bank_account, app):
        """Test updating bank account details"""
        response = client.put(f'/api/bank-accounts/{sample_bank_account["id"]}',
                             data=json.dumps({
                                 'bank_name': 'HDFC Bank - Updated',
                                 'account_number': '9999999999',
                                 'account_type': 'current'
                             }),
                             content_type='application/json',
                             headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['bank_name'] == 'HDFC Bank - Updated'
        assert data['account_number'] == '9999999999'
        assert data['account_type'] == 'current'

        # Verify in database
        with app.app_context():
            account = BankAccount.query.get(sample_bank_account['id'])
            assert account.bank_name == 'HDFC Bank - Updated'
            assert account.account_number == '9999999999'
            assert account.account_type == 'current'

    def test_update_partial_fields(self, client, auth_headers, sample_bank_account):
        """Test updating only some fields"""
        response = client.put(f'/api/bank-accounts/{sample_bank_account["id"]}',
                             data=json.dumps({
                                 'bank_name': 'New Bank Name'
                             }),
                             content_type='application/json',
                             headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['bank_name'] == 'New Bank Name'
        assert data['account_number'] == '1234567890'  # Unchanged

    def test_update_bank_account_not_found(self, client, auth_headers):
        """Test updating non-existent account returns 404"""
        response = client.put('/api/bank-accounts/99999',
                             data=json.dumps({
                                 'bank_name': 'New Name'
                             }),
                             content_type='application/json',
                             headers=auth_headers)

        assert response.status_code == 404

    def test_update_other_user_account_returns_404(self, client, auth_headers,
                                                    other_user_bank_account):
        """Test that updating another user's account returns 404"""
        response = client.put(f'/api/bank-accounts/{other_user_bank_account["id"]}',
                             data=json.dumps({
                                 'bank_name': 'Hacked Bank'
                             }),
                             content_type='application/json',
                             headers=auth_headers)

        assert response.status_code == 404

    def test_update_bank_account_requires_auth(self, client, sample_bank_account):
        """Test that updating account requires authentication"""
        response = client.put(f'/api/bank-accounts/{sample_bank_account["id"]}',
                             data=json.dumps({
                                 'bank_name': 'New Name'
                             }),
                             content_type='application/json')

        assert response.status_code == 401


class TestDeleteBankAccount:
    """Tests for DELETE /api/bank-accounts/:id endpoint"""

    def test_delete_bank_account_soft_delete(self, client, auth_headers,
                                              sample_bank_account, app):
        """Test soft delete (sets is_active=False)"""
        response = client.delete(f'/api/bank-accounts/{sample_bank_account["id"]}',
                                headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

        # Verify account still exists but is inactive
        with app.app_context():
            account = BankAccount.query.get(sample_bank_account['id'])
            assert account is not None
            assert account.is_active is False

    def test_delete_bank_account_not_in_list(self, client, auth_headers,
                                              sample_bank_account):
        """Test that deleted account doesn't appear in list"""
        # Delete the account
        client.delete(f'/api/bank-accounts/{sample_bank_account["id"]}',
                     headers=auth_headers)

        # Try to list accounts
        response = client.get('/api/bank-accounts', headers=auth_headers)
        data = json.loads(response.data)

        account_ids = [a['id'] for a in data]
        assert sample_bank_account['id'] not in account_ids

    def test_delete_bank_account_not_found(self, client, auth_headers):
        """Test deleting non-existent account returns 404"""
        response = client.delete('/api/bank-accounts/99999',
                                headers=auth_headers)

        assert response.status_code == 404

    def test_delete_other_user_account_returns_404(self, client, auth_headers,
                                                    other_user_bank_account):
        """Test that deleting another user's account returns 404"""
        response = client.delete(f'/api/bank-accounts/{other_user_bank_account["id"]}',
                                headers=auth_headers)

        assert response.status_code == 404

    def test_delete_bank_account_requires_auth(self, client, sample_bank_account):
        """Test that deleting account requires authentication"""
        response = client.delete(f'/api/bank-accounts/{sample_bank_account["id"]}')

        assert response.status_code == 401
