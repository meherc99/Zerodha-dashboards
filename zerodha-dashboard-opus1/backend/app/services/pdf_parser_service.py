"""
PDF Parser Service for extracting transaction data from bank statement PDFs.
"""
import re
import logging
import os
import json
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Tuple, Optional
import pdfplumber
from app.database import db
from app.models.bank_statement import BankStatement
from app.models.parsing_template import ParsingTemplate

logger = logging.getLogger(__name__)


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
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(page_text)

            return '\n'.join(text_content)

        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {str(e)}")
            raise RuntimeError(f"Failed to extract text from PDF: {str(e)}")

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
                for page in pdf.pages:
                    tables = page.extract_tables()
                    if tables:
                        all_tables.extend(tables)

            return all_tables

        except Exception as e:
            logger.error(f"Error extracting tables from PDF {pdf_path}: {str(e)}")
            raise RuntimeError(f"Failed to extract tables from PDF: {str(e)}")

    @staticmethod
    def identify_transaction_table(tables: List[List[List[str]]]) -> Optional[List[List[str]]]:
        """
        Identify the transaction table from list of extracted tables.

        Looks for a table with:
        - 4-6 columns
        - A date column (contains date patterns)
        - Amount/balance columns

        Args:
            tables: List of tables extracted from PDF

        Returns:
            Transaction table or None if not found
        """
        for table in tables:
            if not table or len(table) < 2:
                continue

            # Check if table has 4-6 columns
            num_cols = len(table[0]) if table[0] else 0
            if num_cols < 4 or num_cols > 6:
                continue

            # Check if first column looks like dates
            # Look at first few data rows (skip header)
            has_date_column = False
            for row in table[1:4]:  # Check first 3 data rows
                if not row or not row[0]:
                    continue

                # Check if first cell matches date pattern
                cell = str(row[0]).strip()
                for pattern in PDFParserService.DATE_PATTERNS:
                    if re.match(pattern, cell):
                        has_date_column = True
                        break

                if has_date_column:
                    break

            if has_date_column:
                return table

        return None

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

        # Build header map (case-insensitive)
        header_map = {h.lower().strip(): i for i, h in enumerate(headers) if h}

        # Extract description (usually second column)
        description = str(row[1]).strip() if len(row) > 1 else ''
        if not description:
            return None

        # Find debit, credit, and balance columns
        debit_idx = None
        credit_idx = None
        balance_idx = None

        for header, idx in header_map.items():
            if 'debit' in header or 'withdrawal' in header or 'dr' == header:
                debit_idx = idx
            elif 'credit' in header or 'deposit' in header or 'cr' == header:
                credit_idx = idx
            elif 'balance' in header or 'closing' in header:
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
        """
        Find active parsing template for a bank.

        Args:
            bank_name: Bank name (normalized)

        Returns:
            Most recently used active ParsingTemplate or None
        """
        if not bank_name or bank_name == 'Unknown':
            return None

        template = ParsingTemplate.query.filter_by(
            bank_name=bank_name,
            is_active=True
        ).order_by(
            ParsingTemplate.last_used_at.desc().nullslast(),
            ParsingTemplate.success_count.desc()
        ).first()

        if template:
            logger.info(f"Found template {template.id} for {bank_name} "
                       f"(v{template.template_version}, {template.success_count} successes)")

        return template

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

                # Find transaction table using template hints
                transaction_table = PDFParserService.identify_transaction_table(tables)
                if not transaction_table:
                    raise RuntimeError("No transaction table found")

                # Parse transactions using template column mapping
                headers = transaction_table[0]
                transactions = []
                column_map = config.get('columns', {})

                for row in transaction_table[1:]:
                    txn = PDFParserService.parse_transaction_row(row, headers)
                    if txn:
                        transactions.append(txn)

                if not transactions:
                    raise RuntimeError("No transactions extracted using template")

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

        except Exception as e:
            logger.warning(f"Template extraction failed: {str(e)}")
            # Mark template failure
            template.mark_failure()
            db.session.commit()
            raise RuntimeError(f"Template extraction failed: {str(e)}")

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

            # Find transaction table
            transaction_table = PDFParserService.identify_transaction_table(tables)
            if not transaction_table:
                raise RuntimeError("No transaction table found")

            # Parse transactions
            headers = transaction_table[0]
            transactions = []

            for row in transaction_table[1:]:
                txn = PDFParserService.parse_transaction_row(row, headers)
                if txn:
                    transactions.append(txn)

            if not transactions:
                raise RuntimeError("No valid transactions extracted")

            # Validate
            is_valid, errors = PDFParserService.validate_transactions(transactions)

            # Calculate confidence
            confidence = 0.8 if is_valid else 0.5

            logger.info(f"PDFPlumber extraction: {len(transactions)} transactions, "
                       f"confidence={confidence:.2f}")

            return transactions, confidence

        except Exception as e:
            logger.error(f"PDFPlumber extraction failed: {str(e)}")
            raise

    @staticmethod
    def fallback_to_ai(pdf_path: str, bank_name: str = None) -> Tuple[List[Dict], float]:
        """
        Use AI (Claude API or GPT-4 Vision) to extract transactions from PDF.

        This is the fallback when pdfplumber fails or has low confidence.
        Converts PDF to images and sends to vision API with structured prompt.

        Args:
            pdf_path: Path to PDF file
            bank_name: Optional bank name hint for AI

        Returns:
            Tuple of (transactions list, confidence score)

        Raises:
            RuntimeError: If AI extraction fails or API not configured
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

        except Exception as e:
            logger.error(f"AI fallback failed: {str(e)}")
            raise RuntimeError(f"AI extraction failed: {str(e)}")

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
        statement = BankStatement.query.get(statement_id)
        if not statement:
            raise ValueError(f"Statement not found: {statement_id}")

        try:
            # Update status to parsing
            statement.status = 'parsing'
            db.session.commit()

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

                except Exception as template_error:
                    logger.warning(f"Template extraction failed, falling back: {template_error}")
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
                        except Exception as ai_error:
                            logger.warning(f"AI fallback failed, using pdfplumber results: {ai_error}")
                            # Keep pdfplumber results even if AI fails

                except Exception as e:
                    logger.error(f"PDFPlumber extraction failed: {str(e)}")

                    # Try AI as last resort
                    logger.info("Attempting AI fallback as last resort")
                    try:
                        transactions, confidence = PDFParserService.fallback_to_ai(
                            statement.pdf_file_path, bank_name
                        )
                        logger.info(f"AI extraction successful with confidence {confidence:.2f}")
                    except Exception as ai_error:
                        logger.error(f"AI fallback also failed: {ai_error}")
                        raise ValueError(f"All extraction methods failed. PDFPlumber: {str(e)}, AI: {str(ai_error)}")

            if not transactions:
                raise ValueError("No valid transactions found in PDF")

            # Validate transactions
            is_valid, validation_errors = PDFParserService.validate_transactions(transactions)

            # Convert Decimal and date to serializable formats for JSON storage
            serializable_transactions = []
            for txn in transactions:
                serializable_transactions.append({
                    'date': txn['date'].isoformat(),
                    'description': txn['description'],
                    'amount': str(txn['amount']),
                    'transaction_type': txn['transaction_type'],
                    'balance': str(txn['balance']) if txn.get('balance') else None
                })

            # Prepare parsed data
            parsed_data = {
                'bank_name': bank_name,
                'transactions': serializable_transactions,
                'is_valid': is_valid,
                'validation_errors': validation_errors,
                'parsed_count': len(transactions),
                'used_template_id': used_template_id
            }

            # Update statement with parsed data and template reference
            statement.parsed_data = parsed_data
            if used_template_id:
                statement.parsing_template_id = used_template_id
            statement.status = 'review'
            statement.error_message = None
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

        except Exception as e:
            # Update statement status to failed
            statement.status = 'failed'
            statement.error_message = str(e)
            db.session.commit()

            logger.error(f"Failed to parse statement {statement_id}: {str(e)}")
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
            if not txn.get('date'):
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
            prev_balance_str = prev_txn.get('balance')
            curr_balance_str = curr_txn.get('balance')

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

            except (InvalidOperation, ValueError) as e:
                # If we can't parse the numbers, skip this check
                logger.warning(f"Error checking balance consistency: {str(e)}")
                continue

        return warnings
