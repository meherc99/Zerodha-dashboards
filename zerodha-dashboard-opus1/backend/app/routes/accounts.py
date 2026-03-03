"""
Account management endpoints.
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models import Account
from app.utils.encryption import get_encryptor
from app.utils.validators import validate_account_data
import logging

logger = logging.getLogger(__name__)

accounts_bp = Blueprint('accounts', __name__, url_prefix='/api/accounts')


@accounts_bp.route('', methods=['GET'])
def get_accounts():
    """Get all accounts"""
    accounts = Account.query.all()

    return jsonify({
        'accounts': [account.to_dict() for account in accounts],
        'count': len(accounts)
    }), 200


@accounts_bp.route('/<int:account_id>', methods=['GET'])
def get_account(account_id):
    """Get specific account"""
    account = Account.query.get(account_id)

    if not account:
        return jsonify({'error': 'Account not found'}), 404

    return jsonify(account.to_dict()), 200


@accounts_bp.route('', methods=['POST'])
def create_account():
    """Create new account"""
    data = request.get_json()

    # Validate input
    is_valid, error_msg = validate_account_data(data)
    if not is_valid:
        return jsonify({'error': error_msg}), 400

    # Check if account name already exists
    existing = Account.query.filter_by(account_name=data['account_name']).first()
    if existing:
        return jsonify({'error': 'Account name already exists'}), 400

    try:
        # Encrypt credentials
        encryptor = get_encryptor()

        account = Account(
            account_name=data['account_name'],
            api_key_encrypted=encryptor.encrypt(data['api_key']),
            api_secret_encrypted=encryptor.encrypt(data['api_secret']),
            access_token_encrypted=encryptor.encrypt(data.get('access_token')) if data.get('access_token') else None,
            request_token_encrypted=encryptor.encrypt(data.get('request_token')) if data.get('request_token') else None,
            is_active=True
        )

        db.session.add(account)
        db.session.commit()

        logger.info(f"Created account: {account.account_name}")

        return jsonify(account.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating account: {e}")
        return jsonify({'error': 'Failed to create account'}), 500


@accounts_bp.route('/<int:account_id>', methods=['PUT'])
def update_account(account_id):
    """Update account"""
    account = Account.query.get(account_id)

    if not account:
        return jsonify({'error': 'Account not found'}), 404

    data = request.get_json()

    try:
        encryptor = get_encryptor()

        # Update fields if provided
        if 'account_name' in data:
            account.account_name = data['account_name']

        if 'api_key' in data:
            account.api_key_encrypted = encryptor.encrypt(data['api_key'])

        if 'api_secret' in data:
            account.api_secret_encrypted = encryptor.encrypt(data['api_secret'])

        if 'access_token' in data:
            account.access_token_encrypted = encryptor.encrypt(data['access_token'])

        if 'request_token' in data:
            account.request_token_encrypted = encryptor.encrypt(data['request_token'])

        if 'is_active' in data:
            account.is_active = data['is_active']

        db.session.commit()

        logger.info(f"Updated account: {account.account_name}")

        return jsonify(account.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating account: {e}")
        return jsonify({'error': 'Failed to update account'}), 500


@accounts_bp.route('/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    """Deactivate account"""
    account = Account.query.get(account_id)

    if not account:
        return jsonify({'error': 'Account not found'}), 404

    try:
        # Soft delete by deactivating
        account.is_active = False
        db.session.commit()

        logger.info(f"Deactivated account: {account.account_name}")

        return jsonify({'message': 'Account deactivated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting account: {e}")
        return jsonify({'error': 'Failed to delete account'}), 500
