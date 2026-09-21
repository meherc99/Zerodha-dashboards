"""Consolidate portfolio_timeseries rows to one-per-account-day-currency bucket.

Each row's datetime is normalised to UTC midnight so that multiple intra-day
syncs update a single authoritative data-point rather than scattering many
rows.  Duplicate rows that arose from the same calendar day are deduplicated
by keeping the one with the latest original datetime.

Revision ID: 855036219916
Revises: f93c20b8d5e1
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '855036219916'
down_revision: Union[str, None] = 'a04d1b7c8e92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _trunc_to_day(dt_value):
    """Truncate a datetime (or ISO string) to UTC midnight."""
    if dt_value is None:
        return dt_value
    if isinstance(dt_value, str):
        dt_value = datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
    return dt_value.replace(hour=0, minute=0, second=0, microsecond=0,
                            tzinfo=None)


def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. Load all timeseries rows ──────────────────────────────────────────
    rows = bind.execute(
        sa.text(
            'SELECT id, account_id, date, currency, snapshot_id, '
            '       total_value, invested_value, pnl, pnl_percentage, '
            '       day_change, holdings_count, created_at '
            'FROM portfolio_timeseries '
            'ORDER BY account_id, currency, date ASC'
        )
    ).fetchall()

    if not rows:
        return  # nothing to migrate

    # ── 2. Deduplicate: for each (account_id, day, currency) keep the row
    #       with the latest original date.  Build a map keyed by the tuple
    #       (account_id, day_midnight, currency) → best row so far.
    best: dict = {}
    for row in rows:
        day = _trunc_to_day(row[2])  # normalise date column
        key = (row[1], day, row[3])  # (account_id, midnight, currency)
        prev = best.get(key)
        # Keep whichever has the later original timestamp.
        if prev is None or row[2] > prev[2]:
            best[key] = row

    # ── 3. Delete ALL existing rows – we will re-insert the deduplicated set.
    bind.execute(sa.text('DELETE FROM portfolio_timeseries'))

    # ── 4. Re-insert one row per (account_id, day, currency).
    for (account_id, day, currency), row in best.items():
        bind.execute(
            sa.text(
                'INSERT INTO portfolio_timeseries '
                '(account_id, date, currency, snapshot_id, '
                ' total_value, invested_value, pnl, pnl_percentage, '
                ' day_change, holdings_count, created_at) '
                'VALUES (:account_id, :date, :currency, :snapshot_id, '
                '        :total_value, :invested_value, :pnl, :pnl_percentage,'
                '        :day_change, :holdings_count, :created_at)'
            ),
            {
                'account_id': account_id,
                'date': day.isoformat(),
                'currency': currency,
                'snapshot_id': row[4],
                'total_value': row[5],
                'invested_value': row[6],
                'pnl': row[7],
                'pnl_percentage': row[8],
                'day_change': row[9],
                'holdings_count': row[10],
                'created_at': row[11],
            }
        )


def downgrade() -> None:
    # Downgrade is a no-op: we cannot restore sub-day precision that was
    # intentionally discarded, and the schema itself is unchanged.
    pass
