from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class AccountConfig:
    alias: str
    api_key: str
    api_secret: str
    access_token: str


@dataclass(frozen=True)
class AppConfig:
    accounts: list[AccountConfig]
    db_path: Path
    sync_interval_hours: int


def _sanitize_alias(alias: str) -> str:
    return alias.strip().replace(" ", "_").upper()


def load_config() -> AppConfig:
    load_dotenv()
    aliases_raw = os.getenv("ACCOUNT_ALIASES", "").strip()
    aliases = [a.strip() for a in aliases_raw.split(",") if a.strip()]

    accounts: list[AccountConfig] = []
    for alias in aliases:
        prefix = _sanitize_alias(alias)
        api_key = os.getenv(f"{prefix}_API_KEY", "").strip()
        api_secret = os.getenv(f"{prefix}_API_SECRET", "").strip()
        access_token = os.getenv(f"{prefix}_ACCESS_TOKEN", "").strip()
        if api_key and api_secret and access_token:
            accounts.append(
                AccountConfig(
                    alias=alias,
                    api_key=api_key,
                    api_secret=api_secret,
                    access_token=access_token,
                )
            )

    db_path = Path(os.getenv("DB_PATH", "data/portfolio.db")).expanduser()
    sync_interval_hours = int(os.getenv("SYNC_INTERVAL_HOURS", "12"))
    return AppConfig(accounts=accounts, db_path=db_path, sync_interval_hours=sync_interval_hours)
