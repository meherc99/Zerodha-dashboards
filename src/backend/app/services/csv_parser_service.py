"""
CSV Parser Service for extracting transactions from bank CSV exports.

Unlike the PDF path, CSV exports come from a known bank format (a system
``ParsingTemplate`` with ``file_format='csv'``). The matching format is
detected from the header row, then each row is mapped to a transaction and
tagged for later analytics using the configured ``tag_fields``.
"""
import csv
import io
import logging
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

from app.models.parsing_template import ParsingTemplate

logger = logging.getLogger(__name__)

# CSV exports must stay within the same bound the approval workflow enforces.
MAX_CSV_ROWS = 5000
# Longer values (e.g. free-text descriptions) are skipped as tags so grouping
# stays useful for analytics.
MAX_TAG_LENGTH = 80


class CSVParserService:
    """Parse bank CSV exports using a predefined system format."""

    @staticmethod
    def read_header(file_path: str, encoding: str = 'utf-8') -> List[str]:
        """Return normalized (stripped, lowercased) header column names."""
        with open(file_path, 'r', encoding=encoding, newline='') as handle:
            reader = csv.reader(handle)
            for row in reader:
                return [str(cell).strip().lower() for cell in row]
        return []

    @staticmethod
    def detect_format(file_path: str) -> Optional[ParsingTemplate]:
        """Return the active system CSV format whose required headers match.

        Only predefined system formats are considered so private layouts are
        never shared between tenants.
        """
        try:
            header = set(CSVParserService.read_header(file_path))
        except (OSError, UnicodeDecodeError):
            logger.warning("Failed to read CSV header for format detection")
            return None
        if not header:
            return None

        templates = ParsingTemplate.query.filter_by(
            file_format='csv',
            is_system=True,
            is_active=True,
        ).all()

        for template in templates:
            config = template.extraction_config or {}
            required = config.get('detection', {}).get('required_headers', [])
            required_set = {str(name).strip().lower() for name in required}
            if required_set and required_set <= header:
                return template
        return None

    @staticmethod
    def _parse_date(value: str, date_format: str) -> Optional[date]:
        if not value:
            return None
        value = str(value).strip()
        try:
            return datetime.strptime(value, date_format).date()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_amount(value: str) -> Optional[Decimal]:
        if value is None:
            return None
        cleaned = re.sub(r'[^0-9.\-]', '', str(value).strip())
        if cleaned in ('', '-', '.', '-.'):
            return None
        try:
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def build_tags(record: Dict[str, str], tag_fields: List[str]) -> List[str]:
        """Build ``field:value`` analytics tags from configured columns."""
        tags: List[str] = []
        seen = set()
        for field in tag_fields:
            raw = record.get(field)
            if raw is None:
                continue
            value = re.sub(r'\s+', ' ', str(raw)).strip()
            if not value or len(value) > MAX_TAG_LENGTH:
                continue
            tag = f'{field}:{value}'
            key = tag.lower()
            if key in seen:
                continue
            seen.add(key)
            tags.append(tag)
        return tags

    @staticmethod
    def parse(file_path: str, template: ParsingTemplate) -> List[Dict]:
        """Parse a CSV file into transaction dicts using ``template``.

        Returns:
            List of dicts with ``date``, ``description``, ``amount``
            (positive Decimal), ``transaction_type`` ('debit'/'credit'),
            ``balance`` (None) and ``tags``.

        Raises:
            ValueError: If the file is malformed or exceeds row limits.
            RuntimeError: If the file cannot be read.
        """
        config = template.extraction_config or {}
        columns = config.get('columns', {})
        date_column = columns.get('date')
        description_column = columns.get('description')
        amount_column = columns.get('amount')
        if not (date_column and description_column and amount_column):
            raise ValueError('CSV format is missing required column mappings')

        date_format = config.get('date_format', '%Y-%m-%d')
        tag_fields = config.get('tag_fields', [])
        encoding = config.get('encoding', 'utf-8')
        delimiter = config.get('delimiter', ',')

        try:
            with open(file_path, 'r', encoding=encoding, newline='') as handle:
                content = handle.read()
        except UnicodeDecodeError as error:
            raise ValueError('CSV file is not valid UTF-8 text') from error
        except OSError as error:
            raise RuntimeError('Failed to read CSV file') from error

        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError('CSV file has no header row')

        # DictReader keys keep original casing; map from normalized names.
        field_lookup = {
            str(name).strip().lower(): name
            for name in reader.fieldnames
        }

        def source(row, semantic_field):
            column = columns.get(semantic_field)
            if not column:
                return None
            actual = field_lookup.get(str(column).strip().lower())
            return row.get(actual) if actual else None

        transactions: List[Dict] = []
        for row in reader:
            if len(transactions) >= MAX_CSV_ROWS:
                raise ValueError(
                    f'CSV exceeds the maximum of {MAX_CSV_ROWS} transactions'
                )

            txn_date = CSVParserService._parse_date(
                source(row, 'date'), date_format
            )
            if not txn_date:
                continue

            amount = CSVParserService._parse_amount(source(row, 'amount'))
            if amount is None or amount == 0:
                continue

            description = str(source(row, 'description') or '').strip()
            if not description:
                # Fall back to the instrument/counterparty name when present.
                description = str(source(row, 'name') or '').strip()
            if not description:
                description = 'Transaction'

            transaction_type = 'debit' if amount < 0 else 'credit'

            tag_record = {
                field: source(row, field) for field in tag_fields
            }
            tags = CSVParserService.build_tags(tag_record, tag_fields)

            transactions.append({
                'date': txn_date,
                'description': description[:500],
                'amount': abs(amount),
                'transaction_type': transaction_type,
                'balance': None,
                'tags': tags,
            })

        return transactions

    @staticmethod
    def parse_file(file_path: str) -> Tuple[str, List[Dict]]:
        """Detect the format and parse a CSV file.

        Returns:
            Tuple of (bank_name, transactions).

        Raises:
            ValueError: If no known bank format matches the file.
        """
        template = CSVParserService.detect_format(file_path)
        if not template:
            raise ValueError(
                'Unrecognized CSV format; no matching bank format found'
            )
        transactions = CSVParserService.parse(file_path, template)
        return template.bank_name, transactions
