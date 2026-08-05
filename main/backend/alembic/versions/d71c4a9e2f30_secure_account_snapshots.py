"""Secure account ownership and account-scoped portfolio snapshots.

Revision ID: d71c4a9e2f30
Revises: b1f00545dd90
"""
from datetime import datetime
from decimal import Decimal
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = 'd71c4a9e2f30'
down_revision: Union[str, None] = 'b1f00545dd90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NAMING_CONVENTION = {
    'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    'uq': 'uq_%(table_name)s_%(column_0_name)s',
}


def _unique_constraint_name(connection, table_name, columns, fallback):
    """Resolve database-generated names while retaining SQLite batch support."""
    expected_columns = list(columns)
    for constraint in sa.inspect(connection).get_unique_constraints(table_name):
        if list(constraint.get('column_names') or []) == expected_columns:
            return constraint.get('name') or fallback
    raise RuntimeError(
        f'Unique constraint not found on {table_name}({", ".join(columns)})'
    )


def _foreign_key_name(
    connection,
    table_name,
    columns,
    referred_table,
    referred_columns,
    fallback,
):
    """Resolve a foreign-key name across PostgreSQL and SQLite."""
    expected_columns = list(columns)
    expected_referred_columns = list(referred_columns)
    for constraint in sa.inspect(connection).get_foreign_keys(table_name):
        if (
            list(constraint.get('constrained_columns') or [])
            == expected_columns
            and constraint.get('referred_table') == referred_table
            and list(constraint.get('referred_columns') or [])
            == expected_referred_columns
        ):
            return constraint.get('name') or fallback
    raise RuntimeError(
        f'Foreign key not found on {table_name}({", ".join(columns)})'
    )


def _as_datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _claim_orphan_accounts(connection):
    orphan_count = connection.scalar(
        sa.text('SELECT COUNT(*) FROM accounts WHERE user_id IS NULL')
    )
    if not orphan_count:
        return

    email = f"legacy-unclaimed-{uuid.uuid4().hex}@invalid.local"
    result = connection.execute(
        sa.text(
            """
            INSERT INTO users (
                email, password_hash, full_name, created_at, updated_at,
                last_login_at, is_active
            ) VALUES (
                :email, :password_hash, :full_name, :created_at, :updated_at,
                NULL, :is_active
            )
            """
        ),
        {
            'email': email,
            'password_hash': '!disabled-legacy-owner!',
            'full_name': 'Disabled legacy portfolio owner',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'is_active': False,
        },
    )
    legacy_user_id = result.lastrowid
    if legacy_user_id is None:
        legacy_user_id = connection.scalar(
            sa.text('SELECT id FROM users WHERE email = :email'),
            {'email': email},
        )
    connection.execute(
        sa.text(
            'UPDATE accounts SET user_id = :user_id WHERE user_id IS NULL'
        ),
        {'user_id': legacy_user_id},
    )


def _create_quarantine_account(connection):
    """Create an inaccessible owner/account for otherwise orphan snapshots."""
    suffix = uuid.uuid4().hex
    user_result = connection.execute(
        sa.text(
            """
            INSERT INTO users (
                email, password_hash, full_name, created_at, updated_at,
                last_login_at, is_active
            ) VALUES (
                :email, :password_hash, :full_name, :created_at, :updated_at,
                NULL, :is_active
            )
            """
        ),
        {
            'email': f'legacy-snapshot-{suffix}@invalid.local',
            'password_hash': '!disabled-legacy-owner!',
            'full_name': 'Disabled legacy snapshot owner',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'is_active': False,
        },
    )
    user_id = user_result.lastrowid or connection.scalar(
        sa.text('SELECT id FROM users WHERE email = :email'),
        {'email': f'legacy-snapshot-{suffix}@invalid.local'},
    )
    account_result = connection.execute(
        sa.text(
            """
            INSERT INTO accounts (
                account_name, api_key_encrypted, api_secret_encrypted,
                access_token_encrypted, request_token_encrypted, user_id,
                is_active, last_synced_at, created_at, updated_at
            ) VALUES (
                :account_name, :api_key, :api_secret, NULL, NULL, :user_id,
                :is_active, NULL, :created_at, :updated_at
            )
            """
        ),
        {
            'account_name': f'Quarantined legacy snapshots {suffix[:8]}',
            'api_key': '!unusable!',
            'api_secret': '!unusable!',
            'user_id': user_id,
            'is_active': False,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        },
    )
    return account_result.lastrowid or connection.scalar(
        sa.text(
            'SELECT id FROM accounts WHERE user_id = :user_id'
        ),
        {'user_id': user_id},
    )


