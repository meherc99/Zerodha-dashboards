"""
Tests for authentication routes
"""
import pytest
import json
from datetime import datetime
from app import create_app, db
from app.models.user import User
from flask_jwt_extended import decode_token


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
            email='existing@example.com',
            full_name='Existing User'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user


class TestRegistration:
    """Tests for POST /api/auth/register endpoint"""

    def test_successful_registration(self, client, app):
        """Test successful user registration with valid data"""
        response = client.post('/api/auth/register',
                                data=json.dumps({
                                    'email': 'newuser@example.com',
                                    'password': 'secure_password_123',
                                    'full_name': 'New User'
                                }),
                                content_type='application/json')

        assert response.status_code == 201
        data = json.loads(response.data)

        # Check response structure
        assert 'access_token' in data
        assert 'user' in data
        assert data['user']['email'] == 'newuser@example.com'
        assert data['user']['full_name'] == 'New User'
        assert 'password_hash' not in data['user']  # Should not expose password

        # Verify user was created in database
        with app.app_context():
            user = User.query.filter_by(email='newuser@example.com').first()
            assert user is not None
            assert user.email == 'newuser@example.com'
            assert user.full_name == 'New User'
            assert user.check_password('secure_password_123')

    def test_registration_without_full_name(self, client, app):
        """Test registration with only email and password (full_name optional)"""
        response = client.post('/api/auth/register',
                                data=json.dumps({
                                    'email': 'minimal@example.com',
                                    'password': 'password123'
                                }),
                                content_type='application/json')

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['user']['email'] == 'minimal@example.com'
        assert data['user']['full_name'] is None

    def test_registration_duplicate_email(self, client, sample_user):
        """Test registration with existing email should fail"""
        response = client.post('/api/auth/register',
                                data=json.dumps({
                                    'email': 'existing@example.com',
                                    'password': 'different_password'
                                }),
                                content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'already exists' in data['error'].lower()

    def test_registration_missing_email(self, client):
        """Test registration without email should fail"""
        response = client.post('/api/auth/register',
                                data=json.dumps({
                                    'password': 'password123'
                                }),
                                content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_registration_missing_password(self, client):
        """Test registration without password should fail"""
        response = client.post('/api/auth/register',
                                data=json.dumps({
                                    'email': 'test@example.com'
                                }),
                                content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_registration_empty_email(self, client):
        """Test registration with empty email should fail"""
        response = client.post('/api/auth/register',
                                data=json.dumps({
                                    'email': '',
                                    'password': 'password123'
                                }),
                                content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_registration_empty_password(self, client):
        """Test registration with empty password should fail"""
        response = client.post('/api/auth/register',
                                data=json.dumps({
                                    'email': 'test@example.com',
                                    'password': ''
                                }),
                                content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_registration_invalid_json(self, client):
        """Test registration with invalid JSON should fail"""
        response = client.post('/api/auth/register',
                                data='not valid json',
                                content_type='application/json')

        assert response.status_code == 400

    def test_jwt_token_validity(self, client, app):
        """Test that returned JWT token is valid and contains user identity"""
        response = client.post('/api/auth/register',
                                data=json.dumps({
                                    'email': 'jwt@example.com',
                                    'password': 'password123'
                                }),
                                content_type='application/json')

        assert response.status_code == 201
        data = json.loads(response.data)
        token = data['access_token']

        # Decode and verify token
        with app.app_context():
            decoded = decode_token(token)
            user = User.query.filter_by(email='jwt@example.com').first()
            assert decoded['sub'] == str(user.id)  # JWT identity is stored as string


class TestLogin:
    """Tests for POST /api/auth/login endpoint"""

    def test_successful_login(self, client, sample_user):
        """Test successful login with correct credentials"""
        response = client.post('/api/auth/login',
                                data=json.dumps({
                                    'email': 'existing@example.com',
                                    'password': 'password123'
                                }),
                                content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check response structure
        assert 'access_token' in data
        assert 'user' in data
        assert data['user']['email'] == 'existing@example.com'
        assert 'password_hash' not in data['user']

    def test_login_updates_last_login_timestamp(self, client, app, sample_user):
        """Test that login updates last_login_at timestamp"""
        # Get initial last_login_at
        with app.app_context():
            user = User.query.filter_by(email='existing@example.com').first()
            initial_last_login = user.last_login_at
            assert initial_last_login is None  # Should be None initially

        # Login
        response = client.post('/api/auth/login',
                                data=json.dumps({
                                    'email': 'existing@example.com',
                                    'password': 'password123'
                                }),
                                content_type='application/json')

        assert response.status_code == 200

        # Verify last_login_at was updated
        with app.app_context():
            user = User.query.filter_by(email='existing@example.com').first()
            assert user.last_login_at is not None
            assert isinstance(user.last_login_at, datetime)

    def test_login_wrong_password(self, client, sample_user):
        """Test login with incorrect password should fail"""
        response = client.post('/api/auth/login',
                                data=json.dumps({
                                    'email': 'existing@example.com',
                                    'password': 'wrong_password'
                                }),
                                content_type='application/json')

        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert 'invalid' in data['error'].lower()

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent email should fail"""
        response = client.post('/api/auth/login',
                                data=json.dumps({
                                    'email': 'nonexistent@example.com',
                                    'password': 'password123'
                                }),
                                content_type='application/json')

        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert 'invalid' in data['error'].lower()

    def test_login_missing_email(self, client):
        """Test login without email should fail"""
        response = client.post('/api/auth/login',
                                data=json.dumps({
                                    'password': 'password123'
                                }),
                                content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_login_missing_password(self, client):
        """Test login without password should fail"""
        response = client.post('/api/auth/login',
                                data=json.dumps({
                                    'email': 'test@example.com'
                                }),
                                content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_login_inactive_user(self, client, app):
        """Test login with inactive user should fail"""
        with app.app_context():
            user = User(email='inactive@example.com', is_active=False)
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()

        response = client.post('/api/auth/login',
                                data=json.dumps({
                                    'email': 'inactive@example.com',
                                    'password': 'password123'
                                }),
                                content_type='application/json')

        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert 'inactive' in data['error'].lower()


class TestGetCurrentUser:
    """Tests for GET /api/auth/me endpoint"""

    def test_get_current_user_with_valid_token(self, client, app, sample_user):
        """Test retrieving current user profile with valid JWT token"""
        # First login to get token
        login_response = client.post('/api/auth/login',
                                      data=json.dumps({
                                          'email': 'existing@example.com',
                                          'password': 'password123'
                                      }),
                                      content_type='application/json')
        token = json.loads(login_response.data)['access_token']

        # Get current user
        response = client.get('/api/auth/me',
                              headers={'Authorization': f'Bearer {token}'})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['email'] == 'existing@example.com'
        assert data['full_name'] == 'Existing User'
        assert 'password_hash' not in data

    def test_get_current_user_without_token(self, client):
        """Test accessing /me endpoint without token should fail"""
        response = client.get('/api/auth/me')

        assert response.status_code == 401

    def test_get_current_user_with_invalid_token(self, client):
        """Test accessing /me endpoint with invalid token should fail"""
        response = client.get('/api/auth/me',
                              headers={'Authorization': 'Bearer invalid_token_here'})

        assert response.status_code == 422  # JWT library returns 422 for invalid tokens


class TestLogout:
    """Tests for POST /api/auth/logout endpoint"""

    def test_logout_endpoint_exists(self, client):
        """Test that logout endpoint exists and returns success"""
        response = client.post('/api/auth/logout')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

    def test_logout_with_token(self, client, sample_user):
        """Test logout with valid token (client-side deletion)"""
        # Login first
        login_response = client.post('/api/auth/login',
                                      data=json.dumps({
                                          'email': 'existing@example.com',
                                          'password': 'password123'
                                      }),
                                      content_type='application/json')
        token = json.loads(login_response.data)['access_token']

        # Logout
        response = client.post('/api/auth/logout',
                               headers={'Authorization': f'Bearer {token}'})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
