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
