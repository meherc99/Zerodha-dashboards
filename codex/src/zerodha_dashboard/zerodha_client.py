from __future__ import annotations

from kiteconnect import KiteConnect

from .config import AccountConfig


class ZerodhaClient:
    def __init__(self, account: AccountConfig) -> None:
        self.account = account
        self.client = KiteConnect(api_key=account.api_key)
        self.client.set_access_token(account.access_token)

    def fetch_holdings(self) -> list[dict]:
        return self.client.holdings()

    def fetch_mf_holdings(self) -> list[dict]:
        try:
            return self.client.mf_holdings()
        except Exception:
            return []

    def fetch_trades(self) -> list[dict]:
        try:
            return self.client.trades()
        except Exception:
            return []

    def fetch_margins(self) -> dict:
        try:
            return self.client.margins(segment="equity")
        except Exception:
            return {}
