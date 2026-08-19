"""
Account management endpoints.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError
from urllib.parse import urlparse

from app.database import db
from app.models import Account
from app.services.kite_service import KiteService
from app.utils.auth import current_user_id, owned_account
from app.utils.encryption import get_encryptor
from app.utils.rate_limiter import user_rate_limit
from app.utils.validators import validate_account_data
import logging

logger = logging.getLogger(__name__)

accounts_bp = Blueprint('accounts', __name__, url_prefix='/api/accounts')


def _generate_access_token(api_key, api_secret, request_token):
    """Exchange a request token for an access token."""
    kite_service = KiteService(api_key=api_key, api_secret=api_secret)
    return kite_service.generate_session(request_token)


def _generate_login_url(api_key):
    """Build a Kite login URL without exposing the stored API key."""
    return KiteService(
        api_key=api_key,
        api_secret='not-used-for-login-url',
    ).get_login_url()


@accounts_bp.route('', methods=['GET'])
@jwt_required()
def get_accounts():
    """Get the authenticated user's Zerodha accounts."""
    accounts = Account.query.filter_by(user_id=current_user_id()).order_by(
        Account.account_name.asc()
    ).all()

    return jsonify({
        'accounts': [account.to_dict() for account in accounts],
        'count': len(accounts)
    }), 200


@accounts_bp.route('/<int:account_id>', methods=['GET'])
@jwt_required()
def get_account(account_id):
    """Get one owned Zerodha account."""
    account = owned_account(account_id)

    if not account:
        return jsonify({'error': 'Account not found'}), 404

    return jsonify(account.to_dict()), 200


@accounts_bp.route('/<int:account_id>/login-url', methods=['GET'])
@jwt_required()
@user_rate_limit(max_requests=30, window_minutes=60)
def get_account_login_url(account_id):
    """Return the trusted broker-login URL for one owned account."""
    account = owned_account(account_id)
    if not account:
        return jsonify({'error': 'Account not found'}), 404

    try:
        api_key = get_encryptor().decrypt(account.api_key_encrypted)
        login_url = _generate_login_url(api_key)
        parsed_url = urlparse(login_url)
        if (
            parsed_url.scheme != 'https'
            or parsed_url.hostname != 'kite.zerodha.com'
        ):
            raise ValueError('Untrusted Kite login URL')
        return jsonify({
            'login_url': login_url,
        }), 200
    except Exception:
        logger.error(
            "Failed to build Kite login URL for account %s",
            account_id,
        )
        return jsonify({'error': 'Failed to generate login URL'}), 500


@accounts_bp.route('', methods=['POST'])
@jwt_required()
def create_account():
    """Create new account"""
    data = request.get_json(silent=True)

    # Validate input
    is_valid, error_msg = validate_account_data(data)
    if not is_valid:
        return jsonify({'error': error_msg}), 400

    user_id = current_user_id()
    account_name = data['account_name'].strip()
    existing = Account.query.filter_by(
        user_id=user_id,
        account_name=account_name,
    ).first()
    if existing:
        return jsonify({'error': 'Account name already exists'}), 400

    try:
        # Encrypt credentials
        encryptor = get_encryptor()

        request_token = data['request_token'].strip()
        try:
            access_token = _generate_access_token(
                data['api_key'].strip(),
                data['api_secret'].strip(),
                request_token,
            )
        except Exception:
            logger.warning(
                'Kite request-token exchange failed while creating account'
            )
            return jsonify({
                'error': 'Failed to generate access token from request token'
            }), 400

        account = Account(
            account_name=account_name,
            user_id=user_id,
            api_key_encrypted=encryptor.encrypt(data['api_key'].strip()),
            api_secret_encrypted=encryptor.encrypt(
                data['api_secret'].strip()
            ),
            access_token_encrypted=encryptor.encrypt(access_token),
            # Request tokens are one-time exchange material and are not
            # retained after a successful exchange.
            request_token_encrypted=None,
            is_active=True
        )

        db.session.add(account)
        db.session.commit()

        logger.info(f"Created account: {account.account_name}")

        return jsonify(account.to_dict()), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Account name already exists'}), 409
    except Exception:
        db.session.rollback()
        logger.error("Unexpected error while creating account")
        return jsonify({'error': 'Failed to create account'}), 500


