"""Preserve manually entered bank opening balances.

Revision ID: b15a7e4c2d90
Revises: a04f31c9e762
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b15a7e4c2d90'
down_revision: Union[str, None] = 'a04f31c9e762'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'bank_accounts',
        sa.Column(
            'opening_balance',
            sa.Numeric(15, 2),
            nullable=True,
            server_default='0',
        ),
    )
    op.execute(
        """
        UPDATE bank_accounts
        SET opening_balance = COALESCE(current_balance, 0)
        """
    )
    with op.batch_alter_table('bank_accounts') as batch_op:
        batch_op.alter_column(
            'opening_balance',
            existing_type=sa.Numeric(15, 2),
            nullable=False,
            server_default='0',
        )


def downgrade() -> None:
    with op.batch_alter_table('bank_accounts') as batch_op:
        batch_op.drop_column('opening_balance')
