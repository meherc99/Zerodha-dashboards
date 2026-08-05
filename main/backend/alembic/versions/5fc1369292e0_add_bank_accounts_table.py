"""Add bank accounts.

Revision ID: 5fc1369292e0
Revises: 4b86235fc91f
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5fc1369292e0'
down_revision: Union[str, None] = '4b86235fc91f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bank_accounts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('bank_name', sa.String(100), nullable=False),
        sa.Column('account_number', sa.String(50), nullable=False),
        sa.Column('account_type', sa.String(20)),
        sa.Column('current_balance', sa.Numeric(15, 2)),
        sa.Column('currency', sa.String(3)),
        sa.Column('last_statement_date', sa.Date()),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'], ondelete='CASCADE'
        ),
    )
    op.create_index(
        'ix_bank_accounts_user_id',
        'bank_accounts',
        ['user_id'],
    )


def downgrade() -> None:
    op.drop_table('bank_accounts')
