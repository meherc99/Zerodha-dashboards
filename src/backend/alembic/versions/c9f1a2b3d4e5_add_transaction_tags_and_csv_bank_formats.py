"""Add transaction tags and CSV bank formats.

Revision ID: c9f1a2b3d4e5
Revises: 855036219916
"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9f1a2b3d4e5'
down_revision: Union[str, None] = '855036219916'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Trade Republic "Transaction report" CSV format. Kept as a frozen snapshot so
# this migration stays reproducible even as the app registry evolves.
TRADE_REPUBLIC_CSV_CONFIG = {
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

SYSTEM_BANK_FORMATS = (
    ('Trade Republic', 'csv', TRADE_REPUBLIC_CSV_CONFIG),
)


def _seed_bank_formats(connection) -> None:
    templates = sa.table(
        'parsing_templates',
        sa.column('bank_name', sa.String(100)),
        sa.column('template_version', sa.Integer()),
        sa.column('file_format', sa.String(10)),
        sa.column('is_system', sa.Boolean()),
        sa.column('extraction_config', sa.JSON()),
        sa.column('success_count', sa.Integer()),
        sa.column('failure_count', sa.Integer()),
        sa.column('is_active', sa.Boolean()),
        sa.column('created_at', sa.DateTime()),
        sa.column('updated_at', sa.DateTime()),
    )
    now = datetime.utcnow()
    for bank_name, file_format, config in SYSTEM_BANK_FORMATS:
        existing = connection.execute(
            sa.select(templates.c.bank_name).where(
                sa.and_(
                    templates.c.bank_name == bank_name,
                    templates.c.is_system.is_(True),
                )
            )
        ).fetchone()
        if existing:
            connection.execute(
                templates.update()
                .where(
                    sa.and_(
                        templates.c.bank_name == bank_name,
                        templates.c.is_system.is_(True),
                    )
                )
                .values(
                    file_format=file_format,
                    extraction_config=config,
                    is_active=True,
                    updated_at=now,
                )
            )
        else:
            connection.execute(
                templates.insert().values(
                    bank_name=bank_name,
                    template_version=1,
                    file_format=file_format,
                    is_system=True,
                    extraction_config=config,
                    success_count=0,
                    failure_count=0,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )


def upgrade() -> None:
    op.add_column(
        'transactions',
        sa.Column('tags', sa.JSON(), nullable=True),
    )
    with op.batch_alter_table('parsing_templates') as batch_op:
        batch_op.add_column(
            sa.Column(
                'file_format',
                sa.String(10),
                nullable=False,
                server_default='pdf',
            )
        )
        batch_op.add_column(
            sa.Column(
                'is_system',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
    op.create_index(
        'ix_parsing_templates_is_system',
        'parsing_templates',
        ['is_system'],
    )

    _seed_bank_formats(op.get_bind())


def downgrade() -> None:
    op.drop_index(
        'ix_parsing_templates_is_system',
        table_name='parsing_templates',
    )
    with op.batch_alter_table('parsing_templates') as batch_op:
        batch_op.drop_column('is_system')
        batch_op.drop_column('file_format')
    op.drop_column('transactions', 'tags')
