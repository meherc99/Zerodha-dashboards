"""
Transaction routes for listing, searching, and managing transactions.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.transaction_service import TransactionService

transactions_bp = Blueprint('transactions', __name__)


@transactions_bp.route('/bank-accounts/<int:bank_account_id>/transactions', methods=['GET'])
@jwt_required()
def list_transactions(bank_account_id):
    """
    List transactions for a specific bank account with filters.

    Query params:
        - date_from: Start date (YYYY-MM-DD)
        - date_to: End date (YYYY-MM-DD)
        - type: 'credit', 'debit', or 'all'
        - category_id: Filter by category
        - search: Search in description
        - sort_by: 'date', 'amount', 'description'
        - order: 'asc' or 'desc'
        - page: Page number (default 1)
        - limit: Results per page (default 50, max 200)

    Returns:
        200: Paginated transaction list
        403: User doesn't own the bank account
        404: Bank account not found
        400: Invalid filters
    """
    user_id = int(get_jwt_identity())

    # Extract filters from query params
    filters = {
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to'),
        'type': request.args.get('type', 'all'),
        'category_id': request.args.get('category_id'),
        'search': request.args.get('search'),
        'sort_by': request.args.get('sort_by', 'date'),
        'order': request.args.get('order', 'desc'),
        'page': request.args.get('page', 1),
        'limit': request.args.get('limit', 50)
    }

    try:
        result = TransactionService.list_transactions(bank_account_id, filters, user_id)
        return jsonify(result), 200
    except ValueError as e:
        error_msg = str(e)
        if "access denied" in error_msg.lower():
            return jsonify({'error': 'Access denied'}), 403
        elif "not found" in error_msg.lower():
            return jsonify({'error': error_msg}), 404
        else:
            return jsonify({'error': error_msg}), 400
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@transactions_bp.route('/transactions/search', methods=['GET'])
@jwt_required()
def search_all_transactions():
    """
    Search transactions across all user's bank accounts.

    Uses same query params as list_transactions.

    Returns:
        200: Paginated transaction list with bank account info
        400: Invalid filters
    """
    user_id = int(get_jwt_identity())

    # Extract filters from query params
    filters = {
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to'),
        'type': request.args.get('type', 'all'),
        'category_id': request.args.get('category_id'),
        'search': request.args.get('search'),
        'sort_by': request.args.get('sort_by', 'date'),
        'order': request.args.get('order', 'desc'),
        'page': request.args.get('page', 1),
        'limit': request.args.get('limit', 50)
    }

    try:
        result = TransactionService.search_all_transactions(filters, user_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@transactions_bp.route('/transactions/<int:transaction_id>', methods=['PUT'])
@jwt_required()
def update_transaction(transaction_id):
    """
    Update a transaction. Only allows updating category_id, notes, and verified.

    Body:
        {
            "category_id": 2,
            "notes": "Updated note",
            "verified": true
        }

    Returns:
        200: Updated transaction
        403: User doesn't own the transaction
        404: Transaction not found
        400: Invalid data or attempting to update restricted fields
    """
    user_id = int(get_jwt_identity())

    # Get JSON data
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        updated_txn = TransactionService.update_transaction(transaction_id, data, user_id)
        return jsonify(updated_txn), 200
    except ValueError as e:
        error_msg = str(e)
        if "access denied" in error_msg.lower():
            return jsonify({'error': 'Access denied'}), 403
        elif "not found" in error_msg.lower():
            return jsonify({'error': error_msg}), 404
        else:
            return jsonify({'error': error_msg}), 400
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@transactions_bp.route('/transactions/<int:transaction_id>', methods=['DELETE'])
@jwt_required()
def delete_transaction(transaction_id):
    """
    Delete a transaction.

    Returns:
        200: Transaction deleted successfully
        403: User doesn't own the transaction
        404: Transaction not found
    """
    user_id = int(get_jwt_identity())

    try:
        TransactionService.delete_transaction(transaction_id, user_id)
        return jsonify({'message': 'Transaction deleted successfully'}), 200
    except ValueError as e:
        error_msg = str(e)
        if "access denied" in error_msg.lower():
            return jsonify({'error': 'Access denied'}), 403
        elif "not found" in error_msg.lower():
            return jsonify({'error': error_msg}), 404
        else:
            return jsonify({'error': error_msg}), 400
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
