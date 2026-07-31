"""Application-factory regression tests."""
import os
import stat

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import create_app, db
from app.config import config
from app.models.account import Account
import app.services.bank_statement_service as bank_statement_service


TEST_CONFIG = {
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'JWT_SECRET_KEY': 'test-jwt-secret-key-at-least-32-bytes',
    'SECRET_KEY': 'test-secret-key-at-least-32-bytes',
    'SCHEDULER_ENABLED': False,
}


def test_config_is_applied_before_database_binding():
    app = create_app(TEST_CONFIG)

    with app.app_context():
        assert str(db.engine.url) == 'sqlite:///:memory:'


def test_auth_routes_are_registered_once():
    app = create_app(TEST_CONFIG)
    expected_routes = {
        '/api/auth/register',
        '/api/auth/login',
        '/api/auth/me',
        '/api/auth/logout',
        '/api/auth/login-url',
        '/api/auth/access-token',
    }

    rules = [rule.rule for rule in app.url_map.iter_rules()]
    assert all(rules.count(route) == 1 for route in expected_routes)


def test_factory_does_not_start_scheduler():
    app = create_app(TEST_CONFIG)

    assert app.scheduler.scheduler.running is False
    assert app.scheduler.scheduler.get_jobs() == []


def test_factory_hardens_legacy_statement_storage(
    monkeypatch,
    tmp_path,
):
    storage_root = tmp_path / 'legacy-statements'
    account_directory = storage_root / '7' / '11'
    account_directory.mkdir(parents=True)
    statement_path = account_directory / 'legacy.pdf'
    statement_path.write_bytes(b'%PDF-1.4\nlegacy')
    for directory in (
        storage_root,
        storage_root / '7',
        account_directory,
    ):
        os.chmod(directory, 0o755)
    os.chmod(statement_path, 0o644)
    monkeypatch.setattr(
        bank_statement_service,
        'UPLOAD_BASE_DIR',
        str(storage_root),
    )

    create_app(TEST_CONFIG)

    for directory in (
        storage_root,
        storage_root / '7',
        account_directory,
    ):
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(statement_path.stat().st_mode) == 0o600


def test_factory_refuses_symlinks_in_statement_storage(
    monkeypatch,
    tmp_path,
):
    storage_root = tmp_path / 'unsafe-statements'
    storage_root.mkdir()
    outside_file = tmp_path / 'outside.pdf'
    outside_file.write_bytes(b'%PDF-1.4\noutside')
    (storage_root / 'linked.pdf').symlink_to(outside_file)
    monkeypatch.setattr(
        bank_statement_service,
        'UPLOAD_BASE_DIR',
        str(storage_root),
    )

    with pytest.raises(RuntimeError, match='symbolic link'):
        create_app(TEST_CONFIG)

    assert outside_file.read_bytes() == b'%PDF-1.4\noutside'


def test_api_responses_include_baseline_security_headers():
    app = create_app(TEST_CONFIG)
    client = app.test_client()
    response = client.get('/')

    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['Referrer-Policy'] == 'same-origin'
    assert response.headers['Content-Security-Policy'].startswith(
        "default-src 'none'"
    )
    assert response.headers['Permissions-Policy'] == (
        'camera=(), geolocation=(), microphone=()'
    )

    api_response = client.get('/api/health')
    assert api_response.headers['Cache-Control'] == 'no-store, max-age=0'
    assert api_response.headers['Pragma'] == 'no-cache'


def test_production_rejects_default_secrets(monkeypatch):
    production = config['production']
    monkeypatch.setattr(production, 'SECRET_KEY', 'dev-secret-key-change-in-production')
    monkeypatch.setattr(production, 'JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
    monkeypatch.setattr(production, 'ENCRYPTION_KEY', None)

    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        create_app('production')


def test_production_rejects_wildcard_cors(monkeypatch):
    production = config['production']
    monkeypatch.setattr(production, 'SECRET_KEY', 's' * 32)
    monkeypatch.setattr(production, 'JWT_SECRET_KEY', 'j' * 32)
    monkeypatch.setattr(
        production,
        'ENCRYPTION_KEY',
        Fernet.generate_key().decode(),
    )
    monkeypatch.setattr(production, 'CORS_ORIGINS', ['*'])

    with pytest.raises(RuntimeError, match='CORS_ORIGINS'):
        create_app('production')


def test_production_requires_distinct_session_and_jwt_secrets(monkeypatch):
    production = config['production']
    shared_secret = 'shared-production-secret-value!!'
    monkeypatch.setattr(production, 'SECRET_KEY', shared_secret)
    monkeypatch.setattr(production, 'JWT_SECRET_KEY', shared_secret)
    monkeypatch.setattr(
        production,
        'ENCRYPTION_KEY',
        Fernet.generate_key().decode(),
    )
    monkeypatch.setattr(
        production,
        'CORS_ORIGINS',
        ['https://portfolio.example'],
    )

    with pytest.raises(RuntimeError, match='distinct SECRET_KEY'):
        create_app('production')


def test_unknown_environment_fails_closed(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'staging-typo')

    with pytest.raises(RuntimeError, match='Unsupported FLASK_ENV'):
        create_app()


def test_factory_normalizes_comma_separated_cors_origins():
    app = create_app({
        **TEST_CONFIG,
        'CORS_ORIGINS': (
            'https://portfolio.example, https://family.example, '
        ),
    })

    assert app.config['CORS_ORIGINS'] == [
        'https://portfolio.example',
        'https://family.example',
    ]


def test_invalid_factory_override_fails_fast():
    with pytest.raises(TypeError, match='config_overrides'):
        create_app(object())


def test_sqlite_connections_enforce_foreign_keys():
    app = create_app(TEST_CONFIG)

    with app.app_context():
        db.create_all()
        try:
            assert db.session.execute(
                text('PRAGMA foreign_keys')
            ).scalar_one() == 1

            db.session.add(
                Account(
                    user_id=999_999,
                    account_name='Orphaned account',
                    api_key_encrypted='key',
                    api_secret_encrypted='secret',
                )
            )
            with pytest.raises(IntegrityError):
                db.session.commit()
        finally:
            db.session.rollback()
            db.drop_all()
