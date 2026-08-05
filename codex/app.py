from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from zerodha_dashboard.analytics import build_equity_positions, build_family_summary, build_mf_positions
from zerodha_dashboard.config import load_config
from zerodha_dashboard.data_store import DataStore
from zerodha_dashboard.scheduler import start_scheduler
from zerodha_dashboard.sync_service import PortfolioSyncService

st.set_page_config(page_title="Zerodha Family Wealth Dashboard", page_icon="📈", layout="wide")

st.markdown(
    """
    <style>
    .main {background: linear-gradient(180deg,#081126 0%, #0b1835 100%);} 
    h1, h2, h3, p, div, span, label {color: #e6edf7 !important;}
    .stMetric {background: rgba(255,255,255,0.06); border-radius: 14px; padding: 10px;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_runtime():
    config = load_config()
    store = DataStore(config.db_path)
    sync_service = PortfolioSyncService(config, store)
    scheduler = start_scheduler(sync_service, config.sync_interval_hours)
    return config, store, sync_service, scheduler


config, store, sync_service, _scheduler = get_runtime()

st.title("📊 Zerodha Family Holdings Dashboard")
st.caption("Stocks + Mutual Funds across family accounts, with profit analytics and buying-date insights.")

if not config.accounts:
    st.error("No Zerodha accounts configured. Add credentials in .env (see .env.example), then rerun.")
    st.stop()

with st.sidebar:
    st.header("Controls")
    if st.button("Sync now", type="primary", use_container_width=True):
        results = sync_service.sync_all_accounts()
        for account, message in results.items():
            st.write(f"{account}: {message}")
        st.rerun()
    st.write(f"Auto-sync every {config.sync_interval_hours} hours")
    st.write("Configured accounts:")
    for account in config.accounts:
        st.write(f"• {account.alias}")

equity_df = store.get_latest_equity()
mf_df = store.get_latest_mf()
first_buy_df = store.get_first_buy_dates()
history_df = store.get_portfolio_history()

positions_equity = build_equity_positions(equity_df, first_buy_df)
positions_mf = build_mf_positions(mf_df)
positions = pd.concat([positions_equity, positions_mf], ignore_index=True)

summary = build_family_summary(positions)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Invested", f"₹{summary['invested']:,.0f}")
col2.metric("Current Value", f"₹{summary['current']:,.0f}")
col3.metric("Total Profit", f"₹{summary['profit']:,.0f}")
col4.metric("Profit %", f"{summary['profit_pct']:.2f}%")

if positions.empty:
    st.warning("No holdings data available yet. Click Sync now after configuring valid Zerodha tokens.")
    st.stop()

alloc = positions.groupby("asset_type", as_index=False)["current_value"].sum()
chart_alloc = px.pie(alloc, names="asset_type", values="current_value", hole=0.55, title="Asset Allocation")
chart_alloc.update_traces(textposition="inside", textinfo="percent+label")

account_perf = (
    positions.groupby("account", as_index=False)
    .agg(invested_value=("invested_value", "sum"), current_value=("current_value", "sum"), pnl=("pnl", "sum"))
)
account_perf["pnl_pct"] = (account_perf["pnl"] / account_perf["invested_value"].replace(0, pd.NA) * 100).fillna(0.0)
chart_accounts = px.bar(
    account_perf,
    x="account",
    y="pnl",
    color="pnl",
    title="Profit by Family Account",
    text=account_perf["pnl"].map(lambda x: f"₹{x:,.0f}"),
)

winners = positions.sort_values("pnl", ascending=False).head(8)
losers = positions.sort_values("pnl", ascending=True).head(8)
chart_winners = px.bar(winners, x="pnl", y="symbol", orientation="h", color="pnl", title="Top Winners")
chart_losers = px.bar(losers, x="pnl", y="symbol", orientation="h", color="pnl", title="Top Losers")

left, right = st.columns([1, 1])
left.plotly_chart(chart_alloc, use_container_width=True)
right.plotly_chart(chart_accounts, use_container_width=True)

left2, right2 = st.columns([1, 1])
left2.plotly_chart(chart_winners, use_container_width=True)
right2.plotly_chart(chart_losers, use_container_width=True)

if not history_df.empty:
    history_df["ts"] = pd.to_datetime(history_df["ts"], errors="coerce")
    history_df = history_df.sort_values("ts")
    history_df["profit"] = history_df["total_value"] - history_df["total_invested"]
    chart_history = px.line(
        history_df,
        x="ts",
        y=["total_value", "total_invested", "profit"],
        title="Portfolio Trend Across Syncs",
        markers=True,
    )
    st.plotly_chart(chart_history, use_container_width=True)

display = positions.copy()
display["first_buy_date"] = pd.to_datetime(display["first_buy_date"], errors="coerce").dt.date
for col in ["quantity", "average_price", "last_price", "invested_value", "current_value", "pnl", "pnl_pct"]:
    display[col] = pd.to_numeric(display[col], errors="coerce").fillna(0)

st.subheader("Holdings Detail")
st.dataframe(
    display.sort_values(["asset_type", "pnl"], ascending=[True, False]),
    use_container_width=True,
    hide_index=True,
)

st.subheader("Recent Sync Logs")
st.dataframe(store.get_recent_sync_runs(30), use_container_width=True, hide_index=True)
