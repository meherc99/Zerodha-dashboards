"""
Tests for transaction routes and management endpoints.
Following TDD approach - these tests are written BEFORE implementation.
"""
import pytest
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from app.models.transaction import Transaction
from app.models.transaction_category import TransactionCategory
from app.models.bank_account import BankAccount
from app.database import db


@pytest.fixture
def sample_categories(app):
    """Create sample transaction categories"""
    with app.app_context():
        categories = [
            TransactionCategory(
                name='Groceries',
                icon='🛒',
                color='#10b981',
                keywords=['bigbasket', 'swiggy', 'zomato', 'grocery']
            ),
            TransactionCategory(
                name='Utilities',
                icon='💡',
                color='#f59e0b',
                keywords=['electricity', 'water', 'gas', 'bill']
            ),
            TransactionCategory(
                name='Salary',
                icon='💰',
                color='#3b82f6',
                keywords=['salary', 'income', 'wages']
            ),
            TransactionCategory(
                name='Shopping',
                icon='🛍️',
                color='#ec4899',
                keywords=['amazon', 'flipkart', 'shopping']
            )
        ]
        for cat in categories:
            db.session.add(cat)
        db.session.commit()

        # Return category IDs instead of dicts
        return [cat.id for cat in categories]


@pytest.fixture
def sample_transactions(app, sample_bank_account, sample_categories):
    """Create sample transactions for testing"""
    with app.app_context():
        base_date = date(2024, 1, 1)
        transactions = []

        # Create 50 transactions with various types
        for i in range(50):
            txn = Transaction(
                bank_account_id=sample_bank_account['id'],
                transaction_date=base_date + timedelta(days=i),
                description=f'Transaction {i+1}',
                amount=Decimal('100.00') * (i + 1),
                transaction_type='debit' if i % 2 == 0 else 'credit',
                running_balance=Decimal('50000.00') + Decimal('100.00') * i,
                category_id=sample_categories[i % 4],  # Rotate through categories
                category_confidence=0.85,
                verified=i % 3 == 0  # Every third transaction is verified
            )
            db.session.add(txn)
            transactions.append(txn)

        # Add some specific test transactions
        specific_txns = [
            Transaction(
                bank_account_id=sample_bank_account['id'],
                transaction_date=date(2024, 2, 15),
                description='BigBasket Online',
                amount=Decimal('2500.00'),
                transaction_type='debit',
                running_balance=Decimal('47500.00'),
                category_id=sample_categories[0],  # Groceries
                category_confidence=0.95,
                verified=False
            ),
            Transaction(
                bank_account_id=sample_bank_account['id'],
                transaction_date=date(2024, 2, 16),
                description='Electricity Bill Payment',
                amount=Decimal('1200.00'),
                transaction_type='debit',
                running_balance=Decimal('46300.00'),
                category_id=sample_categories[1],  # Utilities
                category_confidence=0.90,
                verified=True,
                notes='Monthly electricity bill'
            ),
            Transaction(
                bank_account_id=sample_bank_account['id'],
                transaction_date=date(2024, 2, 28),
                description='Salary Credit',
                amount=Decimal('75000.00'),
                transaction_type='credit',
                running_balance=Decimal('121300.00'),
                category_id=sample_categories[2],  # Salary
                category_confidence=0.99,
                verified=True
            )
        ]

        for txn in specific_txns:
            db.session.add(txn)
            transactions.append(txn)

        db.session.commit()

        # Return transaction IDs for use in tests
        return [txn.id for txn in transactions]


@pytest.fixture
def other_user_transactions(app, other_user_bank_account, sample_categories):
    """Create transactions for another user to test ownership verification"""
    with app.app_context():
        txn = Transaction(
            bank_account_id=other_user_bank_account['id'],
            transaction_date=date(2024, 1, 1),
            description='Other User Transaction',
            amount=Decimal('500.00'),
            transaction_type='debit',
            running_balance=Decimal('99500.00'),
            category_id=sample_categories[0]
        )
        db.session.add(txn)
        db.session.commit()
        txn_id = txn.id

    return txn_id


