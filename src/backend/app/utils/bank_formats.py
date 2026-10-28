"""
Predefined per-bank statement upload formats.

Each entry describes how a specific bank's export file is laid out so future
uploads for that bank are parsed the same way. Formats are stored as system
``ParsingTemplate`` rows (``is_system=True``) which are safe to reuse across
all users, unlike user-derived layouts.

CSV ``extraction_config`` schema::

    {
      "parsing_method": "csv",
      "delimiter": ",",
      "encoding": "utf-8",
      "columns": {            # semantic field -> source column header
        "date": "date",
        "description": "description",
        "amount": "amount",
        "currency": "currency"
      },
      "date_format": "%Y-%m-%d",
      "amount_sign_convention": "signed",  # negative=debit, positive=credit
      "tag_fields": ["category", "type", "name", "description"],
      "detection": {"required_headers": [...]}  # all must be present to match
    }
"""
from datetime import datetime

from app.database import db
from app.models.parsing_template import ParsingTemplate


# Trade Republic "Transaction report" CSV export. The ``amount`` column is
# signed (money out is negative), there is no running balance, and the
# category/type/name/description columns drive analytics tags.
TRADE_REPUBLIC_CSV = {
    'parsing_method': 'csv',
    'delimiter': ',',
    'encoding': 'utf-8',
    'columns': {
        'date': 'date',
        'description': 'description',
        'amount': 'amount',
        'currency': 'currency',
        'category': 'category',
        'type': 'type',
        'name': 'name',
    },
    'date_format': '%Y-%m-%d',
    'amount_sign_convention': 'signed',
    'tag_fields': ['category', 'type', 'name', 'description'],
    'detection': {
        'required_headers': [
            'datetime',
            'date',
            'account_type',
            'category',
            'type',
            'asset_class',
            'name',
            'amount',
            'currency',
            'description',
            'transaction_id',
        ],
    },
}


# Registry of predefined bank formats. Add new banks here.
BANK_STATEMENT_FORMATS = [
    {
        'bank_name': 'Trade Republic',
        'file_format': 'csv',
        'extraction_config': TRADE_REPUBLIC_CSV,
    },
]


def seed_bank_formats():
    """Create or refresh predefined system bank formats.

    Idempotent: existing system rows for a bank name are updated in place so
    format fixes ship without creating duplicates.

    Returns:
        int: Number of new formats created.
    """
    created_count = 0
    now = datetime.utcnow()

    for spec in BANK_STATEMENT_FORMATS:
        existing = ParsingTemplate.query.filter_by(
            bank_name=spec['bank_name'],
            is_system=True,
        ).first()

        if existing:
            existing.file_format = spec['file_format']
            existing.extraction_config = spec['extraction_config']
            existing.is_active = True
            existing.updated_at = now
        else:
            db.session.add(
                ParsingTemplate(
                    bank_name=spec['bank_name'],
                    template_version=1,
                    file_format=spec['file_format'],
                    extraction_config=spec['extraction_config'],
                    is_system=True,
                    is_active=True,
                    success_count=0,
                    failure_count=0,
                    created_at=now,
                )
            )
            created_count += 1

    db.session.commit()
    return created_count
