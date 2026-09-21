"""Add statement idempotency, token revocation, and system categories.

Revision ID: a04f31c9e762
Revises: f93c20b8d5e1
"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a04f31c9e762'
down_revision: Union[str, None] = 'f93c20b8d5e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_CATEGORIES = (
    ('Income', '💰', '#10b981', ['salary', 'freelance', 'interest', 'dividend']),
    ('Housing', '🏠', '#3b82f6', ['rent', 'mortgage', 'maintenance', 'property tax']),
    ('Utilities', '⚡', '#f59e0b', ['electricity', 'water', 'internet', 'phone', 'mobile']),
    ('Groceries', '🛒', '#10b981', ['grocery', 'supermarket', 'bigbasket', 'grofers', 'blinkit']),
    ('Dining', '🍽️', '#ef4444', ['restaurant', 'swiggy', 'zomato', 'food delivery', 'cafe']),
    ('Transportation', '🚗', '#8b5cf6', ['fuel', 'petrol', 'uber', 'ola', 'metro', 'bus']),
    ('Shopping', '🛍️', '#ec4899', ['amazon', 'flipkart', 'myntra', 'clothing', 'electronics']),
    ('Healthcare', '🏥', '#ef4444', ['doctor', 'hospital', 'pharmacy', 'medicine', 'insurance']),
    ('Entertainment', '🎬', '#a855f7', ['netflix', 'prime', 'movie', 'cinema', 'spotify']),
    ('Education', '📚', '#3b82f6', ['course', 'book', 'tuition', 'school', 'college']),
    ('Insurance', '🛡️', '#6366f1', ['insurance', 'premium', 'policy']),
    ('Investments', '📈', '#059669', ['mutual fund', 'sip', 'stock', 'investment']),
    ('Transfers', '↔️', '#6b7280', ['transfer', 'neft', 'imps', 'upi']),
    ('Uncategorized', '❓', '#9ca3af', []),
)


def _seed_default_categories(connection) -> None:
    categories = sa.table(
        'transaction_categories',
        sa.column('name', sa.String(50)),
        sa.column('icon', sa.String(10)),
        sa.column('color', sa.String(7)),
        sa.column('keywords', sa.JSON()),
        sa.column('is_system', sa.Boolean()),
        sa.column('parent_category_id', sa.Integer()),
        sa.column('created_at', sa.DateTime()),
    )
    existing_names = {
        row[0]
        for row in connection.execute(sa.select(categories.c.name)).fetchall()
    }
    now = datetime.utcnow()
    for name, icon, color, keywords in DEFAULT_CATEGORIES:
        if name in existing_names:
            # Canonical names are public application taxonomy. Older versions
            # could leave a row marked as user-created, so normalize the full
            # safe display/matching definition instead of trusting legacy data.
            connection.execute(
                categories.update()
                .where(categories.c.name == name)
                .values(
                    icon=icon,
                    color=color,
                    keywords=keywords,
                    is_system=True,
                    parent_category_id=None,
                )
            )
        else:
            connection.execute(
                categories.insert().values(
                    name=name,
                    icon=icon,
                    color=color,
                    keywords=keywords,
                    is_system=True,
                    created_at=now,
                )
            )


def upgrade() -> None:
    op.add_column(
        'bank_statements',
        sa.Column('file_sha256', sa.String(64), nullable=True),
    )
    op.add_column(
        'bank_statements',
        sa.Column('parsing_started_at', sa.DateTime(), nullable=True),
    )
    with op.batch_alter_table('bank_statements') as batch_op:
        batch_op.create_unique_constraint(
            'uq_bank_statements_account_file_sha256',
            ['bank_account_id', 'file_sha256'],
        )

    op.create_table(
        'revoked_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('jti', sa.String(36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            ondelete='CASCADE',
        ),
        sa.UniqueConstraint('jti'),
    )
    op.create_index('ix_revoked_tokens_jti', 'revoked_tokens', ['jti'])
    op.create_index(
        'ix_revoked_tokens_user_id',
        'revoked_tokens',
        ['user_id'],
    )
    op.create_index(
        'ix_revoked_tokens_expires_at',
        'revoked_tokens',
        ['expires_at'],
    )
    op.create_table(
        'rate_limit_buckets',
        sa.Column('key_hash', sa.String(64), primary_key=True),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.Column('reset_time', sa.DateTime(), nullable=False),
    )
    op.create_index(
        'ix_rate_limit_buckets_reset_time',
        'rate_limit_buckets',
        ['reset_time'],
    )

    _seed_default_categories(op.get_bind())


def downgrade() -> None:
    op.drop_index(
        'ix_rate_limit_buckets_reset_time',
        table_name='rate_limit_buckets',
    )
    op.drop_table('rate_limit_buckets')
    op.drop_index('ix_revoked_tokens_expires_at', table_name='revoked_tokens')
    op.drop_index('ix_revoked_tokens_user_id', table_name='revoked_tokens')
    op.drop_index('ix_revoked_tokens_jti', table_name='revoked_tokens')
    op.drop_table('revoked_tokens')
    with op.batch_alter_table('bank_statements') as batch_op:
        batch_op.drop_constraint(
            'uq_bank_statements_account_file_sha256',
            type_='unique',
        )
        batch_op.drop_column('parsing_started_at')
        batch_op.drop_column('file_sha256')

    # System categories are intentionally retained because transactions may
    # reference them after this schema feature is downgraded.
