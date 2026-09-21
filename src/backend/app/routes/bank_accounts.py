"""
Bank account endpoints for managing user bank accounts.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from decimal import Decimal, InvalidOperation
from app.database import db
from app.models.bank_account import BankAccount
from app.services.bank_statement_service import BankStatementService
import logging

logger = logging.getLogger(__name__)

bank_accounts_bp = Blueprint('bank_accounts', __name__, url_prefix='/api/bank-accounts')
ACCOUNT_TYPES = {'savings', 'current', 'credit'}
SUPPORTED_CURRENCIES = {'INR', 'USD', 'EUR', 'GBP'}
DB_MONEY_MAX = Decimal('9999999999999.99')
CREATE_FIELDS = {
    'bank_name',
    'account_number',
    'account_type',
    'current_balance',
    'currency',
}
UPDATE_FIELDS = {'bank_name', 'account_number', 'account_type'}


def _clean_text(data, field, *, minimum=1, maximum):
    value = data.get(field)
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not minimum <= len(value) <= maximum:
        return None
    return value


@bank_accounts_bp.route('', methods=['GET'])
@jwt_required()
def list_bank_accounts():
    """
    List all active bank accounts for the authenticated user.

    Requires: JWT token in Authorization header

    Returns:
        200: List of bank account objects
        401: Unauthorized (no token or invalid token)
    """
    user_id = int(get_jwt_identity())

    accounts = BankAccount.query.filter_by(
        user_id=user_id,
        is_active=True
    ).all()

    return jsonify([account.to_dict() for account in accounts]), 200


@bank_accounts_bp.route('', methods=['POST'])
@jwt_required()
def create_bank_account():
    """
    Create a new bank account for the authenticated user.

    Request body:
        {
            "bank_name": "HDFC Bank" (required),
            "account_number": "1234567890" (required),
            "account_type": "savings" (optional, default: savings),
            "current_balance": 0.0 (optional, default: 0),
            "currency": "INR" (optional, default: INR)
        }

    Returns:
        201: Created bank account object
        400: {"error": "error message"}
        401: Unauthorized
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({'error': 'Invalid JSON data'}), 400

    unexpected = sorted(set(data) - CREATE_FIELDS)
    if unexpected:
        return jsonify({'error': f'Unsupported field: {unexpected[0]}'}), 400

    # Validate required fields
    bank_name = _clean_text(data, 'bank_name', maximum=100)
    account_number = _clean_text(
        data,
        'account_number',
        minimum=4,
        maximum=50,
    )

    if not bank_name:
        return jsonify({'error': 'Enter a valid bank_name'}), 400

    if not account_number:
        return jsonify({'error': 'Enter a valid account_number'}), 400

    account_type = data.get('account_type', 'savings')
    if account_type not in ACCOUNT_TYPES:
        return jsonify({'error': 'Unsupported account_type'}), 400
    currency = str(data.get('currency', 'INR')).upper()
    if currency not in SUPPORTED_CURRENCIES:
        return jsonify({'error': 'Unsupported currency'}), 400
    try:
        current_balance = Decimal(str(data.get('current_balance', 0)))
    except (InvalidOperation, TypeError, ValueError):
        return jsonify({'error': 'current_balance must be numeric'}), 400
    if not current_balance.is_finite():
        return jsonify({'error': 'current_balance must be finite'}), 400
    if (
        abs(current_balance) > DB_MONEY_MAX
        or current_balance != current_balance.quantize(Decimal('0.01'))
    ):
        return jsonify({
            'error': (
                'current_balance must fit 13 integer and 2 decimal places'
            )
        }), 400

    # Create new bank account
    account = BankAccount(
        user_id=user_id,
        bank_name=bank_name,
        account_number=account_number,
        account_type=account_type,
        opening_balance=current_balance,
        current_balance=current_balance,
        currency=currency,
    )

    try:
        db.session.add(account)
        db.session.commit()

        logger.info(f"Bank account created for user {user_id}: {bank_name}")

        return jsonify(account.to_dict()), 201

    except Exception:
        db.session.rollback()
        logger.error("Unexpected error while creating bank account")
        return jsonify({'error': 'Failed to create bank account'}), 500


