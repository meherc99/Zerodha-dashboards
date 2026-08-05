"""Alembic upgrade-path tests for clean and populated SQLite databases."""

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from cryptography.fernet import Fernet


BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
HEAD_REVISION = "b15a7e4c2d90"
LEGACY_REVISION = "b1f00545dd90"
ENCRYPTION_REVISION = "e82b91a7c4d6"
TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()


def _run_alembic(
    database_path,
    *arguments,
    encryption_key=TEST_ENCRYPTION_KEY,
):
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": f"sqlite:///{database_path}",
            "FLASK_ENV": "development",
            "SCHEDULER_ENABLED": "false",
            "PYTHONPYCACHEPREFIX": str(database_path.parent / "pycache"),
        }
    )
    if encryption_key is None:
        # Keep python-dotenv from silently filling the key from a developer's
        # local .env file: an explicit empty process value is not overridden.
        environment["ENCRYPTION_KEY"] = ""
    else:
        environment["ENCRYPTION_KEY"] = encryption_key
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(ALEMBIC_INI),
            *arguments,
        ],
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    return result


def _upgrade(database_path, revision, *, encryption_key=TEST_ENCRYPTION_KEY):
    result = _run_alembic(
        database_path,
        "upgrade",
        revision,
        encryption_key=encryption_key,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _columns(connection, table):
    return {
        row[1]: {"type": row[2], "nullable": not bool(row[3])}
        for row in connection.execute(f"PRAGMA table_info({table})")
    }


def test_clean_database_upgrades_to_head(tmp_path):
    database_path = tmp_path / "clean.db"
    _upgrade(database_path, "head")

    with sqlite3.connect(database_path) as connection:
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        account_columns = _columns(connection, "accounts")
        bank_account_columns = _columns(connection, "bank_accounts")
        bank_statement_columns = _columns(connection, "bank_statements")
        snapshot_columns = _columns(connection, "snapshots")
        holding_columns = _columns(connection, "holdings")

        assert revision == HEAD_REVISION
        assert {
            "users",
            "accounts",
            "snapshots",
            "holdings",
            "portfolio_timeseries",
            "sector_allocation",
            "bank_accounts",
            "bank_statements",
            "transactions",
            "revoked_tokens",
        } <= tables
        assert account_columns["user_id"]["nullable"] is False
        assert account_columns["portfolio_version"]["nullable"] is False
        assert "account_number" not in bank_account_columns
        assert bank_account_columns["account_number_encrypted"]["nullable"] is False
        assert bank_account_columns["account_number_last4"]["nullable"] is False
        assert bank_account_columns["opening_balance"]["nullable"] is False
        assert bank_statement_columns["file_sha256"]["nullable"] is True
        assert snapshot_columns["account_id"]["nullable"] is False
        assert snapshot_columns["batch_id"]["nullable"] is False
        assert holding_columns["holding_key"]["nullable"] is False
        assert "NUMERIC(20, 6)" in holding_columns["quantity"]["type"].upper()
        assert connection.execute(
            "SELECT COUNT(*) FROM transaction_categories"
        ).fetchone()[0] == 14
        assert connection.execute(
            """
            SELECT COUNT(*)
            FROM transaction_categories
            WHERE name = 'Uncategorized' AND is_system = 1
            """
        ).fetchone()[0] == 1
        revoked_columns = _columns(connection, "revoked_tokens")
        assert {
            "id",
            "jti",
            "user_id",
            "expires_at",
            "revoked_at",
        } <= set(revoked_columns)
        statement_unique_indexes = [
            row[1]
            for row in connection.execute(
                "PRAGMA index_list(bank_statements)"
            )
            if row[2]
        ]
        assert any(
            [
                index_column[2]
                for index_column in connection.execute(
                    f"PRAGMA index_info({index_name})"
                )
            ] == ["bank_account_id", "file_sha256"]
            for index_name in statement_unique_indexes
        )
        assert list(connection.execute("PRAGMA foreign_key_check")) == []


def _seed_two_account_legacy_snapshot(connection):
    users = (
        (1, "first@example.com", "hash", "First", 1),
        (2, "second@example.com", "hash", "Second", 1),
    )
    connection.executemany(
        """
        INSERT INTO users (id, email, password_hash, full_name, is_active)
        VALUES (?, ?, ?, ?, ?)
        """,
        users,
    )
    accounts = (
        (1, "First Account", "key-1", "secret-1", 1, 1),
        (2, "Second Account", "key-2", "secret-2", 2, 1),
    )
    connection.executemany(
        """
        INSERT INTO accounts (
            id, account_name, api_key_encrypted, api_secret_encrypted,
            user_id, is_active
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        accounts,
    )
    connection.execute(
        """
        INSERT INTO snapshots (
            id, snapshot_date, total_holdings, total_investment,
            current_value, total_pnl, total_pnl_percentage
        ) VALUES (1, '2026-01-01 00:00:00', 2, 300, 330, 30, 10)
        """
    )
    holdings = (
        (1, 1, 1, "INFY", 1, 100, 110, 110),
        (2, 2, 1, "TCS", 1, 200, 220, 220),
    )
    connection.executemany(
        """
        INSERT INTO holdings (
            id, account_id, snapshot_id, tradingsymbol, instrument_type,
            market, exchange, quantity, average_price, last_price,
            current_value
        ) VALUES (?, ?, ?, ?, 'equity', 'IN', 'NSE', ?, ?, ?, ?)
        """,
        holdings,
    )
    timeseries = (
        (1, 1, 1, "2026-01-01 00:00:00", 110, 100),
        (2, 2, 1, "2026-01-01 00:00:00", 220, 200),
    )
    connection.executemany(
        """
        INSERT INTO portfolio_timeseries (
            id, account_id, snapshot_id, date, total_value, invested_value
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        timeseries,
    )
    sectors = (
        (1, 1, 1, "Technology", 110, 10),
        (2, 2, 1, "Technology", 220, 20),
    )
    connection.executemany(
        """
        INSERT INTO sector_allocation (
            id, account_id, snapshot_id, sector, total_value, pnl
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        sectors,
    )
    connection.commit()


def test_legacy_global_snapshot_is_split_by_account_without_cross_tenant_data(
    tmp_path,
):
    database_path = tmp_path / "legacy.db"
    _upgrade(database_path, LEGACY_REVISION)
    with sqlite3.connect(database_path) as connection:
        _seed_two_account_legacy_snapshot(connection)

    _upgrade(database_path, "head")

    with sqlite3.connect(database_path) as connection:
        snapshots = connection.execute(
            """
            SELECT id, account_id, batch_id, total_holdings,
                   total_investment, current_value, currency
            FROM snapshots
            ORDER BY account_id
            """
        ).fetchall()
        holding_links = connection.execute(
            """
            SELECT h.account_id, s.account_id
            FROM holdings h
            JOIN snapshots s ON s.id = h.snapshot_id
            ORDER BY h.account_id
            """
        ).fetchall()
        timeseries_links = connection.execute(
            """
            SELECT p.account_id, s.account_id
            FROM portfolio_timeseries p
            JOIN snapshots s ON s.id = p.snapshot_id
            ORDER BY p.account_id
            """
        ).fetchall()

        assert len(snapshots) == 2
        assert len({snapshot[2] for snapshot in snapshots}) == 1
        assert snapshots[0][1:] == (
            1,
            snapshots[0][2],
            1,
            100,
            110,
            "INR",
        )
        assert snapshots[1][1:] == (
            2,
            snapshots[1][2],
            1,
            200,
            220,
            "INR",
        )
        assert holding_links == [(1, 1), (2, 2)]
        assert timeseries_links == [(1, 1), (2, 2)]
        assert list(connection.execute("PRAGMA foreign_key_check")) == []


def _seed_legacy_bank_data(connection):
    connection.execute(
        """
        INSERT INTO users (id, email, password_hash, full_name, is_active)
        VALUES (1, 'bank@example.com', 'hash', 'Bank Owner', 1)
        """
    )
    connection.execute(
        """
        INSERT INTO bank_accounts (
            id, user_id, bank_name, account_number, account_type,
            current_balance, currency, is_active
        ) VALUES (
            1, 1, 'HDFC Bank', '123456789012', 'savings',
            1000, 'INR', 1
        )
        """
    )
    connection.executemany(
        """
        INSERT INTO transaction_categories (
            id, name, keywords, is_system
        ) VALUES (?, ?, ?, ?)
        """,
        (
            (
                1,
                "Income",
                json.dumps(["private-employer", "private-reference"]),
                1,
            ),
            (
                2,
                "Private Custom Category",
                json.dumps(["tenant-secret-merchant"]),
                0,
            ),
        ),
    )
    connection.commit()


def test_populated_bank_accounts_are_encrypted_and_private_keywords_removed(
    tmp_path,
):
    database_path = tmp_path / "bank-encryption.db"
    _upgrade(database_path, "d71c4a9e2f30")
    with sqlite3.connect(database_path) as connection:
        _seed_legacy_bank_data(connection)

    _upgrade(database_path, "head")

    with sqlite3.connect(database_path) as connection:
        columns = _columns(connection, "bank_accounts")
        encrypted, last4 = connection.execute(
            """
            SELECT account_number_encrypted, account_number_last4
            FROM bank_accounts
            WHERE id = 1
            """
        ).fetchone()
        opening_balance = connection.execute(
            """
            SELECT opening_balance
            FROM bank_accounts
            WHERE id = 1
            """
        ).fetchone()[0]
        categories = dict(
            connection.execute(
                """
                SELECT name, keywords
                FROM transaction_categories
                ORDER BY id
                """
            )
        )

        assert "account_number" not in columns
        assert last4 == "9012"
        assert opening_balance == 1000
        assert encrypted != "123456789012"
        assert (
            Fernet(TEST_ENCRYPTION_KEY.encode())
            .decrypt(encrypted.encode())
            .decode()
            == "123456789012"
        )
        assert json.loads(categories["Income"]) == [
            "salary",
            "freelance",
            "interest",
            "dividend",
        ]
        assert json.loads(categories["Private Custom Category"]) == []
        assert "private-employer" not in json.dumps(categories)
        assert "tenant-secret-merchant" not in json.dumps(categories)


def test_missing_encryption_key_fails_before_schema_change_and_can_retry(
    tmp_path,
):
    database_path = tmp_path / "missing-key.db"
    _upgrade(database_path, "d71c4a9e2f30")
    with sqlite3.connect(database_path) as connection:
        _seed_legacy_bank_data(connection)

    failed = _run_alembic(
        database_path,
        "upgrade",
        ENCRYPTION_REVISION,
        encryption_key=None,
    )
    assert failed.returncode != 0
    assert "valid ENCRYPTION_KEY is required" in (
        failed.stdout + failed.stderr
    )

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0] == "d71c4a9e2f30"
        columns = _columns(connection, "bank_accounts")
        assert "account_number" in columns
        assert "account_number_encrypted" not in columns
        assert connection.execute(
            "SELECT account_number FROM bank_accounts WHERE id = 1"
        ).fetchone()[0] == "123456789012"

    _upgrade(database_path, "head")
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0] == HEAD_REVISION
        assert "account_number" not in _columns(connection, "bank_accounts")


def test_published_statement_revision_chain_remains_upgradeable(tmp_path):
    """The historical 751 -> 7c -> b1 ancestry must not be rewritten."""
    database_path = tmp_path / "historical-chain.db"

    _upgrade(database_path, "751d9fc01792")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert "transactions" in tables
        assert "bank_statements" not in tables
        statement_foreign_keys = [
            row
            for row in connection.execute("PRAGMA foreign_key_list(transactions)")
            if row[3] == "statement_id"
        ]
        assert statement_foreign_keys == []

    _upgrade(database_path, "7c612302520e")
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0] == "7c612302520e"
        statement_foreign_keys = [
            row
            for row in connection.execute("PRAGMA foreign_key_list(transactions)")
            if row[3] == "statement_id"
        ]
        assert len(statement_foreign_keys) == 1
        assert statement_foreign_keys[0][2] == "bank_statements"
        assert statement_foreign_keys[0][4] == "id"

    _upgrade(database_path, "b1f00545dd90")
    _upgrade(database_path, "head")
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0] == HEAD_REVISION
        assert list(connection.execute("PRAGMA foreign_key_check")) == []
