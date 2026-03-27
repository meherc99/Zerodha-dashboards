"""
Tests for bank analytics routes (TDD approach)
"""
import pytest
import json
from datetime import date, timedelta
from decimal import Decimal
from app.models.transaction import Transaction
from app.models.transaction_category import TransactionCategory
from app.database import db


@pytest.fixture
def sample_categories(app):
    """Create sample transaction categories"""
    with app.app_context():
        categories = [
            TransactionCategory(
                id=1,
                name='Groceries',
                icon='🛒',
                color='#10b981',
                keywords=['grocery', 'supermarket', 'bigbasket']
            ),
            TransactionCategory(
                id=2,
                name='Food & Dining',
                icon='🍽️',
                color='#f59e0b',
                keywords=['swiggy', 'zomato', 'restaurant']
            ),
            TransactionCategory(
                id=3,
                name='Transport',
                icon='🚗',
                color='#3b82f6',
                keywords=['uber', 'ola', 'petrol']
            ),
            TransactionCategory(
                id=4,
                name='Shopping',
                icon='🛍️',
                color='#ec4899',
                keywords=['amazon', 'flipkart', 'myntra']
            ),
            TransactionCategory(
                id=5,
                name='Salary',
                icon='💰',
                color='#10b981',
                keywords=['salary', 'wages']
            ),
        ]
        db.session.bulk_save_objects(categories)
        db.session.commit()

    return {
        'groceries': 1,
        'food': 2,
        'transport': 3,
        'shopping': 4,
        'salary': 5
    }


@pytest.fixture
def sample_transactions(app, sample_bank_account, sample_categories):
    """Create sample transactions for testing analytics"""
    today = date.today()

    with app.app_context():
        transactions = [
            # Day 1 - 30 days ago
            Transaction(
                bank_account_id=sample_bank_account['id'],
                transaction_date=today - timedelta(days=30),
                description='SALARY CREDIT',
                merchant_name='Employer',
                amount=Decimal('50000.00'),
                transaction_type='credit',
                running_balance=Decimal('50000.00'),
                category_id=sample_categories['salary'],
                verified=True
            ),
            # Day 2 - 29 days ago
            Transaction(
                bank_account_id=sample_bank_account['id'],
                transaction_date=today - timedelta(days=29),
                description='AMAZON ONLINE SHOPPING',
                merchant_name='Amazon',
                amount=Decimal('2500.00'),
                transaction_type='debit',
                running_balance=Decimal('47500.00'),
                category_id=sample_categories['shopping'],
                verified=True
            ),
            # Day 3 - 28 days ago
            Transaction(
                bank_account_id=sample_bank_account['id'],
                transaction_date=today - timedelta(days=28),
                description='BIGBASKET GROCERIES',
                merchant_name='BigBasket',
                amount=Decimal('3500.00'),
                transaction_type='debit',
                running_balance=Decimal('44000.00'),
                category_id=sample_categories['groceries'],
                verified=True
            ),
            # Day 5 - 26 days ago
            Transaction(
                bank_account_id=sample_bank_account['id'],
                transaction_date=today - timedelta(days=26),
                description='SWIGGY FOOD ORDER',
                merchant_name='Swiggy',
                amount=Decimal('800.00'),
                transaction_type='debit',
                running_balance=Decimal('43200.00'),
                category_id=sample_categories['food'],
                verified=True
            ),
            # Day 7 - 24 days ago
            Transaction(
                bank_account_id=sample_bank_account['id'],
                transaction_date=today - timedelta(days=24),
                description='UBER RIDE',
                merchant_name='Uber',
                amount=Decimal('350.00'),
                transaction_type='debit',
                running_balance=Decimal('42850.00'),
                category_id=sample_categories['transport'],
                verified=True
            ),
            # Day 10 - 21 days ago
            Transaction(
                bank_account_id=sample_bank_account['id'],
                transaction_date=today - timedelta(days=21),
                description='AMAZON PRIME MEMBERSHIP',
                merchant_name='Amazon',
                amount=Decimal('1500.00'),
                transaction_type='debit',
                running_balance=Decimal('41350.00'),
                category_id=sample_categories['shopping'],
                verified=True
            ),
            # Day 15 - 16 days ago (Week 2-3)
            Transaction(
                bank_account_id=sample_bank_account['id'],
                transaction_date=today - timedelta(days=16),
                description='ZOMATO DINNER',
                merchant_name='Zomato',
                amount=Decimal('1200.00'),
                transaction_type='debit',
                running_balance=Decimal('40150.00'),
                category_id=sample_categories['food'],
                verified=True
            ),
            # Day 20 - 11 days ago
            Transaction(
                bank_account_id=sample_bank_account['id'],
                transaction_date=today - timedelta(days=11),
                description='BIGBASKET GROCERIES',
                merchant_name='BigBasket',
                amount=Decimal('2800.00'),
                transaction_type='debit',
                running_balance=Decimal('37350.00'),
                category_id=sample_categories['groceries'],
                verified=True
            ),
            # Day 25 - 6 days ago
            Transaction(
                bank_account_id=sample_bank_account['id'],
                transaction_date=today - timedelta(days=6),
                description='FLIPKART SHOPPING',
                merchant_name='Flipkart',
                amount=Decimal('5000.00'),
                transaction_type='debit',
                running_balance=Decimal('32350.00'),
                category_id=sample_categories['shopping'],
                verified=True
            ),
            # Yesterday - unverified transaction (should be excluded)
            Transaction(
                bank_account_id=sample_bank_account['id'],
                transaction_date=today - timedelta(days=1),
                description='PENDING TRANSACTION',
                amount=Decimal('10000.00'),
                transaction_type='debit',
                running_balance=Decimal('22350.00'),
                category_id=sample_categories['shopping'],
                verified=False  # Not verified
            ),
        ]

        db.session.bulk_save_objects(transactions)
        db.session.commit()


