"""
Bank account endpoints for managing user bank accounts.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.database import db
from app.models.bank_account import BankAccount
import logging

logger = logging.getLogger(__name__)

bank_accounts_bp = Blueprint('bank_accounts', __name__, url_prefix='/api/bank-accounts')


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
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Invalid JSON data'}), 400

    # Validate required fields
    bank_name = data.get('bank_name', '').strip()
    account_number = data.get('account_number', '').strip()

    if not bank_name:
        return jsonify({'error': 'bank_name is required'}), 400

    if not account_number:
        return jsonify({'error': 'account_number is required'}), 400

    # Create new bank account
    account = BankAccount(
        user_id=user_id,
        bank_name=bank_name,
        account_number=account_number,
        account_type=data.get('account_type', 'savings'),
        current_balance=data.get('current_balance', 0),
        currency=data.get('currency', 'INR')
    )

    try:
        db.session.add(account)
        db.session.commit()

        logger.info(f"Bank account created for user {user_id}: {bank_name}")

        return jsonify(account.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating bank account: {str(e)}")
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
        user_id=user_id
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
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Invalid JSON data'}), 400

    account = BankAccount.query.filter_by(
        id=account_id,
        user_id=user_id
    ).first()

    if not account:
        return jsonify({'error': 'Bank account not found'}), 404

    # Update allowed fields
    if 'bank_name' in data:
        account.bank_name = data['bank_name'].strip()

    if 'account_number' in data:
        account.account_number = data['account_number'].strip()

    if 'account_type' in data:
        account.account_type = data['account_type'].strip()

    try:
        db.session.commit()

        logger.info(f"Bank account {account_id} updated by user {user_id}")

        return jsonify(account.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating bank account: {str(e)}")
        return jsonify({'error': 'Failed to update bank account'}), 500


@bank_accounts_bp.route('/<int:account_id>', methods=['DELETE'])
@jwt_required()
def delete_bank_account(account_id):
    """
    Soft delete a bank account (sets is_active=False).

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
        user_id=user_id
    ).first()

    if not account:
        return jsonify({'error': 'Bank account not found'}), 404

    # Soft delete
    account.is_active = False

    try:
        db.session.commit()

        logger.info(f"Bank account {account_id} deleted by user {user_id}")

        return jsonify({'message': 'Bank account deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting bank account: {str(e)}")
        return jsonify({'error': 'Failed to delete bank account'}), 500
