"""
Shared test fixtures for pytest
"""
import pytest
from app import create_app, db
from app.models.user import User


@pytest.fixture
def app():
    """Create and configure test app"""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'JWT_SECRET_KEY': 'test-jwt-secret-key',
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def sample_user(app):
    """Create a sample user for testing"""
    with app.app_context():
        user = User(
            email='user@example.com',
            full_name='Test User'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        # Return user ID for use in tests
        user_id = user.id

    # Return a dict with user info that can be used outside app context
    return {
        'id': user_id,
        'email': 'user@example.com',
        'password': 'password123'
    }


@pytest.fixture
def other_user(app):
    """Create another user for testing ownership verification"""
    with app.app_context():
        user = User(
            email='other@example.com',
            full_name='Other User'
        )
        user.set_password('password456')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    return {
        'id': user_id,
        'email': 'other@example.com',
        'password': 'password456'
    }


@pytest.fixture
def auth_headers(client, sample_user):
    """Get authentication headers for sample_user"""
    import json
    response = client.post('/api/auth/login',
                          data=json.dumps({
                              'email': sample_user['email'],
                              'password': sample_user['password']
                          }),
                          content_type='application/json')
    token = json.loads(response.data)['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def other_auth_headers(client, other_user):
    """Get authentication headers for other_user"""
    import json
    response = client.post('/api/auth/login',
                          data=json.dumps({
                              'email': other_user['email'],
                              'password': other_user['password']
                          }),
                          content_type='application/json')
    token = json.loads(response.data)['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def sample_bank_account(app, sample_user):
    """Create a sample bank account for the current user"""
    from app.models.bank_account import BankAccount

    with app.app_context():
        account = BankAccount(
            user_id=sample_user['id'],
            bank_name='HDFC Bank',
            account_number='1234567890',
            account_type='savings',
            current_balance=50000.00,
            currency='INR'
        )
        db.session.add(account)
        db.session.commit()
        account_id = account.id

    return {
        'id': account_id,
        'user_id': sample_user['id'],
        'bank_name': 'HDFC Bank',
        'account_number': '1234567890',
        'account_type': 'savings',
        'current_balance': 50000.00,
        'currency': 'INR'
    }


@pytest.fixture
def other_user_bank_account(app, other_user):
    """Create a bank account for a different user to test ownership"""
    from app.models.bank_account import BankAccount

    with app.app_context():
        account = BankAccount(
            user_id=other_user['id'],
            bank_name='ICICI Bank',
            account_number='9876543210',
            account_type='current',
            current_balance=100000.00,
            currency='INR'
        )
        db.session.add(account)
        db.session.commit()
        account_id = account.id

    return {
        'id': account_id,
        'user_id': other_user['id'],
        'bank_name': 'ICICI Bank',
        'account_number': '9876543210'
    }
