"""Encrypt bank account numbers and remove learned global keywords.

Revision ID: e82b91a7c4d6
Revises: d71c4a9e2f30
"""
import os
from typing import Sequence, Union

from alembic import op
from cryptography.fernet import Fernet
import sqlalchemy as sa


revision: str = 'e82b91a7c4d6'
down_revision: Union[str, None] = 'd71c4a9e2f30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SAFE_SYSTEM_KEYWORDS = {
    'Income': ['salary', 'freelance', 'interest', 'dividend'],
    'Housing': ['rent', 'mortgage', 'maintenance', 'property tax'],
    'Utilities': ['electricity', 'water', 'internet', 'phone', 'mobile'],
    'Groceries': [
        'grocery',
        'supermarket',
        'bigbasket',
        'grofers',
        'blinkit',
    ],
    'Dining': ['restaurant', 'swiggy', 'zomato', 'food delivery', 'cafe'],
    'Transportation': ['fuel', 'petrol', 'uber', 'ola', 'metro', 'bus'],
    'Shopping': ['amazon', 'flipkart', 'myntra', 'clothing', 'electronics'],
    'Healthcare': ['doctor', 'hospital', 'pharmacy', 'medicine', 'insurance'],
    'Entertainment': ['netflix', 'prime', 'movie', 'cinema', 'spotify'],
    'Education': ['course', 'book', 'tuition', 'school', 'college'],
    'Insurance': ['insurance', 'premium', 'policy'],
    'Investments': ['mutual fund', 'sip', 'stock', 'investment'],
    'Transfers': ['transfer', 'neft', 'imps', 'upi'],
    'Uncategorized': [],
}


def _cipher_for_existing_rows():
    key = os.environ.get('ENCRYPTION_KEY')
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (TypeError, ValueError) as error:
        raise RuntimeError(
            'A valid ENCRYPTION_KEY is required to migrate existing bank '
            'account numbers'
        ) from error


def _replace_category_keywords(connection):
    """Remove previously learned private terms and restore public defaults."""
    categories = sa.table(
        'transaction_categories',
        sa.column('name', sa.String()),
        sa.column('keywords', sa.JSON()),
    )
    connection.execute(categories.update().values(keywords=[]))
    for name, keywords in SAFE_SYSTEM_KEYWORDS.items():
        connection.execute(
            categories.update()
            .where(categories.c.name == name)
            .values(keywords=keywords)
        )


def upgrade() -> None:
    connection = op.get_bind()
    accounts = connection.execute(
        sa.text('SELECT id, account_number FROM bank_accounts')
    ).fetchall()
    encrypted_accounts = []
    if accounts:
        cipher = _cipher_for_existing_rows()
        for account_id, account_number in accounts:
            normalized = str(account_number or '').strip()
            if len(normalized) < 4:
                raise RuntimeError(
                    f'Bank account {account_id} has an invalid account number'
                )
            encrypted_accounts.append(
                (
                    account_id,
                    cipher.encrypt(normalized.encode()).decode(),
                    normalized[-4:],
                )
            )

    op.add_column(
        'bank_accounts',
        sa.Column('account_number_encrypted', sa.Text()),
    )
    op.add_column(
        'bank_accounts',
        sa.Column('account_number_last4', sa.String(4)),
    )

    for account_id, encrypted, last4 in encrypted_accounts:
        connection.execute(
            sa.text(
                """
                UPDATE bank_accounts
                SET account_number_encrypted = :encrypted,
                    account_number_last4 = :last4
                WHERE id = :account_id
                """
            ),
            {
                'encrypted': encrypted,
                'last4': last4,
                'account_id': account_id,
            },
        )

    with op.batch_alter_table('bank_accounts') as batch_op:
        batch_op.alter_column(
            'account_number_encrypted',
            existing_type=sa.Text(),
            nullable=False,
        )
        batch_op.alter_column(
            'account_number_last4',
            existing_type=sa.String(4),
            nullable=False,
        )
        batch_op.drop_column('account_number')

    _replace_category_keywords(connection)


def downgrade() -> None:
    connection = op.get_bind()
    accounts = connection.execute(
        sa.text('SELECT id, account_number_encrypted FROM bank_accounts')
    ).fetchall()
    decrypted_accounts = []
    if accounts:
        cipher = _cipher_for_existing_rows()
        for account_id, encrypted in accounts:
            decrypted_accounts.append(
                (
                    account_id,
                    cipher.decrypt(str(encrypted).encode()).decode(),
                )
            )

    op.add_column(
        'bank_accounts',
        sa.Column('account_number', sa.String(50)),
    )
    for account_id, account_number in decrypted_accounts:
        connection.execute(
            sa.text(
                """
                UPDATE bank_accounts
                SET account_number = :account_number
                WHERE id = :account_id
                """
            ),
            {
                'account_number': account_number,
                'account_id': account_id,
            },
        )

    with op.batch_alter_table('bank_accounts') as batch_op:
        batch_op.alter_column(
            'account_number',
            existing_type=sa.String(50),
            nullable=False,
        )
        batch_op.drop_column('account_number_last4')
        batch_op.drop_column('account_number_encrypted')

    # Learned global keywords are intentionally not restored on downgrade.
