"""Add parsing templates.

Revision ID: b1f00545dd90
Revises: 7c612302520e
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1f00545dd90'
down_revision: Union[str, None] = '7c612302520e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'parsing_templates',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('bank_name', sa.String(100), nullable=False),
        sa.Column('template_version', sa.Integer(), nullable=False),
        sa.Column('extraction_config', sa.JSON(), nullable=False),
        sa.Column('success_count', sa.Integer(), nullable=False),
        sa.Column('failure_count', sa.Integer(), nullable=False),
        sa.Column('last_used_at', sa.DateTime()),
        sa.Column('created_from_statement_id', sa.Integer()),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime()),
        sa.ForeignKeyConstraint(
            ['created_from_statement_id'],
            ['bank_statements.id'],
            name='fk_parsing_templates_created_statement',
        ),
    )
    op.create_index(
        'ix_parsing_templates_bank_name',
        'parsing_templates',
        ['bank_name'],
    )
    op.create_index(
        'ix_parsing_templates_is_active',
        'parsing_templates',
        ['is_active'],
    )
    op.create_index(
        'idx_parsing_templates_bank_active',
        'parsing_templates',
        ['bank_name', 'is_active'],
    )

    with op.batch_alter_table('bank_statements') as batch_op:
        batch_op.add_column(
            sa.Column('parsing_template_id', sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_bank_statements_parsing_template',
            'parsing_templates',
            ['parsing_template_id'],
            ['id'],
        )
    op.create_index(
        'ix_bank_statements_parsing_template_id',
        'bank_statements',
        ['parsing_template_id'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_bank_statements_parsing_template_id',
        table_name='bank_statements',
    )
    with op.batch_alter_table('bank_statements') as batch_op:
        batch_op.drop_constraint(
            'fk_bank_statements_parsing_template',
            type_='foreignkey',
        )
        batch_op.drop_column('parsing_template_id')
    op.drop_table('parsing_templates')
