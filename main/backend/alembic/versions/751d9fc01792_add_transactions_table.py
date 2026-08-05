"""Add transactions.

Revision ID: 751d9fc01792
Revises: a6640608403a
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '751d9fc01792'
down_revision: Union[str, None] = 'a6640608403a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('statement_id', sa.Integer()),
        sa.Column('bank_account_id', sa.Integer(), nullable=False),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('merchant_name', sa.String(200)),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('transaction_type', sa.String(10), nullable=False),
        sa.Column('running_balance', sa.Numeric(15, 2)),
        sa.Column('category_id', sa.Integer()),
        sa.Column('category_confidence', sa.Float()),
        sa.Column('verified', sa.Boolean(), nullable=False),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
        sa.ForeignKeyConstraint(
            ['bank_account_id'],
            ['bank_accounts.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['category_id'],
            ['transaction_categories.id'],
        ),
    )
    op.create_index(
        'ix_transactions_statement_id',
        'transactions',
        ['statement_id'],
    )
    op.create_index(
        'ix_transactions_bank_account_id',
        'transactions',
        ['bank_account_id'],
    )
    op.create_index(
        'ix_transactions_transaction_date',
        'transactions',
        ['transaction_date'],
    )
    op.create_index(
        'ix_transactions_category_id',
        'transactions',
        ['category_id'],
    )
    op.create_index(
        'idx_transactions_bank_account_date',
        'transactions',
        ['bank_account_id', 'transaction_date'],
    )
    op.create_index(
        'idx_transactions_filters',
        'transactions',
        ['bank_account_id', 'transaction_date', 'transaction_type', 'category_id'],
    )


def downgrade() -> None:
    op.drop_table('transactions')
