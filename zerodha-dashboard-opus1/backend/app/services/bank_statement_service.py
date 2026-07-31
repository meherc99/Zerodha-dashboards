"""
Bank statement service for handling PDF uploads and statement management.
"""
import hashlib
import os
import stat
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from sqlalchemy.exc import IntegrityError

from app.database import db
from app.models.bank_statement import BankStatement
from app.models.bank_account import BankAccount
from app.models.transaction_category import TransactionCategory
import logging

logger = logging.getLogger(__name__)

# Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {'pdf'}
DB_MONEY_MAX = Decimal('9999999999999.99')
OPERATION_LEASE = timedelta(minutes=15)
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
        """Create private storage and secure every newly created parent."""
        BankStatementService.harden_upload_permissions()
        os.makedirs(directory_path, mode=0o700, exist_ok=True)
        # ``makedirs`` applies its explicit mode only to the leaf directory.
        # Reconcile the whole tree before any sensitive bytes are written.
        BankStatementService.harden_upload_permissions()

    @staticmethod
    def _harden_directory_contents(directory_fd):
        """Harden one directory tree without following filesystem links."""
        nofollow = getattr(os, 'O_NOFOLLOW', 0)
        if not nofollow:
            raise RuntimeError(
                'Statement storage requires no-follow filesystem support'
            )
        common_flags = os.O_RDONLY | nofollow | getattr(os, 'O_CLOEXEC', 0)

        for entry_name in os.listdir(directory_fd):
            metadata = os.stat(
                entry_name,
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
            if stat.S_ISLNK(metadata.st_mode):
                raise RuntimeError(
                    'Statement storage contains an unsafe symbolic link'
                )

            if stat.S_ISDIR(metadata.st_mode):
                child_fd = os.open(
                    entry_name,
                    common_flags | getattr(os, 'O_DIRECTORY', 0),
                    dir_fd=directory_fd,
                )
                try:
                    if not stat.S_ISDIR(os.fstat(child_fd).st_mode):
                        raise RuntimeError(
                            'Statement storage changed during validation'
                        )
                    os.fchmod(child_fd, 0o700)
                    BankStatementService._harden_directory_contents(child_fd)
                finally:
                    os.close(child_fd)
                continue

            if not stat.S_ISREG(metadata.st_mode):
                raise RuntimeError(
                    'Statement storage contains an unsafe file type'
                )

            file_fd = os.open(
                entry_name,
                common_flags | getattr(os, 'O_NONBLOCK', 0),
                dir_fd=directory_fd,
            )
            try:
                if not stat.S_ISREG(os.fstat(file_fd).st_mode):
                    raise RuntimeError(
                        'Statement storage changed during validation'
                    )
                os.fchmod(file_fd, 0o600)
            finally:
                os.close(file_fd)

    @staticmethod
    def harden_upload_permissions():
        """Reconcile legacy statement storage before serving requests.

        Older releases did not consistently protect parent directories or
        existing files. Startup walks only the configured private storage root,
        rejects links and special files, and applies owner-only permissions.
        """
        storage_root = os.path.abspath(UPLOAD_BASE_DIR)
        try:
            if not os.path.lexists(storage_root):
                os.makedirs(storage_root, mode=0o700, exist_ok=False)
            if os.path.realpath(storage_root) != storage_root:
                raise RuntimeError(
                    'Statement storage path must not contain symbolic links'
                )

            nofollow = getattr(os, 'O_NOFOLLOW', 0)
            if not nofollow:
                raise RuntimeError(
                    'Statement storage requires no-follow filesystem support'
                )
            root_fd = os.open(
                storage_root,
                os.O_RDONLY
                | nofollow
                | getattr(os, 'O_DIRECTORY', 0)
                | getattr(os, 'O_CLOEXEC', 0),
            )
            try:
                if not stat.S_ISDIR(os.fstat(root_fd).st_mode):
                    raise RuntimeError(
                        'Statement storage root is not a directory'
                    )
                os.fchmod(root_fd, 0o700)
                BankStatementService._harden_directory_contents(root_fd)
            finally:
                os.close(root_fd)
        except RuntimeError:
            raise
        except OSError as error:
            raise RuntimeError(
                'Failed to secure private statement storage'
            ) from error

    @staticmethod
    def _file_sha256(file):
        """Hash an upload without retaining its contents in memory."""
        digest = hashlib.sha256()
        file.seek(0)
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
        file.seek(0)
        return digest.hexdigest()

    @staticmethod
    def _operation_is_busy(statement):
        """Return whether a transitional statement state still owns its lease."""
        now = datetime.utcnow()
        if statement.status == 'approving':
            return True
        if statement.status == 'parsing':
            return bool(
                statement.parsing_started_at
                and statement.parsing_started_at > now - OPERATION_LEASE
            )
        if statement.status == 'uploading':
            return bool(
                statement.created_at
                and statement.created_at > now - OPERATION_LEASE
            )
        return False

    @staticmethod
    def _cleanup_failed_upload(statement_id, file_path):
        """Remove a partial upload while retaining a durable retry tombstone."""
        file_removed = True
        if file_path and os.path.lexists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                file_removed = False
                logger.error("Failed to remove an incomplete statement upload")

        try:
            db.session.rollback()
            statement = db.session.get(BankStatement, statement_id)
            if not statement:
                return
            if file_removed:
                db.session.delete(statement)
            else:
                statement.status = 'deleting'
                statement.error_message = (
                    'Incomplete upload cleanup failed; retry deletion'
                )
            db.session.commit()
        except Exception:
            # The row was committed before the file write, so even a
            # bookkeeping outage leaves the path discoverable for recovery.
            db.session.rollback()
            logger.error("Failed to finalize incomplete upload cleanup")

    @staticmethod
    def _remove_account_uploads(account):
        """Remove every private statement file before account erasure.

        Database deletion only begins after all extant files are gone. If a
        filesystem operation fails, the still-active account remains
        reachable so the owner can retry instead of creating an inaccessible
        plaintext orphan.
        """
        statements = BankStatement.query.filter_by(
            bank_account_id=account.id
        ).all()
        if any(
            BankStatementService._operation_is_busy(statement)
            for statement in statements
        ):
            raise ValueError(
                'Bank account has a statement operation in progress'
            )

        storage_root = os.path.abspath(UPLOAD_BASE_DIR)
        account_directory = os.path.abspath(
            BankStatementService._get_upload_path(account.user_id, account.id)
        )
        try:
            contained = (
                account_directory != storage_root
                and os.path.commonpath([storage_root, account_directory])
                == storage_root
            )
        except ValueError:
            contained = False
        if (
            not contained
            or os.path.realpath(storage_root) != storage_root
            or (
                os.path.lexists(account_directory)
                and (
                    os.path.islink(account_directory)
                    or os.path.realpath(account_directory) != account_directory
                    or not os.path.isdir(account_directory)
                )
            )
        ):
            logger.error("Refused to traverse unsafe statement storage")
            raise RuntimeError(
                'Statement storage requires administrator review'
            )

        for statement in statements:
            file_path = statement.pdf_file_path
            if not file_path or not os.path.lexists(file_path):
                continue
            absolute_path = os.path.abspath(file_path)
            resolved_path = os.path.realpath(file_path)
            try:
                contained = (
                    os.path.commonpath([
                        account_directory,
                        absolute_path,
                    ])
                    == account_directory
                    and os.path.commonpath([
                        account_directory,
                        resolved_path,
                    ])
                    == account_directory
                )
            except ValueError:
                contained = False
            if (
                not contained
                or absolute_path != resolved_path
                or not stat.S_ISREG(os.lstat(absolute_path).st_mode)
            ):
                logger.error(
                    "Refused to delete statement file outside account storage"
                )
                raise RuntimeError(
                    'Statement storage requires administrator review'
                )
            try:
                os.remove(file_path)
            except OSError as error:
                raise RuntimeError(
                    'Failed to delete a bank statement file'
                ) from error

        # Older deployments and interrupted writes may have account-owned
        # files without a database row. The account directory is exclusively
        # private to this owner, so permanent deletion must erase those too.
        if os.path.isdir(account_directory):
            try:
                with os.scandir(account_directory) as entries:
                    for entry in entries:
                        metadata = entry.stat(follow_symlinks=False)
                        if not stat.S_ISREG(metadata.st_mode):
                            raise RuntimeError(
                                'Statement storage requires administrator review'
                            )
                        os.remove(entry.path)
            except RuntimeError:
                raise
            except OSError as error:
                raise RuntimeError(
                    'Failed to delete a bank statement file'
                ) from error

        return account_directory

    @staticmethod
    def permanently_delete_account(account):
        """Erase a bank account, its financial rows, and uploaded PDFs."""
        account_id = account.id
        user_id = account.user_id
        try:
            if account.is_active:
                claimed = (
                    BankAccount.query.filter_by(
                        id=account_id,
                        user_id=user_id,
                        is_active=True,
                    )
                    .update(
                        {'is_active': False},
                        synchronize_session=False,
                    )
                )
                if claimed != 1:
                    db.session.rollback()
                    raise ValueError('Bank account is already being deleted')
                db.session.commit()

            account = db.session.get(BankAccount, account_id)
            if not account or account.user_id != user_id:
                raise ValueError('Bank account not found')
            account_directory = BankStatementService._remove_account_uploads(
                account
            )
        except Exception:
            db.session.rollback()
            remaining = db.session.get(BankAccount, account_id)
            if remaining and remaining.user_id == user_id:
                try:
                    remaining.is_active = True
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    logger.error(
                        "Failed to reactivate bank account after deletion error"
                    )
            raise

        user_directory = os.path.dirname(account_directory)
        try:
            db.session.delete(account)
            db.session.commit()
        except Exception as error:
            db.session.rollback()
            remaining = db.session.get(BankAccount, account_id)
            if remaining and remaining.user_id == user_id:
                try:
                    remaining.is_active = True
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    logger.error(
                        "Failed to reactivate bank account after database "
                        "deletion error"
                    )
            logger.error(
                "Failed to erase bank account %s after file cleanup",
                account_id,
            )
            raise RuntimeError('Failed to delete bank account') from error

        for directory in (account_directory, user_directory):
            try:
                if os.path.isdir(directory) and not os.listdir(directory):
                    os.rmdir(directory)
            except OSError:
                logger.warning(
                    "Failed to remove an empty statement directory"
                )

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

        # An extension alone is not a content check. Every PDF begins with this
        # signature, including PDFs that contain binary data after the header.
        signature = file.read(5)
        file.seek(0)
        if signature != b'%PDF-':
            raise ValueError('File content is not a valid PDF')

        account = BankAccount.query.filter_by(
            id=bank_account_id,
            user_id=user_id,
            is_active=True,
        ).first()
        if not account:
            raise ValueError('Bank account not found')

        file_sha256 = BankStatementService._file_sha256(file)
        if BankStatement.query.filter_by(
            bank_account_id=bank_account_id,
            file_sha256=file_sha256,
        ).first():
            raise ValueError(
                'This statement has already been uploaded for this account'
            )

        unique_filename = f"{uuid.uuid4()}.pdf"

        # Create directory structure
        upload_dir = BankStatementService._get_upload_path(user_id, bank_account_id)
        BankStatementService._ensure_upload_directory(upload_dir)

        # Full file path
        file_path = os.path.join(upload_dir, unique_filename)

        # Commit a durable ownership/path record before writing sensitive
        # bytes. A failed filesystem cleanup can then always be retried through
        # the authenticated statement lifecycle.
        statement = BankStatement(
            bank_account_id=bank_account_id,
            statement_period_start=date.today(),
            statement_period_end=date.today(),
            pdf_file_path=file_path,
            file_sha256=file_sha256,
            status='uploading',
        )
        try:
            # Serialize the durable upload record with account deletion.
            # Updating the owner row takes a write lock on supported databases;
            # a deletion that won the race makes this conditional claim fail.
            account_claimed = (
                BankAccount.query.filter_by(
                    id=bank_account_id,
                    user_id=user_id,
                    is_active=True,
                )
                .update(
                    {'updated_at': datetime.utcnow()},
                    synchronize_session=False,
                )
            )
            if account_claimed != 1:
                raise ValueError('Bank account not found')
            db.session.add(statement)
            db.session.commit()
        except IntegrityError as error:
            db.session.rollback()
            raise ValueError(
                'This statement has already been uploaded for this account'
            ) from error
        except ValueError:
            db.session.rollback()
            raise
        except Exception as error:
            db.session.rollback()
            logger.error("Failed to persist bank statement upload")
            raise RuntimeError('Failed to save statement') from error

        statement_id = statement.id
        try:
            file.save(file_path)
            os.chmod(file_path, 0o600)
            claimed = (
                BankStatement.query.filter_by(
                    id=statement_id,
                    status='uploading',
                )
                .update(
                    {'status': 'uploaded'},
                    synchronize_session=False,
                )
            )
            if claimed != 1:
                raise RuntimeError('Statement upload lease was lost')
            db.session.commit()
        except Exception as error:
            BankStatementService._cleanup_failed_upload(
                statement_id,
                file_path,
            )
            logger.error("Failed to save bank statement upload")
            raise RuntimeError('Failed to save statement') from error

        logger.info(
            "Created bank statement %s for account %s",
            statement_id,
            bank_account_id,
        )
        return statement_id

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
            user_id=user_id,
            is_active=True,
        ).first()

        if not account:
            raise ValueError('Bank account not found')

        # Get all statements for this account
        statements = BankStatement.query.filter_by(
            bank_account_id=bank_account_id
        ).order_by(BankStatement.upload_date.desc()).all()

        return [
            stmt.to_dict(include_parsed_data=False)
            for stmt in statements
        ]

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
            BankAccount.user_id == user_id,
            BankAccount.is_active.is_(True),
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
            BankAccount.user_id == user_id,
            BankAccount.is_active.is_(True),
        ).first()

        if not statement:
            raise ValueError('Statement not found')
        if BankStatementService._operation_is_busy(statement):
            raise ValueError('Statement is busy; try deletion again later')

        file_path = statement.pdf_file_path

        try:
            if statement.status != 'deleting':
                current_status = statement.status
                claimed = (
                    BankStatement.query.filter_by(
                        id=statement.id,
                        status=current_status,
                    )
                    .update(
                        {
                            'status': 'deleting',
                            'error_message': None,
                        },
                        synchronize_session=False,
                    )
                )
                if claimed != 1:
                    db.session.rollback()
                    raise RuntimeError(
                        'Statement changed while deletion was starting'
                    )
                db.session.commit()

            # The durable "deleting" row is a retryable tombstone. If file
            # removal fails, the API can safely retry without losing its path.
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError as error:
                    statement = db.session.get(BankStatement, statement_id)
                    if statement:
                        statement.status = 'deleting'
                        statement.error_message = (
                            'File deletion failed; retry deletion'
                        )
                        db.session.commit()
                    raise RuntimeError(
                        'Failed to delete statement file'
                    ) from error

            statement = db.session.get(BankStatement, statement_id)
            if statement:
                bank_account_id = statement.bank_account_id
                db.session.delete(statement)
                db.session.flush()
                BankStatementService._recalculate_account_statement_state(
                    bank_account_id
                )
                db.session.commit()

            if file_path:
                try:
                    dir_path = os.path.dirname(file_path)
                    if os.path.isdir(dir_path) and not os.listdir(dir_path):
                        os.rmdir(dir_path)
                except OSError:
                    logger.warning(
                        "Failed to clean up directory for statement %s",
                        statement_id,
                    )

            logger.info("Deleted bank statement %s", statement_id)
        except RuntimeError:
            db.session.rollback()
            raise
        except Exception as error:
            db.session.rollback()
            logger.error("Failed to delete statement %s", statement_id)
            raise RuntimeError('Failed to delete statement') from error

    @staticmethod
    def _recalculate_account_statement_state(bank_account_id: int):
        """Rebuild cached statement metadata after destructive changes."""
        from app.models.transaction import Transaction

        account = db.session.get(BankAccount, bank_account_id)
        if not account:
            return
        latest_statement = (
            BankStatement.query.filter_by(
                bank_account_id=bank_account_id,
                status='approved',
            )
            .order_by(
                BankStatement.statement_period_end.desc(),
                BankStatement.id.desc(),
            )
            .first()
        )
        latest_balance = (
            Transaction.query.filter(
                Transaction.bank_account_id == bank_account_id,
                Transaction.verified.is_(True),
                Transaction.running_balance.isnot(None),
            )
            .order_by(
                Transaction.transaction_date.desc(),
                Transaction.id.desc(),
            )
            .first()
        )
        account.last_statement_date = (
            latest_statement.statement_period_end
            if latest_statement
            else None
        )
        account.current_balance = (
            latest_balance.running_balance
            if latest_balance
            else (account.opening_balance or Decimal('0'))
        )

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
            BankAccount.user_id == user_id,
            BankAccount.is_active.is_(True),
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
                'transaction_date': txn.get('date'),
                'description': description,
                'amount': txn.get('amount'),
                'transaction_type': txn.get('transaction_type'),
                'running_balance': txn.get('balance'),
                'category_id': category_id,
                'category_confidence': confidence,
                'notes': '',
            }

            categorized_transactions.append(categorized_txn)

        # Get validation warnings
        from app.services.pdf_parser_service import PDFParserService
        validation_warnings = PDFParserService.get_validation_warnings(
            categorized_transactions
        )
        for message in parsed_data.get('validation_errors') or []:
            validation_warnings.append(
                {
                    'type': 'parser_validation',
                    'message': str(message),
                    'severity': 'warning',
                }
            )
        duplicate_statement_id = parsed_data.get('duplicate_statement_id')
        if duplicate_statement_id:
            validation_warnings.append(
                {
                    'type': 'duplicate_statement',
                    'message': (
                        'Another statement for this account overlaps this '
                        'period. Delete the earlier statement before approval.'
                    ),
                    'severity': 'error',
                    'statement_id': duplicate_statement_id,
                }
            )

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
    def _normalize_approval_transactions(transactions):
        """Validate and normalize the canonical statement-review DTO."""
        if (
            not isinstance(transactions, list)
            or not transactions
            or len(transactions) > 5000
        ):
            raise ValueError(
                'transactions must contain between 1 and 5000 items'
            )

        normalized = []
        allowed_fields = {
            'transaction_date',
            'description',
            'amount',
            'transaction_type',
            'running_balance',
            'category_id',
            'category_confidence',
            'notes',
        }
        for index, transaction in enumerate(transactions, start=1):
            if not isinstance(transaction, dict):
                raise ValueError(f'Transaction {index} must be an object')
            unexpected = sorted(set(transaction) - allowed_fields)
            if unexpected:
                raise ValueError(
                    f'Transaction {index} has unsupported field: '
                    f'{unexpected[0]}'
                )

            transaction_date = transaction.get('transaction_date')
            description = transaction.get('description')
            transaction_type = transaction.get('transaction_type')
            if not isinstance(transaction_date, str):
                raise ValueError(
                    f'Transaction {index} has an invalid transaction_date'
                )
            try:
                parsed_date = datetime.strptime(
                    transaction_date,
                    '%Y-%m-%d',
                ).date()
            except ValueError as error:
                raise ValueError(
                    f'Transaction {index} has an invalid transaction_date'
                ) from error
            if (
                not isinstance(description, str)
                or not 1 <= len(description.strip()) <= 500
            ):
                raise ValueError(
                    f'Transaction {index} has an invalid description'
                )
            if transaction_type not in {'credit', 'debit'}:
                raise ValueError(
                    f'Transaction {index} has invalid transaction_type'
                )

            try:
                amount = Decimal(str(transaction.get('amount')))
            except (InvalidOperation, TypeError, ValueError) as error:
                raise ValueError(
                    f'Transaction {index} has an invalid amount'
                ) from error
            if not amount.is_finite() or amount <= 0:
                raise ValueError(
                    f'Transaction {index} has an invalid amount'
                )
            if (
                amount > DB_MONEY_MAX
                or amount != amount.quantize(Decimal('0.01'))
            ):
                raise ValueError(
                    f'Transaction {index} amount exceeds database precision'
                )

            running_balance = transaction.get('running_balance')
            if running_balance is not None:
                try:
                    running_balance = Decimal(str(running_balance))
                except (InvalidOperation, TypeError, ValueError) as error:
                    raise ValueError(
                        f'Transaction {index} has an invalid running_balance'
                    ) from error
                if not running_balance.is_finite():
                    raise ValueError(
                        f'Transaction {index} has an invalid running_balance'
                    )
                if (
                    abs(running_balance) > DB_MONEY_MAX
                    or running_balance
                    != running_balance.quantize(Decimal('0.01'))
                ):
                    raise ValueError(
                        f'Transaction {index} running_balance exceeds '
                        'database precision'
                    )

            category_id = transaction.get('category_id')
            if category_id is not None and (
                isinstance(category_id, bool)
                or not isinstance(category_id, int)
            ):
                raise ValueError(
                    f'Transaction {index} has an invalid category_id'
                )
            notes = transaction.get('notes')
            if notes is not None and (
                not isinstance(notes, str) or len(notes) > 1000
            ):
                raise ValueError(f'Transaction {index} has invalid notes')

            category_confidence = transaction.get('category_confidence')
            if category_confidence is not None:
                try:
                    category_confidence = Decimal(
                        str(category_confidence)
                    )
                except (InvalidOperation, TypeError, ValueError) as error:
                    raise ValueError(
                        f'Transaction {index} has invalid '
                        'category_confidence'
                    ) from error
                if (
                    not category_confidence.is_finite()
                    or not Decimal('0') <= category_confidence <= Decimal('1')
                ):
                    raise ValueError(
                        f'Transaction {index} has invalid '
                        'category_confidence'
                    )

            normalized.append(
                {
                    'transaction_date': parsed_date,
                    'description': description.strip(),
                    'amount': amount,
                    'transaction_type': transaction_type,
                    'running_balance': running_balance,
                    'category_id': category_id,
                    'category_confidence': category_confidence,
                    'notes': notes.strip() if isinstance(notes, str) else None,
                }
            )

        category_ids = {
            transaction['category_id']
            for transaction in normalized
            if transaction['category_id'] is not None
        }
        if category_ids:
            existing_ids = {
                category_id
                for (category_id,) in (
                    db.session.query(TransactionCategory.id)
                    .filter(
                        TransactionCategory.id.in_(category_ids),
                        TransactionCategory.is_system.is_(True),
                    )
                    .all()
                )
            }
            missing_ids = sorted(category_ids - existing_ids)
            if missing_ids:
                raise ValueError(
                    f'Invalid category_id: {missing_ids[0]}'
                )
        return normalized

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

        # Get statement with join to verify ownership
        statement = db.session.query(BankStatement).join(BankAccount).filter(
            BankStatement.id == statement_id,
            BankAccount.user_id == user_id,
            BankAccount.is_active.is_(True),
        ).first()

        if not statement:
            raise ValueError('Statement not found')

        # Verify statement is in review status
        if statement.status != 'review':
            raise ValueError(f'Statement cannot be approved (current status: {statement.status})')

        normalized_transactions = (
            BankStatementService._normalize_approval_transactions(transactions)
        )
        duplicate = BankStatementService.find_duplicate_statement(
            statement.bank_account_id,
            statement.statement_period_start,
            statement.statement_period_end,
            exclude_statement_id=statement.id,
        )
        if duplicate:
            raise ValueError(
                'Another statement for this account overlaps this period'
            )

        try:
            account_claimed = (
                BankAccount.query.filter_by(
                    id=statement.bank_account_id,
                    user_id=user_id,
                    is_active=True,
                )
                .update(
                    {'updated_at': datetime.utcnow()},
                    synchronize_session=False,
                )
            )
            if account_claimed != 1:
                raise ValueError('Bank account not found')
            claimed = (
                BankStatement.query.filter_by(
                    id=statement.id,
                    status='review',
                )
                .update(
                    {'status': 'approving'},
                    synchronize_session=False,
                )
            )
            if claimed != 1:
                raise ValueError(
                    'Statement is already being approved or has changed'
                )
            statement.status = 'approving'

            # Get the locked bank account.
            bank_account = db.session.get(
                BankAccount,
                statement.bank_account_id,
            )
            if not bank_account:
                raise ValueError('Bank account not found')

            # Create Transaction records
            created_transactions = []
            for txn_data in normalized_transactions:
                # Create transaction
                transaction = Transaction(
                    statement_id=statement.id,
                    bank_account_id=statement.bank_account_id,
                    transaction_date=txn_data['transaction_date'],
                    description=txn_data['description'],
                    amount=txn_data['amount'],
                    transaction_type=txn_data['transaction_type'],
                    running_balance=txn_data['running_balance'],
                    category_id=txn_data.get('category_id'),
                    category_confidence=txn_data.get('category_confidence'),
                    notes=txn_data.get('notes'),
                    verified=True
                )

                db.session.add(transaction)
                created_transactions.append(transaction)

            # Flush to get transaction IDs
            db.session.flush()

            # Update statement status to approved
            statement.status = 'approved'
            statement.parsed_data = None
            statement.parsing_template_id = None
            db.session.flush()

            # Approval order is not necessarily statement order. Rebuild the
            # cache from all approved data so an older statement cannot move
            # the displayed balance or statement date backward.
            BankStatementService._recalculate_account_statement_state(
                statement.bank_account_id
            )

            # Commit all changes
            db.session.commit()

            logger.info(
                f"Approved statement {statement_id}, created {len(created_transactions)} transactions"
            )

            return {
                'transaction_count': len(created_transactions),
                'transaction_ids': [txn.id for txn in created_transactions]
            }

        except ValueError:
            db.session.rollback()
            raise
        except Exception as error:
            db.session.rollback()
            logger.error("Failed to approve statement %s", statement_id)
            raise RuntimeError('Failed to approve statement') from error

    @staticmethod
    def save_template(statement_id: int, bank_name: str):
        """Reject legacy user-derived global templates.

        Templates in older databases remain readable for migration
        compatibility, but new private statement layouts are never persisted
        into a cross-tenant shared object.
        """
        raise RuntimeError('User-derived parsing templates are disabled')

    @staticmethod
    def find_duplicate_statement(
        bank_account_id: int,
        period_start: date,
        period_end: date,
        *,
        exclude_statement_id: int | None = None,
    ):
        """Return a reviewable/approved statement whose inclusive period overlaps."""
        if period_start > period_end:
            raise ValueError(
                'Statement period start must not be after period end'
            )
        query = BankStatement.query.filter(
            BankStatement.bank_account_id == bank_account_id,
            BankStatement.statement_period_start <= period_end,
            BankStatement.statement_period_end >= period_start,
            BankStatement.status.in_(['review', 'approving', 'approved']),
        )
        if exclude_statement_id is not None:
            query = query.filter(BankStatement.id != exclude_statement_id)
        return query.order_by(BankStatement.id.asc()).first()

    @staticmethod
    def detect_duplicate_statement(
        bank_account_id: int,
        period_start: date,
        period_end: date,
        exclude_statement_id: int | None = None,
    ) -> bool:
        """
        Check if another statement overlaps the inclusive period.

        Args:
            bank_account_id: ID of the bank account
            period_start: Statement period start date
            period_end: Statement period end date

        Returns:
            bool: True if duplicate exists, False otherwise
        """
        return BankStatementService.find_duplicate_statement(
            bank_account_id,
            period_start,
            period_end,
            exclude_statement_id=exclude_statement_id,
        ) is not None