def upgrade() -> None:
    connection = op.get_bind()
    _claim_orphan_accounts(connection)

    account_name_constraint = _unique_constraint_name(
        connection,
        'accounts',
        ['account_name'],
        'uq_accounts_account_name',
    )
    account_user_constraint = _foreign_key_name(
        connection,
        'accounts',
        ['user_id'],
        'users',
        ['id'],
        'fk_accounts_user_id_users',
    )
    with op.batch_alter_table(
        'accounts',
        naming_convention=NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint(
            account_name_constraint,
            type_='unique',
        )
        batch_op.drop_constraint(
            account_user_constraint,
            type_='foreignkey',
        )
        batch_op.alter_column(
            'user_id',
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.create_foreign_key(
            'fk_accounts_user_id_users',
            'users',
            ['user_id'],
            ['id'],
            ondelete='CASCADE',
        )
        batch_op.create_unique_constraint(
            'uq_accounts_user_account_name',
            ['user_id', 'account_name'],
        )

    op.add_column('snapshots', sa.Column('account_id', sa.Integer()))
    op.add_column('snapshots', sa.Column('batch_id', sa.String(36)))
    op.add_column('snapshots', sa.Column('status', sa.String(20)))
    op.add_column('snapshots', sa.Column('trigger', sa.String(20)))
    op.add_column('snapshots', sa.Column('error_message', sa.String(255)))
    op.add_column('snapshots', sa.Column('currency', sa.String(8)))

    op.add_column('holdings', sa.Column('holding_key', sa.String(255)))
    op.add_column('holdings', sa.Column('folio', sa.String(100)))
    op.add_column('holdings', sa.Column('currency', sa.String(3)))
    op.add_column('holdings', sa.Column('last_price_date', sa.Date()))
    op.add_column('holdings', sa.Column('maturity_date', sa.Date()))
    op.add_column('holdings', sa.Column('interest_rate', sa.Numeric(7, 4)))
    op.add_column('holdings', sa.Column('source', sa.String(30)))
    op.add_column('holdings', sa.Column('valued_at', sa.DateTime()))

    # The old schema enforced one global timestamp. Remove that constraint
    # before splitting a family snapshot into one row per account.
    snapshot_date_constraint = _unique_constraint_name(
        connection,
        'snapshots',
        ['snapshot_date'],
        'uq_snapshots_snapshot_date',
    )
    with op.batch_alter_table(
        'snapshots',
        naming_convention=NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint(
            snapshot_date_constraint,
            type_='unique',
        )

    snapshots = connection.execute(
        sa.text(
            """
            SELECT id, snapshot_date, total_holdings, total_investment,
                   current_value, total_pnl, total_pnl_percentage, created_at
            FROM snapshots
            ORDER BY id
            """
        )
    ).fetchall()
    quarantine_account_id = None
    snapshot_table = sa.Table(
        'snapshots',
        sa.MetaData(),
        autoload_with=connection,
    )
    for row in snapshots:
        (
            snapshot_id,
            snapshot_date,
            total_holdings,
            total_investment,
            current_value,
            total_pnl,
            total_pnl_percentage,
            created_at,
        ) = row
        account_ids = {
            account_row[0]
            for table_name in (
                'holdings',
                'portfolio_timeseries',
                'sector_allocation',
            )
            for account_row in connection.execute(
                sa.text(
                    f"""
                    SELECT DISTINCT account_id
                    FROM {table_name}
                    WHERE snapshot_id = :snapshot_id
                      AND account_id IS NOT NULL
                    """
                ),
                {'snapshot_id': snapshot_id},
            ).fetchall()
        }
        if not account_ids:
            if quarantine_account_id is None:
                quarantine_account_id = _create_quarantine_account(connection)
            account_ids = {quarantine_account_id}

        batch_id = str(uuid.uuid4())
        for position, account_id in enumerate(sorted(account_ids)):
            if position == 0:
                account_snapshot_id = snapshot_id
                connection.execute(
                    sa.text(
                        """
                        UPDATE snapshots
                        SET account_id = :account_id,
                            batch_id = :batch_id,
                            status = 'completed',
                            trigger = 'legacy'
                        WHERE id = :snapshot_id
                        """
                    ),
                    {
                        'account_id': account_id,
                        'batch_id': batch_id,
                        'snapshot_id': snapshot_id,
                    },
                )
            else:
                result = connection.execute(
                    snapshot_table.insert().values(
                        account_id=account_id,
                        batch_id=batch_id,
                        snapshot_date=_as_datetime(snapshot_date),
                        status='completed',
                        trigger='legacy',
                        error_message=None,
                        currency=None,
                        total_holdings=total_holdings,
                        total_investment=total_investment,
                        current_value=current_value,
                        total_pnl=total_pnl,
                        total_pnl_percentage=total_pnl_percentage,
                        created_at=_as_datetime(created_at),
                    )
                )
                account_snapshot_id = result.inserted_primary_key[0]

            for table_name in (
                'holdings',
                'portfolio_timeseries',
                'sector_allocation',
            ):
                connection.execute(
                    sa.text(
                        f"""
                        UPDATE {table_name}
                        SET snapshot_id = :new_snapshot_id
                        WHERE snapshot_id = :old_snapshot_id
                          AND account_id = :account_id
                        """
                    ),
                    {
                        'new_snapshot_id': account_snapshot_id,
                        'old_snapshot_id': snapshot_id,
                        'account_id': account_id,
                    },
                )

    holding_rows = connection.execute(
        sa.text(
            """
            SELECT h.id, h.instrument_type, h.exchange, h.tradingsymbol,
                   h.market, s.snapshot_date
            FROM holdings h
            LEFT JOIN snapshots s ON s.id = h.snapshot_id
            """
        )
    ).fetchall()
    for row in holding_rows:
        holding_id, instrument_type, exchange, symbol, market, valued_at = row
        currency = 'USD' if str(market or '').upper() == 'US' else 'INR'
        holding_key = (
            f"legacy:{instrument_type or 'unknown'}:{exchange or ''}:"
            f"{symbol}:{holding_id}"
        )[:255]
        connection.execute(
            sa.text(
                """
                UPDATE holdings
                SET holding_key = :holding_key,
                    currency = :currency,
                    source = 'legacy',
                    valued_at = :valued_at
                WHERE id = :holding_id
                """
            ),
            {
                'holding_key': holding_key,
                'currency': currency,
                'valued_at': valued_at,
                'holding_id': holding_id,
            },
        )

    connection.execute(
        sa.text(
            """
            UPDATE snapshots
            SET currency = (
                CASE
                    WHEN (
                        SELECT COUNT(DISTINCT h.currency)
                        FROM holdings h
                        WHERE h.snapshot_id = snapshots.id
                    ) = 1 THEN (
                        SELECT MIN(h.currency)
                        FROM holdings h
                        WHERE h.snapshot_id = snapshots.id
                    )
                    WHEN (
                        SELECT COUNT(DISTINCT h.currency)
                        FROM holdings h
                        WHERE h.snapshot_id = snapshots.id
                    ) > 1 THEN 'MIXED'
                    ELSE NULL
                END
            )
            """
        )
    )

    # Recalculate every split snapshot from its own holdings. Mixed-currency
    # rows keep no scalar money total because no FX policy exists.
    for (snapshot_id,) in connection.execute(
        sa.text('SELECT id FROM snapshots')
    ).fetchall():
        positions = connection.execute(
            sa.text(
                """
                SELECT quantity, average_price, last_price, current_value,
                       currency
                FROM holdings
                WHERE snapshot_id = :snapshot_id
                """
            ),
            {'snapshot_id': snapshot_id},
        ).fetchall()
        currencies = {position[4] for position in positions if position[4]}
        invested = sum(
            Decimal(str(position[0] or 0))
            * Decimal(str(position[1] or 0))
            for position in positions
        )
        value = sum(
            Decimal(
                str(
                    position[3]
                    if position[3] is not None
                    else Decimal(str(position[0] or 0))
                    * Decimal(str(position[2] or 0))
                )
            )
            for position in positions
        )
        homogeneous = len(currencies) <= 1
        pnl = value - invested
        connection.execute(
            sa.text(
                """
                UPDATE snapshots
                SET total_holdings = :total_holdings,
                    total_investment = :total_investment,
                    current_value = :current_value,
                    total_pnl = :total_pnl,
                    total_pnl_percentage = :pnl_percentage,
                    currency = :currency
                WHERE id = :snapshot_id
                """
            ),
            {
                'total_holdings': len(positions),
                'total_investment': float(invested) if homogeneous else None,
                'current_value': float(value) if homogeneous else None,
                'total_pnl': float(pnl) if homogeneous else None,
                'pnl_percentage': (
                    float(pnl / invested * 100)
                    if homogeneous and invested
                    else None
                ),
                'currency': (
                    next(iter(currencies))
                    if len(currencies) == 1
                    else 'MIXED'
                    if len(currencies) > 1
                    else None
                ),
                'snapshot_id': snapshot_id,
            },
        )

    with op.batch_alter_table(
        'snapshots',
        naming_convention=NAMING_CONVENTION,
    ) as batch_op:
        batch_op.alter_column(
            'account_id',
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.alter_column(
            'batch_id',
            existing_type=sa.String(36),
            nullable=False,
        )
        batch_op.alter_column(
            'status',
            existing_type=sa.String(20),
            nullable=False,
        )
        batch_op.alter_column(
            'trigger',
            existing_type=sa.String(20),
            nullable=False,
        )
        batch_op.create_foreign_key(
            'fk_snapshots_account_id_accounts',
            'accounts',
            ['account_id'],
            ['id'],
            ondelete='CASCADE',
        )
        batch_op.create_unique_constraint(
            'uq_snapshots_account_date',
            ['account_id', 'snapshot_date'],
        )
    op.create_index(
        'ix_snapshots_account_id',
        'snapshots',
        ['account_id'],
    )
    op.create_index('ix_snapshots_batch_id', 'snapshots', ['batch_id'])
    op.create_index(
        'idx_snapshots_account_status_date',
        'snapshots',
        ['account_id', 'status', 'snapshot_date'],
    )

    with op.batch_alter_table('holdings') as batch_op:
        batch_op.drop_constraint(
            '_snapshot_account_symbol_uc',
            type_='unique',
        )
        batch_op.alter_column(
            'tradingsymbol',
            existing_type=sa.String(50),
            type_=sa.String(100),
            nullable=False,
        )
        batch_op.alter_column(
            'quantity',
            existing_type=sa.Integer(),
            type_=sa.Numeric(20, 6),
            nullable=False,
        )
        batch_op.alter_column(
            'average_price',
            existing_type=sa.Numeric(15, 2),
            type_=sa.Numeric(20, 6),
            nullable=False,
        )
        batch_op.alter_column(
            'last_price',
            existing_type=sa.Numeric(15, 2),
            type_=sa.Numeric(20, 6),
            nullable=False,
        )
        batch_op.alter_column(
            'holding_key',
            existing_type=sa.String(255),
            nullable=False,
        )
        batch_op.alter_column(
            'currency',
            existing_type=sa.String(3),
            nullable=False,
        )
        batch_op.create_unique_constraint(
            'uq_holding_snapshot_account_key',
            ['snapshot_id', 'account_id', 'holding_key'],
        )

    op.add_column(
        'portfolio_timeseries',
        sa.Column('currency', sa.String(3)),
    )
    connection.execute(
        sa.text(
            """
            UPDATE portfolio_timeseries
            SET currency = COALESCE(
                (
                    SELECT CASE
                        WHEN s.currency IN ('INR', 'USD') THEN s.currency
                        ELSE 'XXX'
                    END
                    FROM snapshots s
                    WHERE s.id = portfolio_timeseries.snapshot_id
                ),
                'INR'
            )
            """
        )
    )
    with op.batch_alter_table('portfolio_timeseries') as batch_op:
        batch_op.drop_constraint('_account_date_uc', type_='unique')
        batch_op.alter_column(
            'currency',
            existing_type=sa.String(3),
            nullable=False,
        )
        batch_op.create_unique_constraint(
            'uq_account_date_currency',
            ['account_id', 'date', 'currency'],
        )

    op.add_column(
        'sector_allocation',
        sa.Column('currency', sa.String(3)),
    )
    connection.execute(
        sa.text(
            """
            UPDATE sector_allocation
            SET currency = COALESCE(
                (
                    SELECT CASE
                        WHEN s.currency IN ('INR', 'USD') THEN s.currency
                        ELSE 'XXX'
                    END
                    FROM snapshots s
                    WHERE s.id = sector_allocation.snapshot_id
                ),
                'INR'
            )
            """
        )
    )
    with op.batch_alter_table('sector_allocation') as batch_op:
        batch_op.alter_column(
            'currency',
            existing_type=sa.String(3),
            nullable=False,
        )


def downgrade() -> None:
    raise RuntimeError(
        'Revision d71c4a9e2f30 is intentionally irreversible after family '
        'accounts are enabled. Restore a pre-upgrade backup instead.'
    )

    with op.batch_alter_table('sector_allocation') as batch_op:
        batch_op.drop_column('currency')

    with op.batch_alter_table('portfolio_timeseries') as batch_op:
        batch_op.drop_constraint(
            'uq_account_date_currency',
            type_='unique',
        )
        batch_op.create_unique_constraint(
            '_account_date_uc',
            ['account_id', 'date'],
        )
        batch_op.drop_column('currency')

    with op.batch_alter_table('holdings') as batch_op:
        batch_op.drop_constraint(
            'uq_holding_snapshot_account_key',
            type_='unique',
        )
        batch_op.create_unique_constraint(
            '_snapshot_account_symbol_uc',
            ['snapshot_id', 'account_id', 'tradingsymbol'],
        )
        batch_op.alter_column(
            'quantity',
            existing_type=sa.Numeric(20, 6),
            type_=sa.Integer(),
            nullable=False,
        )
        batch_op.drop_column('valued_at')
        batch_op.drop_column('source')
        batch_op.drop_column('interest_rate')
        batch_op.drop_column('maturity_date')
        batch_op.drop_column('last_price_date')
        batch_op.drop_column('currency')
        batch_op.drop_column('folio')
        batch_op.drop_column('holding_key')

    op.drop_index(
        'idx_snapshots_account_status_date',
        table_name='snapshots',
    )
    op.drop_index('ix_snapshots_batch_id', table_name='snapshots')
    op.drop_index('ix_snapshots_account_id', table_name='snapshots')
    with op.batch_alter_table('snapshots') as batch_op:
        batch_op.drop_constraint(
            'uq_snapshots_account_date',
            type_='unique',
        )
        batch_op.drop_constraint(
            'fk_snapshots_account_id_accounts',
            type_='foreignkey',
        )
        batch_op.create_unique_constraint(
            'uq_snapshots_snapshot_date',
            ['snapshot_date'],
        )
        batch_op.drop_column('currency')
        batch_op.drop_column('error_message')
        batch_op.drop_column('trigger')
        batch_op.drop_column('status')
        batch_op.drop_column('batch_id')
        batch_op.drop_column('account_id')

    with op.batch_alter_table('accounts') as batch_op:
        batch_op.drop_constraint(
            'uq_accounts_user_account_name',
            type_='unique',
        )
        batch_op.create_unique_constraint(
            'uq_accounts_account_name',
            ['account_name'],
        )
        batch_op.alter_column(
            'user_id',
            existing_type=sa.Integer(),
            nullable=True,
        )
