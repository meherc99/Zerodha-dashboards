from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


class DataStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS equity_snapshots (
                    account TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    tradingsymbol TEXT NOT NULL,
                    exchange TEXT,
                    quantity REAL,
                    average_price REAL,
                    last_price REAL,
                    pnl REAL,
                    invested_value REAL,
                    current_value REAL,
                    source TEXT,
                    PRIMARY KEY (account, ts, tradingsymbol, exchange)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS mf_snapshots (
                    account TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    fund TEXT NOT NULL,
                    folio TEXT,
                    quantity REAL,
                    average_price REAL,
                    last_price REAL,
                    pnl REAL,
                    invested_value REAL,
                    current_value REAL,
                    PRIMARY KEY (account, ts, fund, folio)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    account TEXT NOT NULL,
                    trade_id TEXT NOT NULL,
                    order_id TEXT,
                    symbol TEXT,
                    exchange TEXT,
                    quantity REAL,
                    average_price REAL,
                    trade_timestamp TEXT,
                    transaction_type TEXT,
                    product TEXT,
                    PRIMARY KEY (account, trade_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_runs (
                    account TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT
                )
                """
            )
            connection.commit()

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def insert_equity_snapshot(self, rows: list[dict]) -> None:
        if not rows:
            return
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO equity_snapshots
                (account, ts, tradingsymbol, exchange, quantity, average_price, last_price, pnl, invested_value, current_value, source)
                VALUES
                (:account, :ts, :tradingsymbol, :exchange, :quantity, :average_price, :last_price, :pnl, :invested_value, :current_value, :source)
                """,
                rows,
            )
            connection.commit()

    def insert_mf_snapshot(self, rows: list[dict]) -> None:
        if not rows:
            return
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO mf_snapshots
                (account, ts, fund, folio, quantity, average_price, last_price, pnl, invested_value, current_value)
                VALUES
                (:account, :ts, :fund, :folio, :quantity, :average_price, :last_price, :pnl, :invested_value, :current_value)
                """,
                rows,
            )
            connection.commit()

    def upsert_trades(self, rows: list[dict]) -> None:
        if not rows:
            return
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO trades
                (account, trade_id, order_id, symbol, exchange, quantity, average_price, trade_timestamp, transaction_type, product)
                VALUES
                (:account, :trade_id, :order_id, :symbol, :exchange, :quantity, :average_price, :trade_timestamp, :transaction_type, :product)
                """,
                rows,
            )
            connection.commit()

    def insert_sync_run(self, account: str, status: str, message: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO sync_runs (account, ts, status, message) VALUES (?, ?, ?, ?)",
                (account, self.now_iso(), status, message),
            )
            connection.commit()

    def get_latest_equity(self) -> pd.DataFrame:
        query = """
        SELECT e.*
        FROM equity_snapshots e
        JOIN (
            SELECT account, MAX(ts) AS latest_ts
            FROM equity_snapshots
            GROUP BY account
        ) latest
          ON e.account = latest.account AND e.ts = latest.latest_ts
        """
        with self._connect() as connection:
            return pd.read_sql_query(query, connection)

    def get_latest_mf(self) -> pd.DataFrame:
        query = """
        SELECT m.*
        FROM mf_snapshots m
        JOIN (
            SELECT account, MAX(ts) AS latest_ts
            FROM mf_snapshots
            GROUP BY account
        ) latest
          ON m.account = latest.account AND m.ts = latest.latest_ts
        """
        with self._connect() as connection:
            return pd.read_sql_query(query, connection)

    def get_first_buy_dates(self) -> pd.DataFrame:
        query = """
        SELECT account, symbol, MIN(trade_timestamp) AS first_buy_date
        FROM trades
        WHERE UPPER(transaction_type) = 'BUY' AND symbol IS NOT NULL
        GROUP BY account, symbol
        """
        with self._connect() as connection:
            return pd.read_sql_query(query, connection)

    def get_portfolio_history(self) -> pd.DataFrame:
        query = """
        SELECT ts, SUM(current_value) AS total_value, SUM(invested_value) AS total_invested
        FROM (
            SELECT ts, current_value, invested_value FROM equity_snapshots
            UNION ALL
            SELECT ts, current_value, invested_value FROM mf_snapshots
        ) all_assets
        GROUP BY ts
        ORDER BY ts
        """
        with self._connect() as connection:
            return pd.read_sql_query(query, connection)

    def get_recent_sync_runs(self, limit: int = 25) -> pd.DataFrame:
        query = """
        SELECT account, ts, status, message
        FROM sync_runs
        ORDER BY ts DESC
        LIMIT ?
        """
        with self._connect() as connection:
            return pd.read_sql_query(query, connection, params=(limit,))