@accounts_bp.route('/<int:account_id>', methods=['PUT'])
@jwt_required()
def update_account(account_id):
    """Update account"""
    account = owned_account(account_id)

    if not account:
        return jsonify({'error': 'Account not found'}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return jsonify({'error': 'Invalid JSON data'}), 400

    allowed_fields = {
        'account_name',
        'api_key',
        'api_secret',
        'request_token',
        'is_active',
    }
    unexpected = sorted(set(data) - allowed_fields)
    if unexpected:
        return jsonify({'error': f'Unsupported field: {unexpected[0]}'}), 400

    for field in ('api_key', 'api_secret'):
        if field in data:
            value = data[field]
            if (
                not isinstance(value, str)
                or not 10 <= len(value.strip()) <= 255
            ):
                return jsonify({'error': f'Invalid {field}'}), 400
    if 'request_token' in data:
        request_token = data['request_token']
        if (
            not isinstance(request_token, str)
            or not 1 <= len(request_token.strip()) <= 2048
        ):
            return jsonify({'error': 'Invalid request_token'}), 400
    if 'is_active' in data and not isinstance(data['is_active'], bool):
        return jsonify({'error': 'is_active must be a boolean'}), 400
    if (
        ('api_key' in data or 'api_secret' in data)
        and 'request_token' not in data
    ):
        return jsonify({
            'error': (
                'A new request_token is required when changing Kite '
                'credentials'
            )
        }), 400

    try:
        if 'account_name' in data:
            if not isinstance(data['account_name'], str):
                return jsonify({'error': 'Invalid account name'}), 400
            account_name = data['account_name'].strip()
            if not account_name or len(account_name) > 100:
                return jsonify({'error': 'Invalid account name'}), 400
            duplicate = Account.query.filter(
                Account.user_id == account.user_id,
                Account.account_name == account_name,
                Account.id != account.id,
            ).first()
            if duplicate:
                return jsonify({'error': 'Account name already exists'}), 409
            account.account_name = account_name

        if 'request_token' in data:
            encryptor = get_encryptor()
            current_api_key = (
                data['api_key'].strip()
                if 'api_key' in data
                else encryptor.decrypt(account.api_key_encrypted)
            )
            current_api_secret = (
                data['api_secret'].strip()
                if 'api_secret' in data
                else encryptor.decrypt(account.api_secret_encrypted)
            )
            try:
                generated_token = _generate_access_token(
                    current_api_key,
                    current_api_secret,
                    data['request_token'].strip(),
                )
            except Exception:
                logger.warning(
                    'Kite request-token exchange failed while updating '
                    'account %s',
                    account.id,
                )
                db.session.rollback()
                return jsonify({
                    'error': (
                        'Failed to generate access token from request token'
                    )
                }), 400

            if 'api_key' in data:
                account.api_key_encrypted = encryptor.encrypt(current_api_key)
            if 'api_secret' in data:
                account.api_secret_encrypted = encryptor.encrypt(
                    current_api_secret
                )
            account.access_token_encrypted = encryptor.encrypt(generated_token)
            account.request_token_encrypted = None
            account.needs_reauth = False

        if 'is_active' in data:
            account.is_active = data['is_active']

        db.session.commit()

        logger.info(f"Updated account: {account.account_name}")

        return jsonify(account.to_dict()), 200

    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Account name already exists'}), 409
    except Exception:
        db.session.rollback()
        logger.error("Unexpected error while updating account %s", account_id)
        return jsonify({'error': 'Failed to update account'}), 500


@accounts_bp.route('/<int:account_id>', methods=['DELETE'])
@jwt_required()
def delete_account(account_id):
    """Deactivate account"""
    account = owned_account(account_id)

    if not account:
        return jsonify({'error': 'Account not found'}), 404

    try:
        # Soft delete by deactivating
        account.is_active = False
        db.session.commit()

        logger.info(f"Deactivated account: {account.account_name}")

        return jsonify({'message': 'Account deactivated successfully'}), 200

    except Exception:
        db.session.rollback()
        logger.error("Unexpected error while deactivating account %s", account_id)
        return jsonify({'error': 'Failed to delete account'}), 500
