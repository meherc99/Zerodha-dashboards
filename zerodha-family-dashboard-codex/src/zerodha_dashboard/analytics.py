from __future__ import annotations

import pandas as pd


def _ensure_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce").fillna(0.0)
    return out


def build_equity_positions(equity_df: pd.DataFrame, first_buy_df: pd.DataFrame) -> pd.DataFrame:
    if equity_df.empty:
        return pd.DataFrame(
            columns=[
                "account",
                "asset_type",
                "symbol",
                "quantity",
                "average_price",
                "last_price",
                "invested_value",
                "current_value",
                "pnl",
                "pnl_pct",
                "first_buy_date",
            ]
        )

    enriched = _ensure_numeric(
        equity_df,
        ["quantity", "average_price", "last_price", "invested_value", "current_value", "pnl"],
    ).copy()
    enriched["asset_type"] = "Stocks"
    enriched["symbol"] = enriched["tradingsymbol"]

    merged = enriched.merge(
        first_buy_df,
        left_on=["account", "symbol"],
        right_on=["account", "symbol"],
        how="left",
    )
    merged["pnl_pct"] = (merged["pnl"] / merged["invested_value"].replace(0, pd.NA) * 100).fillna(0.0)
    return merged[
        [
            "account",
            "asset_type",
            "symbol",
            "quantity",
            "average_price",
            "last_price",
            "invested_value",
            "current_value",
            "pnl",
            "pnl_pct",
            "first_buy_date",
        ]
    ]


def build_mf_positions(mf_df: pd.DataFrame) -> pd.DataFrame:
    if mf_df.empty:
        return pd.DataFrame(
            columns=[
                "account",
                "asset_type",
                "symbol",
                "quantity",
                "average_price",
                "last_price",
                "invested_value",
                "current_value",
                "pnl",
                "pnl_pct",
                "first_buy_date",
            ]
        )

    enriched = _ensure_numeric(
        mf_df,
        ["quantity", "average_price", "last_price", "invested_value", "current_value", "pnl"],
    ).copy()
    enriched["asset_type"] = "Mutual Funds"
    enriched["symbol"] = enriched["fund"]
    enriched["first_buy_date"] = pd.NA
    enriched["pnl_pct"] = (enriched["pnl"] / enriched["invested_value"].replace(0, pd.NA) * 100).fillna(0.0)

    return enriched[
        [
            "account",
            "asset_type",
            "symbol",
            "quantity",
            "average_price",
            "last_price",
            "invested_value",
            "current_value",
            "pnl",
            "pnl_pct",
            "first_buy_date",
        ]
    ]


def build_family_summary(positions_df: pd.DataFrame) -> dict[str, float]:
    if positions_df.empty:
        return {
            "invested": 0.0,
            "current": 0.0,
            "profit": 0.0,
            "profit_pct": 0.0,
        }

    invested = float(positions_df["invested_value"].sum())
    current = float(positions_df["current_value"].sum())
    profit = float(positions_df["pnl"].sum())
    profit_pct = (profit / invested * 100.0) if invested else 0.0
    return {
        "invested": invested,
        "current": current,
        "profit": profit,
        "profit_pct": profit_pct,
    }
