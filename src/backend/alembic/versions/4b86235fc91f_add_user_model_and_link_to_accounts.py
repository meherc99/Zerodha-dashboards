"""Create the user and core portfolio schema.

Revision ID: 4b86235fc91f
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4b86235fc91f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
        sa.Column('last_login_at', sa.DateTime()),
        sa.Column('is_active', sa.Boolean(), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table(
        'accounts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('account_name', sa.String(100), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=False),
        sa.Column('api_secret_encrypted', sa.Text(), nullable=False),
        sa.Column('access_token_encrypted', sa.Text()),
        sa.Column('request_token_encrypted', sa.Text()),
        sa.Column('user_id', sa.Integer()),
        sa.Column('is_active', sa.Boolean()),
        sa.Column('last_synced_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.UniqueConstraint('account_name'),
    )
    op.create_index('ix_accounts_user_id', 'accounts', ['user_id'])

    op.create_table(
        'snapshots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('snapshot_date', sa.DateTime(), nullable=False),
        sa.Column('total_holdings', sa.Integer()),
        sa.Column('total_investment', sa.Numeric(15, 2)),
        sa.Column('current_value', sa.Numeric(15, 2)),
        sa.Column('total_pnl', sa.Numeric(15, 2)),
        sa.Column('total_pnl_percentage', sa.Numeric(8, 2)),
        sa.Column('created_at', sa.DateTime()),
        sa.UniqueConstraint('snapshot_date'),
    )
    op.create_index('idx_snapshots_date', 'snapshots', ['snapshot_date'])

    op.create_table(
        'historical_prices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tradingsymbol', sa.String(50), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('open', sa.Numeric(15, 2)),
        sa.Column('high', sa.Numeric(15, 2)),
        sa.Column('low', sa.Numeric(15, 2)),
        sa.Column('close', sa.Numeric(15, 2), nullable=False),
        sa.Column('volume', sa.BigInteger()),
        sa.Column('created_at', sa.DateTime()),
        sa.UniqueConstraint('tradingsymbol', 'date', name='_symbol_date_uc'),
    )
    op.create_index(
        'idx_historical_prices_symbol_date',
        'historical_prices',
        ['tradingsymbol', 'date'],
    )

    op.create_table(
        'holdings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('snapshot_id', sa.Integer()),
        sa.Column('tradingsymbol', sa.String(50), nullable=False),
        sa.Column('instrument_type', sa.String(20), nullable=False),
        sa.Column('market', sa.String(10)),
        sa.Column('exchange', sa.String(10)),
        sa.Column('isin', sa.String(20)),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('average_price', sa.Numeric(15, 2), nullable=False),
        sa.Column('last_price', sa.Numeric(15, 2), nullable=False),
        sa.Column('pnl', sa.Numeric(15, 2)),
        sa.Column('pnl_percentage', sa.Numeric(8, 2)),
        sa.Column('day_change', sa.Numeric(15, 2)),
        sa.Column('day_change_percentage', sa.Numeric(8, 2)),
        sa.Column('current_value', sa.Numeric(15, 2)),
        sa.Column('purchase_date', sa.Date()),
        sa.Column('sector', sa.String(50)),
        sa.Column('created_at', sa.DateTime()),
        sa.ForeignKeyConstraint(
            ['account_id'], ['accounts.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['snapshot_id'], ['snapshots.id'], ondelete='SET NULL'
        ),
        sa.UniqueConstraint(
            'snapshot_id',
            'account_id',
            'tradingsymbol',
            name='_snapshot_account_symbol_uc',
        ),
    )
    op.create_index('idx_holdings_account', 'holdings', ['account_id'])
    op.create_index('idx_holdings_snapshot', 'holdings', ['snapshot_id'])
    op.create_index('idx_holdings_symbol', 'holdings', ['tradingsymbol'])
    op.create_index('idx_holdings_type', 'holdings', ['instrument_type'])

    op.create_table(
        'portfolio_timeseries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('snapshot_id', sa.Integer()),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('total_value', sa.Numeric(15, 2), nullable=False),
        sa.Column('invested_value', sa.Numeric(15, 2), nullable=False),
        sa.Column('pnl', sa.Numeric(15, 2)),
        sa.Column('pnl_percentage', sa.Numeric(8, 2)),
        sa.Column('day_change', sa.Numeric(15, 2)),
        sa.Column('holdings_count', sa.Integer()),
        sa.Column('created_at', sa.DateTime()),
        sa.ForeignKeyConstraint(
            ['account_id'], ['accounts.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['snapshot_id'], ['snapshots.id'], ondelete='SET NULL'
        ),
        sa.UniqueConstraint('account_id', 'date', name='_account_date_uc'),
    )
    op.create_index(
        'idx_portfolio_ts_account_date',
        'portfolio_timeseries',
        ['account_id', 'date'],
    )
    op.create_index('idx_portfolio_ts_date', 'portfolio_timeseries', ['date'])

    op.create_table(
        'sector_allocation',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('snapshot_id', sa.Integer()),
        sa.Column('account_id', sa.Integer()),
        sa.Column('sector', sa.String(50), nullable=False),
        sa.Column('allocation_percentage', sa.Numeric(5, 2)),
        sa.Column('total_value', sa.Numeric(15, 2)),
        sa.Column('pnl', sa.Numeric(15, 2)),
        sa.Column('created_at', sa.DateTime()),
        sa.ForeignKeyConstraint(
            ['account_id'], ['accounts.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['snapshot_id'], ['snapshots.id'], ondelete='CASCADE'
        ),
    )
    op.create_index(
        'idx_sector_allocation_snapshot',
        'sector_allocation',
        ['snapshot_id'],
    )


def downgrade() -> None:
    op.drop_table('sector_allocation')
    op.drop_table('portfolio_timeseries')
    op.drop_table('holdings')
    op.drop_table('historical_prices')
    op.drop_table('snapshots')
    op.drop_table('accounts')
    op.drop_table('users')