class TestListTransactions:
    """Tests for GET /api/bank-accounts/:id/transactions endpoint"""

    def test_list_transactions_success(self, client, auth_headers, sample_bank_account, sample_transactions):
        """Test listing transactions for a bank account"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/transactions',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'transactions' in data
        assert 'total' in data
        assert 'page' in data
        assert 'limit' in data
        assert 'pages' in data

        assert len(data['transactions']) > 0
        assert data['total'] == len(sample_transactions)
        assert data['page'] == 1
        assert data['limit'] == 50

        # Check transaction structure
        txn = data['transactions'][0]
        assert 'id' in txn
        assert 'transaction_date' in txn
        assert 'description' in txn
        assert 'amount' in txn
        assert 'transaction_type' in txn
        assert 'running_balance' in txn
        assert 'category' in txn
        assert 'verified' in txn

        # Check category structure
        if txn['category']:
            assert 'id' in txn['category']
            assert 'name' in txn['category']
            assert 'icon' in txn['category']
            assert 'color' in txn['category']

    def test_list_transactions_with_date_filter(self, client, auth_headers, sample_bank_account, sample_transactions):
        """Test filtering transactions by date range"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/transactions',
            query_string={
                'date_from': '2024-02-15',
                'date_to': '2024-02-28'
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should include BigBasket (2/15), Electricity (2/16), Salary (2/28) and some from loop
        assert len(data['transactions']) >= 3

        for txn in data['transactions']:
            txn_date = datetime.fromisoformat(txn['transaction_date']).date()
            assert date(2024, 2, 15) <= txn_date <= date(2024, 2, 28)

    def test_list_transactions_with_type_filter(self, client, auth_headers, sample_bank_account, sample_transactions):
        """Test filtering transactions by type (credit/debit)"""
        # Test debit filter
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/transactions',
            query_string={'type': 'debit'},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        for txn in data['transactions']:
            assert txn['transaction_type'] == 'debit'

        # Test credit filter
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/transactions',
            query_string={'type': 'credit'},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        for txn in data['transactions']:
            assert txn['transaction_type'] == 'credit'

    def test_list_transactions_with_category_filter(self, client, auth_headers, sample_bank_account, sample_transactions, sample_categories):
        """Test filtering transactions by category"""
        category_id = sample_categories[0]  # First category (Groceries)

        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/transactions',
            query_string={'category_id': category_id},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        for txn in data['transactions']:
            if txn['category']:
                assert txn['category']['id'] == category_id

    def test_list_transactions_with_search(self, client, auth_headers, sample_bank_account, sample_transactions):
        """Test searching transactions by description"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/transactions',
            query_string={'search': 'BigBasket'},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['transactions']) >= 1
        assert any('BigBasket' in txn['description'] for txn in data['transactions'])

    def test_list_transactions_with_sorting(self, client, auth_headers, sample_bank_account, sample_transactions):
        """Test sorting transactions"""
        # Sort by date ascending
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/transactions',
            query_string={'sort_by': 'date', 'order': 'asc'},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        dates = [datetime.fromisoformat(txn['transaction_date']) for txn in data['transactions']]
        assert dates == sorted(dates)

        # Sort by amount descending
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/transactions',
            query_string={'sort_by': 'amount', 'order': 'desc'},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        amounts = [float(txn['amount']) for txn in data['transactions']]
        assert amounts == sorted(amounts, reverse=True)

    def test_list_transactions_pagination(self, client, auth_headers, sample_bank_account, sample_transactions):
        """Test pagination of transaction list"""
        # Page 1 with limit 10
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/transactions',
            query_string={'page': 1, 'limit': 10},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['transactions']) == 10
        assert data['page'] == 1
        assert data['limit'] == 10
        assert data['pages'] > 1

        # Page 2
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/transactions',
            query_string={'page': 2, 'limit': 10},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['transactions']) == 10
        assert data['page'] == 2

    def test_list_transactions_max_limit(self, client, auth_headers, sample_bank_account, sample_transactions):
        """Test that limit is capped at 200"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/transactions',
            query_string={'limit': 500},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['limit'] == 200  # Should be capped

    def test_list_transactions_unauthorized(self, client, auth_headers, other_user_bank_account):
        """Test that users cannot access other users' transactions"""
        response = client.get(
            f'/api/bank-accounts/{other_user_bank_account["id"]}/transactions',
            headers=auth_headers
        )

        assert response.status_code == 403

    def test_list_transactions_invalid_account(self, client, auth_headers):
        """Test listing transactions for non-existent account"""
        response = client.get(
            '/api/bank-accounts/99999/transactions',
            headers=auth_headers
        )

        assert response.status_code == 404


class TestSearchAllTransactions:
    """Tests for GET /api/transactions/search endpoint"""

    def test_search_all_transactions_success(self, client, auth_headers, sample_transactions):
        """Test global search across all user's accounts"""
        response = client.get(
            '/api/transactions/search',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'transactions' in data
        assert 'total' in data

        # Check that bank_account info is included
        txn = data['transactions'][0]
        assert 'bank_account' in txn
        assert 'id' in txn['bank_account']
        assert 'bank_name' in txn['bank_account']

    def test_search_all_with_filters(self, client, auth_headers, sample_transactions):
        """Test global search with various filters"""
        response = client.get(
            '/api/transactions/search',
            query_string={
                'search': 'Salary',
                'type': 'credit',
                'date_from': '2024-02-01'
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        for txn in data['transactions']:
            assert txn['transaction_type'] == 'credit'
            assert 'Salary' in txn['description']

    def test_search_all_only_returns_user_transactions(self, client, auth_headers, sample_transactions, other_user_transactions):
        """Test that search only returns current user's transactions"""
        response = client.get(
            '/api/transactions/search',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should only include sample_transactions, not other_user_transactions
        txn_ids = [txn['id'] for txn in data['transactions']]
        assert other_user_transactions not in txn_ids


class TestUpdateTransaction:
    """Tests for PUT /api/transactions/:id endpoint"""

    def test_update_transaction_category(self, client, auth_headers, sample_transactions, app):
        """Test updating transaction category"""
        txn_id = sample_transactions[0]

        response = client.put(
            f'/api/transactions/{txn_id}',
            data=json.dumps({'category_id': 2}),
            content_type='application/json',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['category']['id'] == 2

        # Verify in database
        with app.app_context():
            txn = Transaction.query.get(txn_id)
            assert txn.category_id == 2
            assert txn.updated_at > txn.created_at

    def test_update_transaction_notes(self, client, auth_headers, sample_transactions, app):
        """Test updating transaction notes"""
        txn_id = sample_transactions[0]

        response = client.put(
            f'/api/transactions/{txn_id}',
            data=json.dumps({'notes': 'This is a test note'}),
            content_type='application/json',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['notes'] == 'This is a test note'

        # Verify in database
        with app.app_context():
            txn = Transaction.query.get(txn_id)
            assert txn.notes == 'This is a test note'

    def test_update_transaction_verified(self, client, auth_headers, sample_transactions, app):
        """Test marking transaction as verified"""
        txn_id = sample_transactions[0]

        response = client.put(
            f'/api/transactions/{txn_id}',
            data=json.dumps({'verified': True}),
            content_type='application/json',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['verified'] is True

        # Verify in database
        with app.app_context():
            txn = Transaction.query.get(txn_id)
            assert txn.verified is True

    def test_update_transaction_multiple_fields(self, client, auth_headers, sample_transactions):
        """Test updating multiple fields at once"""
        txn_id = sample_transactions[0]

        response = client.put(
            f'/api/transactions/{txn_id}',
            data=json.dumps({
                'category_id': 3,
                'notes': 'Updated note',
                'verified': True
            }),
            content_type='application/json',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['category']['id'] == 3
        assert data['notes'] == 'Updated note'
        assert data['verified'] is True

    def test_update_transaction_cannot_change_amount(self, client, auth_headers, sample_transactions):
        """Test that amount cannot be changed"""
        txn_id = sample_transactions[0]

        response = client.put(
            f'/api/transactions/{txn_id}',
            data=json.dumps({'amount': '999999.99'}),
            content_type='application/json',
            headers=auth_headers
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_update_transaction_cannot_change_date(self, client, auth_headers, sample_transactions):
        """Test that transaction_date cannot be changed"""
        txn_id = sample_transactions[0]

        response = client.put(
            f'/api/transactions/{txn_id}',
            data=json.dumps({'transaction_date': '2099-12-31'}),
            content_type='application/json',
            headers=auth_headers
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_update_transaction_unauthorized(self, client, auth_headers, other_user_transactions):
        """Test that users cannot update other users' transactions"""
        response = client.put(
            f'/api/transactions/{other_user_transactions}',
            data=json.dumps({'notes': 'Hacking attempt'}),
            content_type='application/json',
            headers=auth_headers
        )

        assert response.status_code == 403

    def test_update_transaction_not_found(self, client, auth_headers):
        """Test updating non-existent transaction"""
        response = client.put(
            '/api/transactions/99999',
            data=json.dumps({'notes': 'Test'}),
            content_type='application/json',
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_update_transaction_invalid_category(self, client, auth_headers, sample_transactions):
        """Test updating with non-existent category"""
        txn_id = sample_transactions[0]

        response = client.put(
            f'/api/transactions/{txn_id}',
            data=json.dumps({'category_id': 99999}),
            content_type='application/json',
            headers=auth_headers
        )

        assert response.status_code == 400


class TestDeleteTransaction:
    """Tests for DELETE /api/transactions/:id endpoint"""

    def test_delete_transaction_success(self, client, auth_headers, sample_transactions, app):
        """Test deleting a transaction"""
        txn_id = sample_transactions[0]

        response = client.delete(
            f'/api/transactions/{txn_id}',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

        # Verify transaction is deleted
        with app.app_context():
            txn = Transaction.query.get(txn_id)
            assert txn is None

    def test_delete_transaction_unauthorized(self, client, auth_headers, other_user_transactions):
        """Test that users cannot delete other users' transactions"""
        response = client.delete(
            f'/api/transactions/{other_user_transactions}',
            headers=auth_headers
        )

        assert response.status_code == 403

    def test_delete_transaction_not_found(self, client, auth_headers):
        """Test deleting non-existent transaction"""
        response = client.delete(
            '/api/transactions/99999',
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_delete_transaction_reduces_count(self, client, auth_headers, sample_bank_account, sample_transactions, app):
        """Test that deleting reduces transaction count"""
        # Get initial count
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/transactions',
            headers=auth_headers
        )
        initial_total = json.loads(response.data)['total']

        # Delete a transaction
        txn_id = sample_transactions[0]
        client.delete(
            f'/api/transactions/{txn_id}',
            headers=auth_headers
        )

        # Get new count
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/transactions',
            headers=auth_headers
        )
        new_total = json.loads(response.data)['total']

        assert new_total == initial_total - 1