class TestBalanceTrendAnalytics:
    """Tests for GET /api/bank-accounts/:id/analytics/balance-trend"""

    def test_balance_trend_default_30_days(self, client, auth_headers,
                                           sample_bank_account, sample_transactions):
        """Test balance trend with default 30 days period"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/balance-trend',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'dates' in data
        assert 'balances' in data
        assert 'period_days' in data
        assert data['period_days'] == 30
        assert isinstance(data['dates'], list)
        assert isinstance(data['balances'], list)
        assert len(data['dates']) > 0
        assert len(data['dates']) == len(data['balances'])

    def test_balance_trend_custom_days(self, client, auth_headers,
                                       sample_bank_account, sample_transactions):
        """Test balance trend with custom period"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/balance-trend?days=7',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['period_days'] == 7
        assert len(data['dates']) <= 8  # 7 days + today

    def test_balance_trend_ownership_verification(self, client, auth_headers,
                                                   other_user_bank_account):
        """Test that users cannot access other users' balance trends"""
        response = client.get(
            f'/api/bank-accounts/{other_user_bank_account["id"]}/analytics/balance-trend',
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_balance_trend_requires_auth(self, client, sample_bank_account):
        """Test that endpoint requires authentication"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/balance-trend'
        )

        assert response.status_code == 401

    def test_balance_trend_no_transactions(self, client, auth_headers, app, sample_user):
        """Test balance trend for account with no transactions"""
        from app.models.bank_account import BankAccount

        with app.app_context():
            empty_account = BankAccount(
                user_id=sample_user['id'],
                bank_name='Empty Bank',
                account_number='0000000000',
                current_balance=Decimal('10000.00')
            )
            db.session.add(empty_account)
            db.session.commit()
            empty_id = empty_account.id

        response = client.get(
            f'/api/bank-accounts/{empty_id}/analytics/balance-trend',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['dates']) == 0
        assert len(data['balances']) == 0


class TestCategoryBreakdownAnalytics:
    """Tests for GET /api/bank-accounts/:id/analytics/category-breakdown"""

    def test_category_breakdown_default_period(self, client, auth_headers,
                                               sample_bank_account, sample_transactions):
        """Test category breakdown with default 30 days"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/category-breakdown',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'categories' in data
        assert 'total_spending' in data
        assert 'period_days' in data
        assert data['period_days'] == 30
        assert isinstance(data['categories'], list)
        assert float(data['total_spending']) > 0

        # Check category structure
        if len(data['categories']) > 0:
            category = data['categories'][0]
            assert 'id' in category
            assert 'name' in category
            assert 'icon' in category
            assert 'color' in category
            assert 'total' in category
            assert 'percentage' in category
            assert 'transaction_count' in category

    def test_category_breakdown_percentages_sum_to_100(self, client, auth_headers,
                                                        sample_bank_account, sample_transactions):
        """Test that category percentages sum to approximately 100"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/category-breakdown',
            headers=auth_headers
        )

        data = json.loads(response.data)
        total_percentage = sum(cat['percentage'] for cat in data['categories'])

        # Allow small floating point error
        assert abs(total_percentage - 100.0) < 0.1

    def test_category_breakdown_only_debits(self, client, auth_headers,
                                            sample_bank_account, sample_transactions):
        """Test that category breakdown only includes debit transactions"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/category-breakdown',
            headers=auth_headers
        )

        data = json.loads(response.data)

        # Should not include Salary category (which is credit)
        category_names = [cat['name'] for cat in data['categories']]
        assert 'Salary' not in category_names

    def test_category_breakdown_custom_period(self, client, auth_headers,
                                              sample_bank_account, sample_transactions):
        """Test category breakdown with custom period"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/category-breakdown?period_days=7',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['period_days'] == 7

    def test_category_breakdown_ownership_verification(self, client, auth_headers,
                                                        other_user_bank_account):
        """Test ownership verification for category breakdown"""
        response = client.get(
            f'/api/bank-accounts/{other_user_bank_account["id"]}/analytics/category-breakdown',
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_category_breakdown_requires_auth(self, client, sample_bank_account):
        """Test that endpoint requires authentication"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/category-breakdown'
        )

        assert response.status_code == 401


