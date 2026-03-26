"""
Bank statement service for handling PDF uploads and statement management.
"""
import os
import uuid
from datetime import date, datetime
from werkzeug.utils import secure_filename
from app.database import db
from app.models.bank_statement import BankStatement
from app.models.bank_account import BankAccount
import logging

logger = logging.getLogger(__name__)

# Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {'pdf'}
UPLOAD_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                               'uploads', 'bank_statements')


class BankStatementService:
    """Service for managing bank statement uploads and operations"""

    @staticmethod
    def _allowed_file(filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @staticmethod
    def _get_upload_path(user_id, bank_account_id):
        """Get the upload directory path for a user's bank account"""
        return os.path.join(UPLOAD_BASE_DIR, str(user_id), str(bank_account_id))

    @staticmethod
    def _ensure_upload_directory(directory_path):
        """Create upload directory if it doesn't exist"""
        os.makedirs(directory_path, exist_ok=True)

    @staticmethod
    def process_upload(file, bank_account_id: int, user_id: int) -> int:
        """
        Process and save uploaded PDF bank statement.

        Args:
            file: FileStorage object from request.files
            bank_account_id: ID of the bank account
            user_id: ID of the user (for verification and file path)

        Returns:
            int: Created statement ID

        Raises:
            ValueError: If validation fails
            RuntimeError: If file save or database operation fails
        """
        # Validate file presence
        if not file or file.filename == '':
            raise ValueError('No file provided')

        # Validate file type
        if not BankStatementService._allowed_file(file.filename):
            raise ValueError('Only PDF files are allowed')

        # Validate file size (read in chunks to avoid memory issues)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset to beginning

        if file_size > MAX_FILE_SIZE:
            raise ValueError(f'File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024 * 1024)}MB')

        if file_size == 0:
            raise ValueError('File is empty')

        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"

        # Create directory structure
        upload_dir = BankStatementService._get_upload_path(user_id, bank_account_id)
        BankStatementService._ensure_upload_directory(upload_dir)

        # Full file path
        file_path = os.path.join(upload_dir, unique_filename)

        try:
            # Save file to disk
            file.save(file_path)
            logger.info(f"Saved bank statement file to {file_path}")

            # Create database record with temporary dates (will be extracted from PDF later)
            # For now, use current date for both period start and end
            statement = BankStatement(
                bank_account_id=bank_account_id,
                statement_period_start=date.today(),  # Placeholder - will be updated after parsing
                statement_period_end=date.today(),    # Placeholder - will be updated after parsing
                pdf_file_path=file_path,
                status='uploaded'
            )

            db.session.add(statement)
            db.session.commit()

            logger.info(f"Created BankStatement record with ID {statement.id} for account {bank_account_id}")

            return statement.id

        except Exception as e:
            # Cleanup: delete file if database operation failed
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up file {file_path} after error")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup file {file_path}: {str(cleanup_error)}")

            db.session.rollback()
            logger.error(f"Error processing upload: {str(e)}")
            raise RuntimeError(f"Failed to save statement: {str(e)}")

    @staticmethod
    def get_statements_for_account(bank_account_id: int, user_id: int):
        """
        Get all statements for a bank account.

        Args:
            bank_account_id: ID of the bank account
            user_id: ID of the user (for ownership verification)

        Returns:
            list: List of statement dictionaries

        Raises:
            ValueError: If bank account not found or doesn't belong to user
        """
        # Verify account exists and belongs to user
        account = BankAccount.query.filter_by(
            id=bank_account_id,
            user_id=user_id
        ).first()

        if not account:
            raise ValueError('Bank account not found')

        # Get all statements for this account
        statements = BankStatement.query.filter_by(
            bank_account_id=bank_account_id
        ).order_by(BankStatement.upload_date.desc()).all()

        return [stmt.to_dict() for stmt in statements]

    @staticmethod
    def get_statement_details(statement_id: int, user_id: int):
        """
        Get details of a specific statement.

        Args:
            statement_id: ID of the statement
            user_id: ID of the user (for ownership verification)

        Returns:
            dict: Statement details

        Raises:
            ValueError: If statement not found or doesn't belong to user
        """
        # Get statement with join to verify ownership through bank_account
        statement = db.session.query(BankStatement).join(BankAccount).filter(
            BankStatement.id == statement_id,
            BankAccount.user_id == user_id
        ).first()

        if not statement:
            raise ValueError('Statement not found')

        return statement.to_dict()

    @staticmethod
    def delete_statement(statement_id: int, user_id: int):
        """
        Delete a statement and its associated file.

        Args:
            statement_id: ID of the statement
            user_id: ID of the user (for ownership verification)

        Raises:
            ValueError: If statement not found or doesn't belong to user
            RuntimeError: If deletion fails
        """
        # Get statement with join to verify ownership
        statement = db.session.query(BankStatement).join(BankAccount).filter(
            BankStatement.id == statement_id,
            BankAccount.user_id == user_id
        ).first()

        if not statement:
            raise ValueError('Statement not found')

        file_path = statement.pdf_file_path

        try:
            # Delete from database first
            db.session.delete(statement)
            db.session.commit()

            # Then delete file from disk
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted statement file: {file_path}")

                # Try to cleanup empty directories
                try:
                    dir_path = os.path.dirname(file_path)
                    if os.path.exists(dir_path) and not os.listdir(dir_path):
                        os.rmdir(dir_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup empty directory: {str(cleanup_error)}")

            logger.info(f"Deleted BankStatement with ID {statement_id}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting statement: {str(e)}")
            raise RuntimeError(f"Failed to delete statement: {str(e)}")
