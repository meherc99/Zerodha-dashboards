from __future__ import annotations

from datetime import datetime, timezone

from .config import AppConfig
from .data_store import DataStore
from .zerodha_client import ZerodhaClient


class PortfolioSyncService:
    def __init__(self, config: AppConfig, store: DataStore) -> None:
        self.config = config
        self.store = store

    @staticmethod
    def _parse_ts(value: object) -> str:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.isoformat()
        if isinstance(value, str):
            return value
        return ""

    def sync_all_accounts(self) -> dict[str, str]:
        status: dict[str, str] = {}
        for account in self.config.accounts:
            try:
                client = ZerodhaClient(account)
                ts = self.store.now_iso()
                holdings = client.fetch_holdings()
                mf_holdings = client.fetch_mf_holdings()
                trades = client.fetch_trades()

                equity_rows: list[dict] = []
                for row in holdings:
                    quantity = float(row.get("quantity", 0) or 0)
                    average_price = float(row.get("average_price", 0) or 0)
                    last_price = float(row.get("last_price", 0) or 0)
                    invested_value = quantity * average_price
                    current_value = quantity * last_price
                    pnl = float(row.get("pnl", current_value - invested_value) or 0)

                    equity_rows.append(
                        {
                            "account": account.alias,
                            "ts": ts,
                            "tradingsymbol": row.get("tradingsymbol", ""),
                            "exchange": row.get("exchange", ""),
                            "quantity": quantity,
                            "average_price": average_price,
                            "last_price": last_price,
                            "pnl": pnl,
                            "invested_value": invested_value,
                            "current_value": current_value,
                            "source": "zerodha_holdings",
                        }
                    )

                mf_rows: list[dict] = []
                for row in mf_holdings:
                    quantity = float(row.get("quantity", 0) or 0)
                    average_price = float(row.get("average_price", 0) or 0)
                    last_price = float(row.get("last_price", row.get("last_nav", 0)) or 0)
                    invested_value = quantity * average_price
                    current_value = quantity * last_price
                    pnl = current_value - invested_value

                    mf_rows.append(
                        {
                            "account": account.alias,
                            "ts": ts,
                            "fund": row.get("fund", row.get("tradingsymbol", "Unknown Fund")),
                            "folio": row.get("folio", ""),
                            "quantity": quantity,
                            "average_price": average_price,
                            "last_price": last_price,
                            "pnl": pnl,
                            "invested_value": invested_value,
                            "current_value": current_value,
                        }
                    )

                trade_rows: list[dict] = []
                for row in trades:
                    trade_rows.append(
                        {
                            "account": account.alias,
                            "trade_id": str(row.get("trade_id", row.get("order_id", ""))),
                            "order_id": str(row.get("order_id", "")),
                            "symbol": row.get("tradingsymbol", ""),
                            "exchange": row.get("exchange", ""),
                            "quantity": float(row.get("quantity", 0) or 0),
                            "average_price": float(row.get("average_price", 0) or 0),
                            "trade_timestamp": self._parse_ts(row.get("fill_timestamp") or row.get("order_timestamp")),
                            "transaction_type": row.get("transaction_type", ""),
                            "product": row.get("product", ""),
                        }
                    )

                self.store.insert_equity_snapshot(equity_rows)
                self.store.insert_mf_snapshot(mf_rows)
                self.store.upsert_trades(trade_rows)

                message = f"Synced {len(equity_rows)} equity, {len(mf_rows)} MF, {len(trade_rows)} trades"
                self.store.insert_sync_run(account.alias, "success", message)
                status[account.alias] = message
            except Exception as exc:
                message = f"Sync failed: {exc}"
                self.store.insert_sync_run(account.alias, "failure", message)
                status[account.alias] = message

        return status
