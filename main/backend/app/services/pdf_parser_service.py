"""
PDF Parser Service for extracting transaction data from bank statement PDFs.
"""
import re
import logging
import os
import json
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Tuple, Optional
import pdfplumber
from sqlalchemy import and_, or_
from app.database import db
from app.models.bank_statement import BankStatement
from app.models.parsing_template import ParsingTemplate

logger = logging.getLogger(__name__)
PARSING_LEASE_MINUTES = 15
MAX_PDF_PAGES = 200


class PDFParserService:
    """Service for parsing PDF bank statements using pdfplumber"""

    # Bank detection patterns
    BANK_PATTERNS = {
        'HDFC Bank': [r'HDFC\s+BANK', r'HDFC\s+Bank', r'HDFC'],
        'SBI': [r'STATE\s+BANK\s+OF\s+INDIA', r'STATE\s+BANK', r'SBI'],
        'ICICI Bank': [r'ICICI\s+BANK', r'ICICI\s+Bank', r'ICICI'],
        'Axis Bank': [r'AXIS\s+BANK', r'AXIS\s+Bank', r'Axis\s+Bank']
    }

    # Date patterns for parsing
    DATE_PATTERNS = [
        r'(\d{2})/(\d{2})/(\d{4})',  # DD/MM/YYYY
        r'(\d{2})-(\d{2})-(\d{4})',  # DD-MM-YYYY
        r'(\d{4})/(\d{2})/(\d{2})',  # YYYY/MM/DD
        r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
    ]

    @staticmethod
    def extract_text(pdf_path: str) -> str:
        """
        Extract text from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            str: Extracted text content

        Raises:
            RuntimeError: If PDF cannot be read
        """
        try:
            text_content = []
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) > MAX_PDF_PAGES:
                    raise ValueError(
                        f'PDF exceeds the maximum of {MAX_PDF_PAGES} pages'
                    )
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(page_text)

            return '\n'.join(text_content)

        except ValueError:
            raise
        except Exception as error:
            logger.error("Failed to extract text from bank statement PDF")
            raise RuntimeError('Failed to extract text from PDF') from error

    @staticmethod
    def detect_bank_name(text: str) -> str:
        """
        Detect bank name from PDF text using regex patterns.

        Args:
            text: Extracted PDF text

        Returns:
            str: Bank name ('HDFC Bank', 'SBI', 'ICICI Bank', 'Axis Bank', or 'Unknown')
        """
        text_upper = text.upper()

        for bank_name, patterns in PDFParserService.BANK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_upper):
                    return bank_name

        return 'Unknown'

    @staticmethod
    def extract_tables_from_pdf(pdf_path: str) -> List[List[List[str]]]:
        """
        Extract all tables from PDF using pdfplumber.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of tables, where each table is a list of rows

        Raises:
            RuntimeError: If PDF cannot be read
        """
        try:
            all_tables = []
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) > MAX_PDF_PAGES:
                    raise ValueError(
                        f'PDF exceeds the maximum of {MAX_PDF_PAGES} pages'
                    )
                for page in pdf.pages:
                    tables = page.extract_tables()
                    if tables:
                        all_tables.extend(tables)

            return all_tables

        except ValueError:
            raise
        except Exception as error:
            logger.error("Failed to extract tables from bank statement PDF")
            raise RuntimeError('Failed to extract tables from PDF') from error

    @staticmethod
    def identify_transaction_table(tables: List[List[List[str]]]) -> Optional[List[List[str]]]:
        """
        Identify the first transaction table from a list of extracted tables.

        This retains the original single-table return contract for callers
        that only need detection. Standard extraction uses
        ``identify_transaction_tables`` so page continuations are not lost.

        Args:
            tables: List of tables extracted from PDF

        Returns:
            Transaction table or None if not found
        """
        transaction_tables = PDFParserService.identify_transaction_tables(tables)
        return transaction_tables[0] if transaction_tables else None

    @staticmethod
    def _header_role(value: object) -> str:
        """Map bank-specific column labels to their parser role."""
        header = re.sub(r'[^a-z0-9]+', ' ', str(value or '').lower()).strip()

        if 'date' in header:
            return 'date'
        if any(word in header for word in ('description', 'narration', 'particular')):
            return 'description'
        if 'debit' in header or 'withdrawal' in header or header == 'dr':
            return 'debit'
        if 'credit' in header or 'deposit' in header or header == 'cr':
            return 'credit'
        if 'balance' in header or 'closing' in header:
            return 'balance'
        return 'other'

    @staticmethod
    def _header_signature(headers: List[str]) -> Tuple[str, ...]:
        """Return the ordered parser roles in a table header."""
        return tuple(
            PDFParserService._header_role(header)
            for header in headers
        )

    @staticmethod
    def _looks_like_transaction_table(table: List[List[str]]) -> bool:
        """Return whether a table has a supported transaction-table shape."""
        if not table or not table[0]:
            return False

        num_cols = len(table[0])
        if num_cols < 4 or num_cols > 6:
            return False

        first_row_is_data = PDFParserService._parse_date(table[0][0]) is not None
        if not first_row_is_data and len(table) < 2:
            return False

        data_rows = table if first_row_is_data else table[1:]
        return any(
            row
            and row[0]
            and PDFParserService._parse_date(row[0]) is not None
            for row in data_rows[:4]
        )

    @staticmethod
    def identify_transaction_tables(
        tables: List[List[List[str]]],
    ) -> List[List[List[str]]]:
        """
        Identify compatible transaction tables in extraction order.

        Banks commonly repeat the same transaction table on every page.
        Header aliases are compared by semantic role. A headerless
        continuation is accepted only when its width matches the first table,
        allowing it to inherit that table's column mapping safely.
        """
        transaction_tables = []
        reference_signature = None
        reference_column_count = None

        for table in tables:
            if not PDFParserService._looks_like_transaction_table(table):
                continue

            first_row_is_data = PDFParserService._parse_date(table[0][0]) is not None
            if first_row_is_data:
                if (
                    reference_signature is not None
                    and len(table[0]) == reference_column_count
                ):
                    transaction_tables.append(table)
                continue

            signature = PDFParserService._header_signature(table[0])
            if not ({'debit', 'credit'} & set(signature)):
                continue

            if reference_signature is None:
                reference_signature = signature
                reference_column_count = len(table[0])
                transaction_tables.append(table)
            elif signature == reference_signature:
                transaction_tables.append(table)

        return transaction_tables

    @staticmethod
    def _is_repeated_header(row: List[str], headers: List[str]) -> bool:
        """Detect a header repeated inside a continued transaction table."""
        if not row or PDFParserService._parse_date(row[0]) is not None:
            return False

        normalize = lambda values: [
            re.sub(r'\s+', ' ', str(value or '').strip().lower())
            for value in values
        ]
        if normalize(row) == normalize(headers):
            return True

        row_signature = PDFParserService._header_signature(row)
        return bool(row_signature) and row_signature == (
            PDFParserService._header_signature(headers)
        )

    @staticmethod
    def _parse_transaction_tables(
        tables: List[List[List[str]]],
    ) -> List[Dict]:
        """Flatten compatible tables into one ordered transaction sequence."""
        transaction_tables = PDFParserService.identify_transaction_tables(tables)
        if not transaction_tables:
            return []

        inherited_headers = transaction_tables[0][0]
        transactions = []

        for table in transaction_tables:
            first_row_is_data = PDFParserService._parse_date(table[0][0]) is not None
            headers = inherited_headers if first_row_is_data else table[0]
            rows = table if first_row_is_data else table[1:]

            for row in rows:
                if PDFParserService._is_repeated_header(row, headers):
                    continue
                transaction = PDFParserService.parse_transaction_row(row, headers)
                if transaction:
                    transactions.append(transaction)

        return transactions

    @staticmethod
    def _parse_date(date_str: str) -> Optional[date]:
        """
        Parse date string to date object.

        Args:
            date_str: Date string in various formats

        Returns:
            date object or None if parsing fails
        """
        if not date_str:
            return None

        date_str = str(date_str).strip()

        # Try different date formats
        formats = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%Y-%m-%d',
            '%d/%m/%y',
            '%d-%m-%y'
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.date()
            except ValueError:
                continue

        return None

    @staticmethod
    def _parse_amount(amount_str: str) -> Optional[Decimal]:
        """
        Parse amount string to Decimal.

        Args:
            amount_str: Amount string (may include commas, currency symbols)

        Returns:
            Decimal or None if parsing fails
        """
        if not amount_str or str(amount_str).strip() == '':
            return None

        # Clean amount string
        amount_str = str(amount_str).strip()
        # Remove currency symbols and commas
        amount_str = re.sub(r'[₹$,\s]', '', amount_str)

        # Handle empty strings after cleaning
        if not amount_str:
            return None

        try:
            return Decimal(amount_str)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def parse_transaction_row(row: List[str], headers: List[str]) -> Optional[Dict]:
        """
        Parse a single transaction table row.

        Args:
            row: Table row data
            headers: Table header row

        Returns:
            Transaction dict or None if row cannot be parsed
        """
        if not row or len(row) == 0:
            return None

        # Parse date from first column
        transaction_date = PDFParserService._parse_date(row[0])
        if not transaction_date:
            return None

        # Extract description (usually second column)
        description = str(row[1]).strip() if len(row) > 1 else ''
        if not description:
            return None

        # Find debit, credit, and balance columns
        debit_idx = None
        credit_idx = None
        balance_idx = None

        for idx, header in enumerate(headers):
            role = PDFParserService._header_role(header)
            if role == 'debit':
                debit_idx = idx
            elif role == 'credit':
                credit_idx = idx
            elif role == 'balance':
                balance_idx = idx

        # Parse amounts
        debit_amount = None
        credit_amount = None

        if debit_idx is not None and debit_idx < len(row):
            debit_amount = PDFParserService._parse_amount(row[debit_idx])

        if credit_idx is not None and credit_idx < len(row):
            credit_amount = PDFParserService._parse_amount(row[credit_idx])

        # Determine transaction type and amount
        if debit_amount and debit_amount > 0:
            transaction_type = 'debit'
            amount = debit_amount
        elif credit_amount and credit_amount > 0:
            transaction_type = 'credit'
            amount = credit_amount
        else:
            # Skip rows with no amount (might be headers or subtotals)
            return None

        # Parse balance
        balance = None
        if balance_idx is not None and balance_idx < len(row):
            balance = PDFParserService._parse_amount(row[balance_idx])

        return {
            'date': transaction_date,
            'description': description,
            'amount': amount,
            'transaction_type': transaction_type,
            'balance': balance
        }

    @staticmethod
    def validate_transactions(transactions: List[Dict]) -> Tuple[bool, List[str]]:
        """
        Validate running balance consistency.

        Args:
            transactions: List of parsed transactions

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        if not transactions:
            return False, ['No transactions found']

        errors = []

        # Check balance consistency
        for i in range(1, len(transactions)):
            prev_txn = transactions[i - 1]
            curr_txn = transactions[i]

            # Skip if either transaction doesn't have a balance
            if prev_txn.get('balance') is None or curr_txn.get('balance') is None:
                continue

            # Calculate expected balance
            prev_balance = prev_txn['balance']
            expected_balance = prev_balance

            if curr_txn['transaction_type'] == 'credit':
                expected_balance += curr_txn['amount']
            else:  # debit
                expected_balance -= curr_txn['amount']

            # Allow small rounding errors
            actual_balance = curr_txn['balance']
            diff = abs(expected_balance - actual_balance)

            if diff > Decimal('0.01'):
                errors.append(
                    f"Balance mismatch at transaction {i}: "
                    f"Expected {expected_balance}, got {actual_balance} "
                    f"(difference: {diff})"
                )

        return len(errors) == 0, errors

    @staticmethod
    def find_template(bank_name: str) -> Optional[ParsingTemplate]:
        """Return no legacy user-derived global template.

        Older rows remain in the schema so existing databases upgrade safely,
        but private statement layouts are not shared between tenants.
        """
        return None

    @staticmethod
    def extract_with_template(pdf_path: str, template: ParsingTemplate) -> Tuple[List[Dict], float]:
        """
        Extract transactions using saved template configuration.

        This is the fast path - uses saved extraction patterns instead of
        AI or complex table detection.

        Args:
            pdf_path: Path to PDF file
            template: ParsingTemplate with extraction config

        Returns:
            Tuple of (transactions list, confidence score)

        Raises:
            RuntimeError: If extraction fails
        """
        try:
            logger.info(f"Using template {template.id} for extraction")

            config = template.extraction_config
            parsing_method = config.get('parsing_method', 'pdfplumber')

            if parsing_method == 'pdfplumber':
                # Extract tables using pdfplumber
                tables = PDFParserService.extract_tables_from_pdf(pdf_path)

                if not tables:
                    raise RuntimeError("No tables found in PDF")

                transactions = PDFParserService._parse_transaction_tables(tables)
                if not transactions:
                    raise RuntimeError("No transaction table found")

                # Validate extracted data
                is_valid, errors = PDFParserService.validate_transactions(transactions)

                # Calculate confidence based on validation
                confidence = 0.9 if is_valid else 0.6

                logger.info(f"Template extraction: {len(transactions)} transactions, "
                           f"confidence={confidence:.2f}")

                return transactions, confidence

            else:
                # For AI-based templates, we'd call AI with hints from template
                # For now, fall back to standard extraction
                raise RuntimeError(f"Unsupported parsing method in template: {parsing_method}")

        except Exception as error:
            logger.warning("Bank statement template extraction failed")
            # Mark template failure
            template.mark_failure()
            db.session.commit()
            raise RuntimeError('Template extraction failed') from error

    @staticmethod
    def extract_with_pdfplumber(pdf_path: str) -> Tuple[List[Dict], float]:
        """
        Extract transactions using pdfplumber auto-detection.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Tuple of (transactions list, confidence score)

        Raises:
            RuntimeError: If extraction fails
        """
        try:
            logger.info("Extracting with pdfplumber auto-detection")

            # Extract tables
            tables = PDFParserService.extract_tables_from_pdf(pdf_path)
            if not tables:
                raise RuntimeError("No tables found in PDF")

            transactions = PDFParserService._parse_transaction_tables(tables)
            if not transactions:
                raise RuntimeError("No transaction table found")

            # Validate
            is_valid, errors = PDFParserService.validate_transactions(transactions)

            # Calculate confidence
            confidence = 0.8 if is_valid else 0.5

            logger.info(f"PDFPlumber extraction: {len(transactions)} transactions, "
                       f"confidence={confidence:.2f}")

            return transactions, confidence

        except Exception:
            logger.error("PDF table extraction failed")
            raise

    @staticmethod
    def fallback_to_ai(pdf_path: str, bank_name: str = None) -> Tuple[List[Dict], float]:
        """
        Use AI (Claude API or GPT-4 Vision) to extract transactions from PDF.

        This is the fallback when pdfplumber fails or has low confidence.
        Converts PDF to images and sends to vision API with structured prompt.

        **Current status: NOT IMPLEMENTED.**
        Always raises ``RuntimeError`` until the body below is filled in.
        Call sites in ``parse_statement`` catch this exception and gracefully
        continue with whatever pdfplumber produced, so the stub does **not**
        break normal parsing — it only means complex PDFs that pdfplumber
        cannot handle will fail rather than fall back to AI.

        To enable:
          1. ``pip install anthropic pdf2image`` (or ``openai`` instead)
          2. Set ``ANTHROPIC_API_KEY`` **or** ``OPENAI_API_KEY`` in the env
          3. Replace the ``raise RuntimeError`` below with the actual API call
             (see the commented-out example implementation that follows it)

        Args:
            pdf_path: Path to PDF file
            bank_name: Optional bank name hint for AI

        Returns:
            Tuple of (transactions list, confidence score)

        Raises:
            RuntimeError: Always, until this method is implemented
        """
        try:
            # Check if AI API is configured
            api_key = os.getenv('ANTHROPIC_API_KEY') or os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise RuntimeError(
                    "AI API not configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable."
                )

            logger.info(f"Attempting AI fallback for {pdf_path}")

            # For now, this is a placeholder implementation
            # In production, you would:
            # 1. Convert PDF pages to images (using pdf2image)
            # 2. Send images to Claude API or GPT-4 Vision with structured prompt
            # 3. Parse JSON response into transaction list
            # 4. Validate and return

            # Placeholder prompt structure:
            prompt = f"""
            Extract all bank transactions from this statement image.
            Bank name: {bank_name or 'Unknown'}

            Return JSON in this exact format:
            {{
                "bank_name": "...",
                "account_number": "...",
                "statement_period": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}},
                "transactions": [
                    {{
                        "date": "YYYY-MM-DD",
                        "description": "...",
                        "debit": null or amount,
                        "credit": null or amount,
                        "balance": amount
                    }}
                ]
            }}
            """

            # For now, raise error indicating this needs implementation
            raise RuntimeError(
                "AI fallback requires additional setup. "
                "Install 'anthropic' or 'openai' package and configure API key. "
                "See documentation for setup instructions."
            )

            # Example implementation structure (commented out):
            # import anthropic
            # client = anthropic.Anthropic(api_key=api_key)
            #
            # # Convert PDF to images
            # from pdf2image import convert_from_path
            # images = convert_from_path(pdf_path)
            #
            # # Send to Claude API
            # response = client.messages.create(
            #     model="claude-3-opus-20240229",
            #     max_tokens=4096,
            #     messages=[{
            #         "role": "user",
            #         "content": [
            #             {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64_image}},
            #             {"type": "text", "text": prompt}
            #         ]
            #     }]
            # )
            #
            # # Parse response
            # result = json.loads(response.content[0].text)
            # transactions = parse_ai_response(result)
            # return transactions, 0.95

        except Exception as error:
            logger.error("AI bank statement extraction failed")
            raise RuntimeError('AI extraction failed') from error

    @staticmethod
    def parse_statement(statement_id: int) -> Dict:
        """
        Main parsing pipeline for a bank statement.

        Args:
            statement_id: ID of BankStatement to parse

        Returns:
            Dict containing parsed data

        Raises:
            ValueError: If statement not found or parsing fails
            RuntimeError: If PDF processing fails
        """
        # Load statement from DB
        statement = db.session.get(BankStatement, statement_id)
        if not statement:
            raise ValueError(f"Statement not found: {statement_id}")

        stale_before = datetime.utcnow() - timedelta(
            minutes=PARSING_LEASE_MINUTES
        )
        lease_started_at = datetime.utcnow()
        claimed = (
            BankStatement.query.filter(
                BankStatement.id == statement_id,
                or_(
                    BankStatement.status.in_(['uploaded', 'failed']),
                    and_(
                        BankStatement.status == 'parsing',
                        or_(
                            BankStatement.parsing_started_at.is_(None),
                            BankStatement.parsing_started_at <= stale_before,
                        ),
                    ),
                ),
            )
            .update(
                {
                    'status': 'parsing',
                    'parsing_started_at': lease_started_at,
                    'error_message': None,
                },
                synchronize_session=False,
            )
        )
        if claimed != 1:
            db.session.rollback()
            raise ValueError(
                'Statement is already being parsed or cannot be parsed'
            )
        db.session.commit()
        statement = db.session.get(BankStatement, statement_id)

        try:
            logger.info(f"Starting parsing for statement {statement_id}")

            # Extract text
            text = PDFParserService.extract_text(statement.pdf_file_path)

            # Detect bank name
            bank_name = PDFParserService.detect_bank_name(text)
            logger.info(f"Detected bank: {bank_name}")

            # Try template-based extraction first (fast path)
            template = PDFParserService.find_template(bank_name)
            transactions = None
            used_template_id = None

            if template:
                try:
                    transactions, confidence = PDFParserService.extract_with_template(
                        statement.pdf_file_path, template
                    )
                    used_template_id = template.id
                    logger.info(f"Template extraction successful with confidence {confidence:.2f}")

                    # Mark template success
                    template.mark_success()
                    db.session.commit()

                except Exception:
                    logger.warning(
                        "Template extraction failed; using standard parser"
                    )
                    transactions = None

            # Fall back to pdfplumber if no template or template failed
            if not transactions:
                try:
                    transactions, confidence = PDFParserService.extract_with_pdfplumber(
                        statement.pdf_file_path
                    )
                    logger.info(f"PDFPlumber extraction successful with confidence {confidence:.2f}")

                    # If pdfplumber confidence is low, try AI as final fallback
                    if confidence < 0.6:
                        logger.info(f"PDFPlumber confidence {confidence:.2f} is low, trying AI fallback")
                        try:
                            ai_transactions, ai_confidence = PDFParserService.fallback_to_ai(
                                statement.pdf_file_path, bank_name
                            )
                            if ai_confidence > confidence:
                                logger.info(f"AI extraction better: {ai_confidence:.2f} > {confidence:.2f}")
                                transactions = ai_transactions
                                confidence = ai_confidence
                        except Exception:
                            logger.warning(
                                "AI fallback failed; using standard parser results"
                            )
                            # Keep pdfplumber results even if AI fails

                except Exception as extraction_error:
                    logger.error("Standard bank statement extraction failed")

                    # An empty table scan is a deterministic validation
                    # failure, not an infrastructure failure. Keep the
                    # actionable domain error instead of obscuring it behind
                    # an optional AI-provider configuration error.
                    if str(extraction_error) == "No tables found in PDF":
                        raise ValueError(
                            "No transaction table found in PDF"
                        ) from extraction_error

                    # Try AI as last resort
                    logger.info("Attempting AI fallback as last resort")
                    try:
                        transactions, confidence = PDFParserService.fallback_to_ai(
                            statement.pdf_file_path, bank_name
                        )
                        logger.info(f"AI extraction successful with confidence {confidence:.2f}")
                    except Exception as ai_error:
                        logger.error("All bank statement extraction methods failed")
                        raise ValueError(
                            "All extraction methods failed"
                        ) from ai_error

            if not transactions:
                raise ValueError("No valid transactions found in PDF")

            # Validate transactions
            is_valid, validation_errors = PDFParserService.validate_transactions(transactions)

            # Extract statement period from transactions
            transaction_dates = [txn['date'] for txn in transactions if txn.get('date')]
            period_start = statement.statement_period_start
            period_end = statement.statement_period_end
            if transaction_dates:
                period_start = min(transaction_dates)
                period_end = max(transaction_dates)

                # Check for duplicate statement
                from app.services.bank_statement_service import BankStatementService
                duplicate_statement = (
                    BankStatementService.find_duplicate_statement(
                        statement.bank_account_id,
                        period_start,
                        period_end,
                        exclude_statement_id=statement.id,
                    )
                )
            else:
                duplicate_statement = None

            # Convert Decimal and date to serializable formats for JSON storage
            serializable_transactions = []
            for txn in transactions:
                serializable_transactions.append({
                    'date': txn['date'].isoformat(),
                    'description': txn['description'],
                    'amount': str(txn['amount']),
                    'transaction_type': txn['transaction_type'],
                    'balance': (
                        str(txn['balance'])
                        if txn.get('balance') is not None
                        else None
                    )
                })

            # Prepare parsed data
            parsed_data = {
                'bank_name': bank_name,
                'transactions': serializable_transactions,
                'is_valid': is_valid,
                'validation_errors': validation_errors,
                'parsed_count': len(transactions),
                'used_template_id': used_template_id,
                'duplicate_statement_id': (
                    duplicate_statement.id if duplicate_statement else None
                ),
            }

            # The exact lease timestamp is the ownership token. A worker whose
            # stale lease was reclaimed must never overwrite the new worker's
            # review result.
            review_values = {
                'statement_period_start': period_start,
                'statement_period_end': period_end,
                'parsed_data': parsed_data,
                'status': 'review',
                'error_message': None,
                'parsing_started_at': None,
            }
            if used_template_id:
                review_values['parsing_template_id'] = used_template_id
            completed = (
                BankStatement.query.filter(
                    BankStatement.id == statement_id,
                    BankStatement.status == 'parsing',
                    BankStatement.parsing_started_at == lease_started_at,
                )
                .update(review_values, synchronize_session=False)
            )
            if completed != 1:
                db.session.rollback()
                raise ValueError('Statement parsing lease was lost')
            db.session.commit()

            logger.info(f"Successfully parsed statement {statement_id}")

            # Return with original Decimal/date objects for immediate use
            return {
                'bank_name': bank_name,
                'transactions': transactions,
                'is_valid': is_valid,
                'validation_errors': validation_errors,
                'parsed_count': len(transactions)
            }

        except Exception:
            # Only the current lease owner may publish a failure. If another
            # worker reclaimed this lease, preserve that worker's state.
            db.session.rollback()
            failed = (
                BankStatement.query.filter(
                    BankStatement.id == statement_id,
                    BankStatement.status == 'parsing',
                    BankStatement.parsing_started_at == lease_started_at,
                )
                .update(
                    {
                        'status': 'failed',
                        'error_message': 'Statement parsing failed',
                        'parsing_started_at': None,
                    },
                    synchronize_session=False,
                )
            )
            if failed:
                db.session.commit()
            else:
                db.session.rollback()

            logger.error("Failed to parse statement %s", statement_id)
            raise

    @staticmethod
    def get_validation_warnings(transactions: List[Dict]) -> List[Dict]:
        """
        Generate validation warnings for parsed transaction data.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            List of warning dictionaries with type, message, and severity
        """
        warnings = []

        if not transactions:
            return warnings

        # Check for missing critical fields
        for i, txn in enumerate(transactions):
            # Missing date
            if not txn.get('transaction_date'):
                warnings.append({
                    'type': 'missing_date',
                    'message': f'Transaction at row {i + 1} is missing date',
                    'severity': 'error'
                })

            # Missing amount
            if not txn.get('amount'):
                warnings.append({
                    'type': 'missing_amount',
                    'message': f'Transaction at row {i + 1} is missing amount',
                    'severity': 'error'
                })

            # Low confidence category
            confidence = txn.get('category_confidence', 0)
            if confidence < 0.6:
                warnings.append({
                    'type': 'low_confidence_category',
                    'message': f'Transaction at row {i + 1} has low categorization confidence ({confidence:.2f})',
                    'severity': 'warning'
                })

        # Check balance consistency
        for i in range(1, len(transactions)):
            prev_txn = transactions[i - 1]
            curr_txn = transactions[i]

            # Skip if either doesn't have balance
            prev_balance_str = prev_txn.get('running_balance')
            curr_balance_str = curr_txn.get('running_balance')

            if not prev_balance_str or not curr_balance_str:
                continue

            try:
                prev_balance = Decimal(str(prev_balance_str))
                curr_balance = Decimal(str(curr_balance_str))
                curr_amount = Decimal(str(curr_txn.get('amount', '0')))

                # Calculate expected balance
                expected_balance = prev_balance
                if curr_txn.get('transaction_type') == 'credit':
                    expected_balance += curr_amount
                else:  # debit
                    expected_balance -= curr_amount

                # Check for mismatch (allow small rounding errors)
                diff = abs(expected_balance - curr_balance)
                if diff > Decimal('0.01'):
                    warnings.append({
                        'type': 'balance_mismatch',
                        'message': f'Balance mismatch at row {i + 1}: expected {expected_balance}, got {curr_balance}',
                        'severity': 'warning'
                    })

            except (InvalidOperation, ValueError):
                # If we can't parse the numbers, skip this check
                logger.warning("Skipped an invalid balance consistency row")
                continue

        return warnings
