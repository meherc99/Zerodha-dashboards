"""Add bank statements.

Revision ID: 7c612302520e
Revises: 751d9fc01792
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7c612302520e'
down_revision: Union[str, None] = '751d9fc01792'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bank_statements',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('bank_account_id', sa.Integer(), nullable=False),
        sa.Column('statement_period_start', sa.Date(), nullable=False),
        sa.Column('statement_period_end', sa.Date(), nullable=False),
        sa.Column('pdf_file_path', sa.String(500), nullable=False),
        sa.Column('upload_date', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.Text()),
        sa.Column('parsed_data', sa.JSON()),
        sa.Column('created_at', sa.DateTime()),
        sa.ForeignKeyConstraint(
            ['bank_account_id'],
            ['bank_accounts.id'],
            ondelete='CASCADE',
        ),
    )
    op.create_index(
        'ix_bank_statements_bank_account_id',
        'bank_statements',
        ['bank_account_id'],
    )
    op.create_index(
        'ix_bank_statements_status',
        'bank_statements',
        ['status'],
    )
    with op.batch_alter_table('transactions') as batch_op:
        batch_op.create_foreign_key(
            'fk_transactions_statement_id_bank_statements',
            'bank_statements',
            ['statement_id'],
            ['id'],
            ondelete='CASCADE',
        )


def downgrade() -> None:
    with op.batch_alter_table('transactions') as batch_op:
        batch_op.drop_constraint(
            'fk_transactions_statement_id_bank_statements',
            type_='foreignkey',
        )
    op.drop_table('bank_statements')