@bank_accounts_bp.route('/<int:account_id>', methods=['GET'])
@jwt_required()
def get_bank_account(account_id):
    """
    Get a specific bank account by ID.

    Args:
        account_id: Bank account ID

    Requires: JWT token in Authorization header

    Returns:
        200: Bank account object
        404: {"error": "Bank account not found"}
        401: Unauthorized
    """
    user_id = int(get_jwt_identity())

    account = BankAccount.query.filter_by(
        id=account_id,
        user_id=user_id,
        is_active=True,
    ).first()

    if not account:
        return jsonify({'error': 'Bank account not found'}), 404

    return jsonify(account.to_dict()), 200


@bank_accounts_bp.route('/<int:account_id>', methods=['PUT'])
@jwt_required()
def update_bank_account(account_id):
    """
    Update a bank account's details.

    Only allows updating: bank_name, account_number, account_type

    Args:
        account_id: Bank account ID

    Request body:
        {
            "bank_name": "New Bank Name" (optional),
            "account_number": "9876543210" (optional),
            "account_type": "current" (optional)
        }

    Returns:
        200: Updated bank account object
        404: {"error": "Bank account not found"}
        400: {"error": "error message"}
        401: Unauthorized
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({'error': 'Invalid JSON data'}), 400

    unexpected = sorted(set(data) - UPDATE_FIELDS)
    if unexpected:
        return jsonify({'error': f'Unsupported field: {unexpected[0]}'}), 400

    account = BankAccount.query.filter_by(
        id=account_id,
        user_id=user_id,
        is_active=True,
    ).first()

    if not account:
        return jsonify({'error': 'Bank account not found'}), 404

    # Update allowed fields
    if 'bank_name' in data:
        bank_name = _clean_text(data, 'bank_name', maximum=100)
        if not bank_name:
            return jsonify({'error': 'Enter a valid bank_name'}), 400
        account.bank_name = bank_name

    if 'account_number' in data:
        account_number = _clean_text(
            data,
            'account_number',
            minimum=4,
            maximum=50,
        )
        if not account_number:
            return jsonify({'error': 'Enter a valid account_number'}), 400
        account.account_number = account_number

    if 'account_type' in data:
        if data['account_type'] not in ACCOUNT_TYPES:
            return jsonify({'error': 'Unsupported account_type'}), 400
        account.account_type = data['account_type']

    try:
        db.session.commit()

        logger.info(f"Bank account {account_id} updated by user {user_id}")

        return jsonify(account.to_dict()), 200

    except Exception:
        db.session.rollback()
        logger.error(
            "Unexpected error while updating bank account %s",
            account_id,
        )
        return jsonify({'error': 'Failed to update bank account'}), 500


@bank_accounts_bp.route('/<int:account_id>', methods=['DELETE'])
@jwt_required()
def delete_bank_account(account_id):
    """
    Permanently delete a bank account and its private statement files.

    Args:
        account_id: Bank account ID

    Returns:
        200: {"message": "Bank account deleted successfully"}
        404: {"error": "Bank account not found"}
        401: Unauthorized
    """
    user_id = int(get_jwt_identity())

    account = BankAccount.query.filter_by(
        id=account_id,
        user_id=user_id,
    ).first()

    if not account:
        return jsonify({'error': 'Bank account not found'}), 404

    try:
        BankStatementService.permanently_delete_account(account)

        logger.info(f"Bank account {account_id} deleted by user {user_id}")

        return jsonify({'message': 'Bank account deleted successfully'}), 200

    except ValueError as error:
        db.session.rollback()
        return jsonify({'error': str(error)}), 409
    except RuntimeError:
        db.session.rollback()
        logger.error(
            "Failed to permanently delete bank account %s",
            account_id,
        )
        return jsonify({'error': 'Failed to delete bank account'}), 500