class TestCashflowAnalytics:
    """Tests for GET /api/bank-accounts/:id/analytics/cashflow"""

    def test_cashflow_default_period(self, client, auth_headers,
                                     sample_bank_account, sample_transactions):
        """Test cashflow analysis with default 30 days"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/cashflow',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'periods' in data
        assert 'credits' in data
        assert 'debits' in data
        assert 'net' in data
        assert 'period_days' in data
        assert data['period_days'] == 30

        # All arrays should have same length
        assert len(data['periods']) == len(data['credits'])
        assert len(data['periods']) == len(data['debits'])
        assert len(data['periods']) == len(data['net'])

    def test_cashflow_net_calculation(self, client, auth_headers,
                                      sample_bank_account, sample_transactions):
        """Test that net = credits - debits for each period"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/cashflow',
            headers=auth_headers
        )

        data = json.loads(response.data)

        for i in range(len(data['periods'])):
            expected_net = data['credits'][i] - data['debits'][i]
            assert abs(data['net'][i] - expected_net) < 0.01

    def test_cashflow_custom_period(self, client, auth_headers,
                                    sample_bank_account, sample_transactions):
        """Test cashflow with custom period"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/cashflow?period_days=14',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['period_days'] == 14
        assert len(data['periods']) <= 3  # 14 days = ~2 weeks

    def test_cashflow_ownership_verification(self, client, auth_headers,
                                              other_user_bank_account):
        """Test ownership verification for cashflow"""
        response = client.get(
            f'/api/bank-accounts/{other_user_bank_account["id"]}/analytics/cashflow',
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_cashflow_requires_auth(self, client, sample_bank_account):
        """Test that endpoint requires authentication"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/cashflow'
        )

        assert response.status_code == 401


class TestTopMerchantsAnalytics:
    """Tests for GET /api/bank-accounts/:id/analytics/top-merchants"""

    def test_top_merchants_default_limit(self, client, auth_headers,
                                         sample_bank_account, sample_transactions):
        """Test top merchants with default limit of 10"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/top-merchants',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'merchants' in data
        assert 'limit' in data
        assert data['limit'] == 10
        assert isinstance(data['merchants'], list)
        assert len(data['merchants']) <= 10

        # Check merchant structure
        if len(data['merchants']) > 0:
            merchant = data['merchants'][0]
            assert 'merchant' in merchant
            assert 'total' in merchant
            assert 'count' in merchant
            assert 'avg_transaction' in merchant

    def test_top_merchants_custom_limit(self, client, auth_headers,
                                        sample_bank_account, sample_transactions):
        """Test top merchants with custom limit"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/top-merchants?limit=5',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['limit'] == 5
        assert len(data['merchants']) <= 5

    def test_top_merchants_sorted_by_total(self, client, auth_headers,
                                           sample_bank_account, sample_transactions):
        """Test that merchants are sorted by total spending (descending)"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/top-merchants',
            headers=auth_headers
        )

        data = json.loads(response.data)
        merchants = data['merchants']

        # Check descending order
        for i in range(len(merchants) - 1):
            assert merchants[i]['total'] >= merchants[i + 1]['total']

    def test_top_merchants_avg_calculation(self, client, auth_headers,
                                           sample_bank_account, sample_transactions):
        """Test that average transaction is calculated correctly"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/top-merchants',
            headers=auth_headers
        )

        data = json.loads(response.data)

        for merchant in data['merchants']:
            expected_avg = merchant['total'] / merchant['count']
            assert abs(merchant['avg_transaction'] - expected_avg) < 0.01

    def test_top_merchants_ownership_verification(self, client, auth_headers,
                                                   other_user_bank_account):
        """Test ownership verification for top merchants"""
        response = client.get(
            f'/api/bank-accounts/{other_user_bank_account["id"]}/analytics/top-merchants',
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_top_merchants_requires_auth(self, client, sample_bank_account):
        """Test that endpoint requires authentication"""
        response = client.get(
            f'/api/bank-accounts/{sample_bank_account["id"]}/analytics/top-merchants'
        )

        assert response.status_code == 401
