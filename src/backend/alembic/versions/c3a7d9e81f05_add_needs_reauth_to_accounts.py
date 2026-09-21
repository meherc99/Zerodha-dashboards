"""add needs_reauth to accounts

Revision ID: c3a7d9e81f05
Revises: b15a7e4c2d90
Create Date: 2026-08-05 00:00:00.000000

"""
from typing import Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3a7d9e81f05'
down_revision: Union[str, None] = 'b15a7e4c2d90'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'accounts',
        sa.Column(
            'needs_reauth',
            sa.Boolean(),
            nullable=False,
            server_default='false',
        ),
    )


def downgrade() -> None:
    op.drop_column('accounts', 'needs_reauth')
