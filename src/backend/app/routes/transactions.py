"""
Transaction routes for listing, searching, and managing transactions.
"""
import logging

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.transaction_service import TransactionService

transactions_bp = Blueprint('transactions', __name__)
logger = logging.getLogger(__name__)
TRANSACTION_QUERY_FIELDS = {
    'date_from',
    'date_to',
    'type',
    'category_id',
    'search',
    'sort_by',
    'order',
    'page',
    'limit',
}


def _reject_unknown_query_fields():
    unexpected = sorted(set(request.args) - TRANSACTION_QUERY_FIELDS)
    if unexpected:
        return jsonify({
            'error': f'Unsupported query parameter: {unexpected[0]}'
        }), 400
    return None


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
    validation_error = _reject_unknown_query_fields()
    if validation_error:
        return validation_error

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
    except Exception:
        logger.exception('Failed to list transactions')
        return jsonify({'error': 'Internal server error'}), 500


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
    validation_error = _reject_unknown_query_fields()
    if validation_error:
        return validation_error

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
    except Exception:
        logger.exception('Failed to search transactions')
        return jsonify({'error': 'Internal server error'}), 500


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
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({'error': 'No data provided'}), 400
    unexpected = sorted(set(data) - {'category_id', 'notes', 'verified'})
    if unexpected:
        return jsonify({'error': f'Unsupported field: {unexpected[0]}'}), 400
    category_id = data.get('category_id')
    if 'category_id' in data and category_id is not None and (
        isinstance(category_id, bool)
        or not isinstance(category_id, int)
        or category_id <= 0
    ):
        return jsonify({
            'error': 'category_id must be a positive integer or null'
        }), 400
    notes = data.get('notes')
    if 'notes' in data and notes is not None and (
        not isinstance(notes, str) or len(notes) > 1000
    ):
        return jsonify({
            'error': 'notes must contain at most 1000 characters or be null'
        }), 400
    if 'verified' in data and not isinstance(data['verified'], bool):
        return jsonify({'error': 'verified must be a boolean'}), 400

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
    except Exception:
        db.session.rollback()
        logger.exception('Failed to update transaction %s', transaction_id)
        return jsonify({'error': 'Internal server error'}), 500


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
    except Exception:
        db.session.rollback()
        logger.exception('Failed to delete transaction %s', transaction_id)
        return jsonify({'error': 'Internal server error'}), 500


@transactions_bp.route('/transactions/bulk-recategorize', methods=['POST'])
@jwt_required()
def bulk_recategorize():
    """
    Bulk recategorize multiple transactions at once.

    Body:
        {
            "transaction_ids": [1, 2, 3, ...],
            "category_id": 5
        }

    Returns:
        200: {updated_count: 10, updated_ids: [...]}
        400: Invalid data
        403: Access denied for one or more transactions
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({'error': 'No data provided'}), 400
    unexpected = sorted(set(data) - {'transaction_ids', 'category_id'})
    if unexpected:
        return jsonify({'error': f'Unsupported field: {unexpected[0]}'}), 400

    transaction_ids = data.get('transaction_ids', [])
    category_id = data.get('category_id')

    if (
        not isinstance(transaction_ids, list)
        or not 1 <= len(transaction_ids) <= 500
        or any(
            isinstance(transaction_id, bool)
            or not isinstance(transaction_id, int)
            or transaction_id <= 0
            for transaction_id in transaction_ids
        )
        or len(set(transaction_ids)) != len(transaction_ids)
    ):
        return jsonify({
            'error': (
                'transaction_ids must contain 1-500 unique positive integers'
            )
        }), 400

    if (
        isinstance(category_id, bool)
        or not isinstance(category_id, int)
        or category_id <= 0
    ):
        return jsonify({'error': 'category_id must be a positive integer'}), 400

    try:
        result = TransactionService.bulk_recategorize(transaction_ids, category_id, user_id)
        return jsonify(result), 200
    except ValueError as e:
        error_msg = str(e)
        if "access denied" in error_msg.lower():
            return jsonify({'error': error_msg}), 403
        else:
            return jsonify({'error': error_msg}), 400
    except Exception:
        logger.exception('Failed to bulk recategorize transactions')
        return jsonify({'error': 'Internal server error'}), 500
