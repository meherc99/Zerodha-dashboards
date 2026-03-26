"""
PDF Parser Service for extracting transaction data from bank statement PDFs.
"""
import re
import logging
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Tuple, Optional
import pdfplumber
from app.database import db
from app.models.bank_statement import BankStatement

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

            # Extract tables
            tables = PDFParserService.extract_tables_from_pdf(statement.pdf_file_path)
            logger.info(f"Extracted {len(tables)} tables from PDF")

            # Find transaction table
            transaction_table = PDFParserService.identify_transaction_table(tables)
            if not transaction_table:
                raise ValueError("No transaction table found in PDF")

            logger.info(f"Found transaction table with {len(transaction_table)} rows")

            # Parse transactions
            headers = transaction_table[0]
            transactions = []

            for row in transaction_table[1:]:
                txn = PDFParserService.parse_transaction_row(row, headers)
                if txn:
                    transactions.append(txn)

            logger.info(f"Parsed {len(transactions)} transactions")

            if not transactions:
                raise ValueError("No valid transactions found in table")

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
                'parsed_count': len(transactions)
            }

            # Update statement with parsed data
            statement.parsed_data = parsed_data
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
