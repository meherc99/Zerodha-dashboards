"""
Bank statement endpoints for uploading and managing PDF bank statements.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.bank_statement_service import BankStatementService
from app.models.bank_account import BankAccount
import logging

logger = logging.getLogger(__name__)

bank_statements_bp = Blueprint('bank_statements', __name__, url_prefix='/api')


@bank_statements_bp.route('/bank-accounts/<int:account_id>/statements/upload', methods=['POST'])
@jwt_required()
def upload_statement(account_id):
    """
    Upload a PDF bank statement for a bank account.

    Args:
        account_id: Bank account ID

    Requires:
        - JWT token in Authorization header
        - PDF file in multipart/form-data with key 'file'

    Returns:
        202: {"statement_id": int, "message": str, "status": "uploaded"}
        400: {"error": "error message"} - Validation errors
        404: {"error": "Bank account not found"} - Account doesn't exist or wrong user
        401: Unauthorized
        500: {"error": "error message"} - Server error
    """
    user_id = int(get_jwt_identity())

    # Verify bank account exists and belongs to user
    account = BankAccount.query.filter_by(
        id=account_id,
        user_id=user_id
    ).first()

    if not account:
        return jsonify({'error': 'Bank account not found'}), 404

    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    try:
        # Process upload using service
        statement_id = BankStatementService.process_upload(
            file=file,
            bank_account_id=account_id,
            user_id=user_id
        )

        logger.info(f"User {user_id} uploaded statement {statement_id} for account {account_id}")

        return jsonify({
            'statement_id': statement_id,
            'message': 'Statement uploaded successfully',
            'status': 'uploaded'
        }), 202  # 202 Accepted - ready for async processing

    except ValueError as e:
        # Validation errors (file type, size, etc.)
        logger.warning(f"Validation error during upload: {str(e)}")
        return jsonify({'error': str(e)}), 400

    except RuntimeError as e:
        # Server/processing errors
        logger.error(f"Runtime error during upload: {str(e)}")
        return jsonify({'error': str(e)}), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error during upload: {str(e)}")
        return jsonify({'error': 'Failed to upload statement'}), 500


@bank_statements_bp.route('/bank-accounts/<int:account_id>/statements', methods=['GET'])
@jwt_required()
def list_statements(account_id):
    """
    List all statements for a bank account.

    Args:
        account_id: Bank account ID

    Requires:
        - JWT token in Authorization header

    Returns:
        200: List of statement objects
        404: {"error": "Bank account not found"}
        401: Unauthorized
        500: {"error": "error message"}
    """
    user_id = int(get_jwt_identity())

    try:
        statements = BankStatementService.get_statements_for_account(
            bank_account_id=account_id,
            user_id=user_id
        )

        return jsonify(statements), 200

    except ValueError as e:
        # Bank account not found or doesn't belong to user
        return jsonify({'error': str(e)}), 404

    except Exception as e:
        logger.error(f"Error listing statements: {str(e)}")
        return jsonify({'error': 'Failed to list statements'}), 500


@bank_statements_bp.route('/statements/<int:statement_id>', methods=['GET'])
@jwt_required()
def get_statement(statement_id):
    """
    Get details of a specific statement.

    Args:
        statement_id: Statement ID

    Requires:
        - JWT token in Authorization header

    Returns:
        200: Statement object
        404: {"error": "Statement not found"}
        401: Unauthorized
        500: {"error": "error message"}
    """
    user_id = int(get_jwt_identity())

    try:
        statement = BankStatementService.get_statement_details(
            statement_id=statement_id,
            user_id=user_id
        )

        return jsonify(statement), 200

    except ValueError as e:
        # Statement not found or doesn't belong to user
        return jsonify({'error': str(e)}), 404

    except Exception as e:
        logger.error(f"Error getting statement details: {str(e)}")
        return jsonify({'error': 'Failed to get statement'}), 500


@bank_statements_bp.route('/statements/<int:statement_id>', methods=['DELETE'])
@jwt_required()
def delete_statement(statement_id):
    """
    Delete a statement and its associated PDF file.

    Args:
        statement_id: Statement ID

    Requires:
        - JWT token in Authorization header

    Returns:
        200: {"message": "Statement deleted successfully"}
        404: {"error": "Statement not found"}
        401: Unauthorized
        500: {"error": "error message"}
    """
    user_id = int(get_jwt_identity())

    try:
        BankStatementService.delete_statement(
            statement_id=statement_id,
            user_id=user_id
        )

        logger.info(f"User {user_id} deleted statement {statement_id}")

        return jsonify({'message': 'Statement deleted successfully'}), 200

    except ValueError as e:
        # Statement not found or doesn't belong to user
        return jsonify({'error': str(e)}), 404

    except RuntimeError as e:
        logger.error(f"Runtime error deleting statement: {str(e)}")
        return jsonify({'error': str(e)}), 500

    except Exception as e:
        logger.error(f"Unexpected error deleting statement: {str(e)}")
        return jsonify({'error': 'Failed to delete statement'}), 500


@bank_statements_bp.route('/statements/<int:statement_id>/preview', methods=['GET'])
@jwt_required()
def get_statement_preview(statement_id):
    """
    Get parsed statement data for review before approval.

    Args:
        statement_id: Statement ID

    Requires:
        - JWT token in Authorization header

    Returns:
        200: Preview data with statement, transactions (with auto-categorization), and validation warnings
        400: {"error": "error message"} - Statement not ready for review
        404: {"error": "Statement not found"} - Statement doesn't exist or wrong user
        401: Unauthorized
        500: {"error": "error message"} - Server error
    """
    user_id = int(get_jwt_identity())

    try:
        preview = BankStatementService.get_statement_preview(
            statement_id=statement_id,
            user_id=user_id
        )

        return jsonify(preview), 200

    except ValueError as e:
        # Statement not found or not ready for review
        error_msg = str(e)
        if 'not found' in error_msg.lower():
            return jsonify({'error': error_msg}), 404
        else:
            return jsonify({'error': error_msg}), 400

    except Exception as e:
        logger.error(f"Error getting statement preview: {str(e)}")
        return jsonify({'error': 'Failed to get statement preview'}), 500


@bank_statements_bp.route('/statements/<int:statement_id>/approve', methods=['POST'])
@jwt_required()
def approve_statement(statement_id):
    """
    Approve statement and save transactions to database.

    Args:
        statement_id: Statement ID

    Requires:
        - JWT token in Authorization header
        - JSON body with 'transactions' array

    Request Body:
        {
            "transactions": [
                {
                    "transaction_date": "2024-01-15",
                    "description": "BigBasket Online",
                    "amount": 2500.00,
                    "transaction_type": "debit",
                    "running_balance": 15000.00,
                    "category_id": 4,
                    "notes": "Weekly groceries"  # optional
                }
            ]
        }

    Returns:
        200: {"message": str, "transaction_count": int, "transaction_ids": [int]}
        400: {"error": "error message"} - Validation errors
        404: {"error": "Statement not found"} - Statement doesn't exist or wrong user
        401: Unauthorized
        500: {"error": "error message"} - Server error
    """
    user_id = int(get_jwt_identity())

    # Get JSON data
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()

    # Validate request body
    if 'transactions' not in data:
        return jsonify({'error': 'Missing transactions field'}), 400

    transactions = data['transactions']

    try:
        result = BankStatementService.approve_statement(
            statement_id=statement_id,
            transactions=transactions,
            user_id=user_id
        )

        logger.info(
            f"User {user_id} approved statement {statement_id} "
            f"with {result['transaction_count']} transactions"
        )

        return jsonify({
            'message': 'Statement approved successfully',
            'transaction_count': result['transaction_count'],
            'transaction_ids': result['transaction_ids']
        }), 200

    except ValueError as e:
        # Validation errors or statement not found
        error_msg = str(e)
        if 'not found' in error_msg.lower():
            return jsonify({'error': error_msg}), 404
        else:
            return jsonify({'error': error_msg}), 400

    except RuntimeError as e:
        logger.error(f"Runtime error approving statement: {str(e)}")
        return jsonify({'error': str(e)}), 500

    except Exception as e:
        logger.error(f"Unexpected error approving statement: {str(e)}")
        return jsonify({'error': 'Failed to approve statement'}), 500
