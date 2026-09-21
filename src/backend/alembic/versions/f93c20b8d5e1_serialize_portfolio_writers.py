"""Serialize concurrent portfolio snapshot writers.

Revision ID: f93c20b8d5e1
Revises: e82b91a7c4d6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f93c20b8d5e1'
down_revision: Union[str, None] = 'e82b91a7c4d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'accounts',
        sa.Column(
            'portfolio_version',
            sa.Integer(),
            nullable=False,
            server_default='0',
        ),
    )


def downgrade() -> None:
    op.drop_column('accounts', 'portfolio_version')
