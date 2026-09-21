"""Make Kite API credentials optional on accounts.

Accounts can now be created with only a name and populated with manually
imported holdings (FD, stocks) without requiring Zerodha Kite Connect
credentials. Credentials can be added later via a PUT request.

Revision ID: a04d1b7c8e92
Revises: f93c20b8d5e1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a04d1b7c8e92'
down_revision: Union[str, None] = 'c3a7d9e81f05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('accounts') as batch_op:
        batch_op.alter_column('api_key_encrypted', existing_type=sa.Text(), nullable=True)
        batch_op.alter_column('api_secret_encrypted', existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    # Note: rows with NULL api_key_encrypted / api_secret_encrypted will
    # violate the NOT NULL constraint after downgrade if any exist.
    with op.batch_alter_table('accounts') as batch_op:
        batch_op.alter_column('api_key_encrypted', existing_type=sa.Text(), nullable=False)
        batch_op.alter_column('api_secret_encrypted', existing_type=sa.Text(), nullable=False)
