"""Shared fixtures for cross-cutting frontend<->backend integration tests.

These tests live outside ``src/backend`` so they can reason about both the
Flask API and the Vue frontend contract at once. The backend package is added
to ``sys.path`` here so ``import app`` resolves without installing the project.

Run them with::

    conda run -n investment_dashboard pytest src/tests
"""
import json
import os
import sys

import pytest
from cryptography.fernet import Fernet

# Make the backend application importable when pytest is invoked from anywhere.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

FRONTEND_SRC = os.path.join(REPO_ROOT, "frontend", "src")

from app import create_app, db  # noqa: E402  (import after sys.path setup)
from app.models.user import User  # noqa: E402


@pytest.fixture(autouse=True)
def isolate_statement_uploads(monkeypatch, tmp_path):
    """Keep statement files out of the source tree during every test."""
    from app.services import bank_statement_service

    monkeypatch.setattr(
        bank_statement_service,
        "UPLOAD_BASE_DIR",
        str(tmp_path / "bank-statements"),
    )


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Keep the process-wide in-memory limiter isolated between tests."""
    from app.utils.rate_limiter import _rate_limit_storage, _storage_lock

    with _storage_lock:
        _rate_limit_storage.clear()
    yield
    with _storage_lock:
        _rate_limit_storage.clear()


@pytest.fixture
def app():
    """Create an isolated in-memory application instance."""
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "JWT_SECRET_KEY": "test-jwt-secret-key-at-least-32-bytes",
            "SECRET_KEY": "test-secret-key",
            "ENCRYPTION_KEY": Fernet.generate_key().decode(),
            "SCHEDULER_ENABLED": False,
        }
    )

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client bound to the isolated app."""
    return app.test_client()


def _create_user(app, email, password, full_name):
    with app.app_context():
        user = User(email=email, full_name=full_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return {"id": user.id, "email": email, "password": password}


@pytest.fixture
def sample_user(app):
    return _create_user(app, "user@example.com", "password123", "Test User")


@pytest.fixture
def other_user(app):
    return _create_user(app, "other@example.com", "password456", "Other User")


def _login(client, email, password):
    response = client.post(
        "/api/auth/login",
        data=json.dumps({"email": email, "password": password}),
        content_type="application/json",
    )
    token = json.loads(response.data)["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(client, sample_user):
    return _login(client, sample_user["email"], sample_user["password"])


@pytest.fixture
def other_auth_headers(client, other_user):
    return _login(client, other_user["email"], other_user["password"])


@pytest.fixture
def make_kite_account(app):
    """Factory that inserts a Zerodha account with encrypted credentials.

    Account creation through the API requires a live Kite request-token
    exchange, so integration tests seed the account directly and mock the
    broker client during sync.
    """
    from app.models import Account
    from app.utils.encryption import get_encryptor

    def _make(user_id, name="Primary", api_key="api-key"):
        with app.app_context():
            encryptor = get_encryptor()
            account = Account(
                user_id=user_id,
                account_name=name,
                api_key_encrypted=encryptor.encrypt(api_key),
                api_secret_encrypted=encryptor.encrypt("api-secret"),
                access_token_encrypted=encryptor.encrypt("access-token"),
                is_active=True,
            )
            db.session.add(account)
            db.session.commit()
            return account.id

    return _make
