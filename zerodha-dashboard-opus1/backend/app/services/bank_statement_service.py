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
from app.models.parsing_template import ParsingTemplate
from app.services.pdf_parser_service import PDFParserService
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

            # Trigger PDF parsing synchronously
            try:
                logger.info(f"Triggering PDF parsing for statement {statement.id}")
                PDFParserService.parse_statement(statement.id)
                logger.info(f"PDF parsing completed for statement {statement.id}")
            except Exception as parse_error:
                logger.error(f"PDF parsing failed for statement {statement.id}: {str(parse_error)}")
                # Don't raise - let the upload succeed even if parsing fails
                # User can retry parsing later

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

    @staticmethod
    def get_statement_preview(statement_id: int, user_id: int):
        """
        Get statement preview with parsed transactions for review.

        Args:
            statement_id: ID of the statement
            user_id: ID of the user (for ownership verification)

        Returns:
            dict: Preview data with statement, transactions, and validation warnings

        Raises:
            ValueError: If statement not found, doesn't belong to user, or not ready for review
        """
        from app.models.transaction_category import TransactionCategory
        from app.services.transaction_categorization_service import TransactionCategorizationService
        from decimal import Decimal

        # Get statement with join to verify ownership
        statement = db.session.query(BankStatement).join(BankAccount).filter(
            BankStatement.id == statement_id,
            BankAccount.user_id == user_id
        ).first()

        if not statement:
            raise ValueError('Statement not found')

        # Check if statement is ready for review
        if statement.status != 'review':
            raise ValueError(f'Statement is not ready for review (current status: {statement.status})')

        if not statement.parsed_data:
            raise ValueError('Statement has no parsed data')

        # Get parsed data
        parsed_data = statement.parsed_data
        transactions = parsed_data.get('transactions', [])

        # Auto-categorize transactions
        categorized_transactions = []
        for txn in transactions:
            # Convert string amounts to Decimal for categorization
            amount = Decimal(txn.get('amount', '0'))
            description = txn.get('description', '')

            # Get category
            category_id, confidence = TransactionCategorizationService.auto_categorize(
                description, amount
            )

            # Build categorized transaction
            categorized_txn = {
                'date': txn.get('date'),
                'description': description,
                'amount': txn.get('amount'),
                'transaction_type': txn.get('transaction_type'),
                'balance': txn.get('balance'),
                'category_id': category_id,
                'category_confidence': confidence
            }

            categorized_transactions.append(categorized_txn)

        # Get validation warnings
        from app.services.pdf_parser_service import PDFParserService
        validation_warnings = PDFParserService.get_validation_warnings(categorized_transactions)

        # Build preview response
        preview = {
            'statement': {
                'id': statement.id,
                'bank_account_id': statement.bank_account_id,
                'status': statement.status,
                'statement_period_start': (statement.statement_period_start.isoformat()
                                          if statement.statement_period_start else None),
                'statement_period_end': (statement.statement_period_end.isoformat()
                                        if statement.statement_period_end else None),
                'upload_date': statement.upload_date.isoformat() if statement.upload_date else None
            },
            'transactions': categorized_transactions,
            'validation_warnings': validation_warnings
        }

        return preview

    @staticmethod
    def approve_statement(statement_id: int, transactions: list, user_id: int):
        """
        Approve statement and save transactions to database.

        Args:
            statement_id: ID of the statement
            transactions: List of transaction dicts to save
            user_id: ID of the user (for ownership verification)

        Returns:
            dict: Result with transaction count and IDs

        Raises:
            ValueError: If statement not found, doesn't belong to user, or validation fails
            RuntimeError: If database operation fails
        """
        from app.models.transaction import Transaction
        from decimal import Decimal

        # Get statement with join to verify ownership
        statement = db.session.query(BankStatement).join(BankAccount).filter(
            BankStatement.id == statement_id,
            BankAccount.user_id == user_id
        ).first()

        if not statement:
            raise ValueError('Statement not found')

        # Verify statement is in review status
        if statement.status != 'review':
            raise ValueError(f'Statement cannot be approved (current status: {statement.status})')

        # Validate transactions list
        if not transactions or len(transactions) == 0:
            raise ValueError('No transactions provided')

        # Validate each transaction has required fields
        required_fields = ['transaction_date', 'description', 'amount', 'transaction_type']
        for i, txn in enumerate(transactions):
            for field in required_fields:
                if field not in txn or txn[field] is None:
                    raise ValueError(f'Transaction {i + 1} is missing required field: {field}')

            # Validate transaction_type
            if txn['transaction_type'] not in ['credit', 'debit']:
                raise ValueError(f'Transaction {i + 1} has invalid transaction_type')

        try:
            # Get bank account
            bank_account = BankAccount.query.get(statement.bank_account_id)
            if not bank_account:
                raise ValueError('Bank account not found')

            # Create Transaction records
            created_transactions = []
            last_balance = None

            for txn_data in transactions:
                # Parse date
                txn_date = datetime.strptime(txn_data['transaction_date'], '%Y-%m-%d').date()

                # Create transaction
                transaction = Transaction(
                    statement_id=statement.id,
                    bank_account_id=statement.bank_account_id,
                    transaction_date=txn_date,
                    description=txn_data['description'],
                    amount=Decimal(str(txn_data['amount'])),
                    transaction_type=txn_data['transaction_type'],
                    running_balance=(Decimal(str(txn_data['running_balance']))
                                   if txn_data.get('running_balance') is not None else None),
                    category_id=txn_data.get('category_id'),
                    category_confidence=txn_data.get('category_confidence'),
                    notes=txn_data.get('notes'),
                    verified=False
                )

                db.session.add(transaction)
                created_transactions.append(transaction)

                # Track last balance
                if transaction.running_balance is not None:
                    last_balance = transaction.running_balance

            # Flush to get transaction IDs
            db.session.flush()

            # Update bank account with last balance and statement date
            if last_balance is not None:
                bank_account.current_balance = last_balance

            bank_account.last_statement_date = statement.statement_period_end

            # Update statement status to approved
            statement.status = 'approved'

            # Commit all changes
            db.session.commit()

            logger.info(
                f"Approved statement {statement_id}, created {len(created_transactions)} transactions"
            )

            # After successful approval, try to save a template for future use
            # Only save if this statement didn't use a template (new bank or failed template)
            if statement.parsed_data and not statement.parsing_template_id:
                try:
                    bank_name = statement.parsed_data.get('bank_name')
                    if bank_name and bank_name != 'Unknown':
                        BankStatementService.save_template(statement_id, bank_name)
                except Exception as template_error:
                    # Don't fail the approval if template saving fails
                    logger.warning(f"Failed to save template for statement {statement_id}: {template_error}")

            return {
                'transaction_count': len(created_transactions),
                'transaction_ids': [txn.id for txn in created_transactions]
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error approving statement: {str(e)}")
            raise RuntimeError(f"Failed to approve statement: {str(e)}")

    @staticmethod
    def save_template(statement_id: int, bank_name: str):
        """
        Save a parsing template from a successfully parsed statement.

        This enables the incremental intelligence feature - subsequent uploads
        from the same bank can use this template for instant parsing.

        Args:
            statement_id: ID of successfully parsed statement
            bank_name: Normalized bank name

        Returns:
            ParsingTemplate: Created template

        Raises:
            ValueError: If statement not found or invalid
        """
        statement = BankStatement.query.get(statement_id)
        if not statement:
            raise ValueError(f"Statement not found: {statement_id}")

        if statement.status != 'approved':
            raise ValueError(f"Can only save template from approved statements (current: {statement.status})")

        try:
            # Check if template already exists for this bank
            existing_template = ParsingTemplate.query.filter_by(
                bank_name=bank_name,
                is_active=True
            ).order_by(ParsingTemplate.template_version.desc()).first()

            # Determine version number
            version = 1
            if existing_template:
                version = existing_template.template_version + 1

            # Build extraction config from parsed data
            # This is a simplified version - in production, we'd extract more details
            extraction_config = {
                'parsing_method': 'pdfplumber',  # For now, only pdfplumber templates
                'date_format': '%Y-%m-%d',  # Could be detected from actual dates
                'currency_symbol': '₹',
                'saved_from_statement': statement_id,
                'columns': {
                    'date': 0,
                    'description': 1,
                    'amount': 2,
                    'type': 3,
                    'balance': 4
                }
            }

            # Create new template
            template = ParsingTemplate(
                bank_name=bank_name,
                template_version=version,
                extraction_config=extraction_config,
                created_from_statement_id=statement_id,
                success_count=0,  # Will be incremented when used
                failure_count=0,
                is_active=True
            )

            db.session.add(template)
            db.session.commit()

            logger.info(f"Created parsing template {template.id} for {bank_name} "
                       f"(v{version}) from statement {statement_id}")

            return template

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving template: {str(e)}")
            raise RuntimeError(f"Failed to save template: {str(e)}")

    @staticmethod
    def detect_duplicate_statement(bank_account_id: int, period_start: date, period_end: date) -> bool:
        """
        Check if a statement for the same period already exists.

        Args:
            bank_account_id: ID of the bank account
            period_start: Statement period start date
            period_end: Statement period end date

        Returns:
            bool: True if duplicate exists, False otherwise
        """
        existing = BankStatement.query.filter(
            BankStatement.bank_account_id == bank_account_id,
            BankStatement.statement_period_start == period_start,
            BankStatement.statement_period_end == period_end,
            BankStatement.status != 'failed'  # Ignore failed uploads
        ).first()

        return existing is not None
