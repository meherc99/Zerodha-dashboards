"""
Tests for User model
"""
import pytest
from datetime import datetime
from app import create_app, db
from app.models.user import User
from app.models.account import Account


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
def client(app):
    """Create test client"""
    return app.test_client()


def test_user_creation(app):
    """Test creating a user with required fields"""
    with app.app_context():
        user = User(
            email='test@example.com',
            full_name='Test User'
        )
        user.set_password('password123')

        db.session.add(user)
        db.session.commit()

        assert user.id is not None
        assert user.email == 'test@example.com'
        assert user.full_name == 'Test User'
        assert user.password_hash is not None
        assert user.password_hash != 'password123'  # Should be hashed
        assert user.is_active is True
        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)


def test_password_hashing(app):
    """Test set_password() hashes password correctly"""
    with app.app_context():
        user = User(email='test@example.com')
        user.set_password('mypassword')

        assert user.password_hash is not None
        assert user.password_hash != 'mypassword'
        assert len(user.password_hash) > 20  # Hashed passwords are long


def test_password_verification(app):
    """Test check_password() verifies password correctly"""
    with app.app_context():
        user = User(email='test@example.com')
        user.set_password('correct_password')

        # Correct password should verify
        assert user.check_password('correct_password') is True

        # Wrong password should not verify
        assert user.check_password('wrong_password') is False
        assert user.check_password('') is False


def test_unique_email_constraint(app):
    """Test email uniqueness is enforced"""
    with app.app_context():
        user1 = User(email='duplicate@example.com')
        user1.set_password('pass1')
        db.session.add(user1)
        db.session.commit()

        # Attempting to create another user with same email should fail
        user2 = User(email='duplicate@example.com')
        user2.set_password('pass2')
        db.session.add(user2)

        with pytest.raises(Exception):  # Should raise IntegrityError
            db.session.commit()


def test_user_account_relationship(app):
    """Test User can have multiple Zerodha accounts"""
    with app.app_context():
        user = User(email='trader@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

        # Create two accounts for this user
        account1 = Account(
            account_name='Account 1',
            api_key_encrypted='key1',
            api_secret_encrypted='secret1',
            access_token_encrypted='token1',
            user_id=user.id
        )
        account2 = Account(
            account_name='Account 2',
            api_key_encrypted='key2',
            api_secret_encrypted='secret2',
            access_token_encrypted='token2',
            user_id=user.id
        )
        db.session.add_all([account1, account2])
        db.session.commit()

        # Verify relationship
        assert user.accounts.count() == 2
        assert account1 in user.accounts
        assert account2 in user.accounts
        assert account1.user == user
        assert account2.user == user


def test_user_is_active_default(app):
    """Test is_active defaults to True"""
    with app.app_context():
        user = User(email='active@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

        assert user.is_active is True


def test_user_nullable_fields(app):
    """Test full_name and last_login_at can be null"""
    with app.app_context():
        user = User(email='minimal@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

        assert user.full_name is None
        assert user.last_login_at is None


def test_user_last_login_tracking(app):
    """Test last_login_at can be updated"""
    with app.app_context():
        user = User(email='login@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

        # Simulate login
        login_time = datetime.utcnow()
        user.last_login_at = login_time
        db.session.commit()

        assert user.last_login_at == login_time


def test_user_repr(app):
    """Test __repr__ method"""
    with app.app_context():
        user = User(email='repr@example.com')
        assert repr(user) == '<User repr@example.com>'
