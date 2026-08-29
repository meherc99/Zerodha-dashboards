from __future__ import annotations

import sys
import time
import threading
import webbrowser
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
for _p in (str(SRC), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from zerodha_dashboard.analytics import build_equity_positions, build_family_summary, build_mf_positions
from zerodha_dashboard.config import load_config
from zerodha_dashboard.data_store import DataStore
from zerodha_dashboard.scheduler import start_scheduler
from zerodha_dashboard.sync_service import PortfolioSyncService
from get_access_token import (
    CallbackState,
    KiteCallbackHandler,
    load_account_credentials,
    upsert_env_var,
)
from http.server import HTTPServer
from kiteconnect import KiteConnect

ENV_PATH = ROOT / ".env"

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
    config = load_config(ENV_PATH)
    store = DataStore(config.db_path)
    sync_service = PortfolioSyncService(config, store)
    scheduler = start_scheduler(sync_service, config.sync_interval_hours)
    return config, store, sync_service, scheduler


config, store, sync_service, _scheduler = get_runtime()

# ── OAuth2 token refresh helpers ──────────────────────────────────────────────

_OAUTH_PORT = 8765
_OAUTH_CALLBACK_PATH = "/callback"
_OAUTH_TIMEOUT = 180

_OAUTH_STATE_KEY = "_kite_oauth_state"


def _start_oauth_flow(alias: str) -> dict:
    """Start OAuth2 flow: spin up callback server in background thread, return login_url."""
    creds = load_account_credentials(ENV_PATH, alias)
    kite = KiteConnect(api_key=creds.api_key)
    login_url = kite.login_url()

    state = CallbackState()
    handler_class = type(
        "_DynamicKiteCallbackHandler",
        (KiteCallbackHandler,),
        {"state": state, "callback_path": _OAUTH_CALLBACK_PATH},
    )
    server = HTTPServer(("127.0.0.1", _OAUTH_PORT), handler_class)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    return {
        "alias": alias,
        "creds": creds,
        "kite": kite,
        "login_url": login_url,
        "state": state,
        "server": server,
        "started_at": time.time(),
    }


def _poll_oauth_state() -> None:
    """Check if OAuth callback has been received; if so, exchange token and save."""
    flow = st.session_state.get(_OAUTH_STATE_KEY)
    if not flow:
        return

    state: object = flow["state"]
    elapsed = time.time() - flow["started_at"]

    if not state.event.is_set():
        if elapsed > _OAUTH_TIMEOUT:
            flow["server"].shutdown()
            st.session_state.pop(_OAUTH_STATE_KEY, None)
            st.error(f"OAuth2 login timed out after {_OAUTH_TIMEOUT}s. Please try again.")
        return

    # Callback received — shut down local server
    flow["server"].shutdown()

    if state.error:
        st.session_state.pop(_OAUTH_STATE_KEY, None)
        st.error(f"Kite OAuth error: {state.error}")
        return

    if not state.request_token:
        st.session_state.pop(_OAUTH_STATE_KEY, None)
        st.error("Kite callback did not return a request_token.")
        return

    try:
        kite: KiteConnect = flow["kite"]
        creds = flow["creds"]
        session = kite.generate_session(state.request_token, api_secret=creds.api_secret)
        access_token = (session.get("access_token") or "").strip()
        if not access_token:
            raise ValueError("Empty access_token in Kite session response.")
        upsert_env_var(ENV_PATH, f"{creds.prefix}_ACCESS_TOKEN", access_token)
        upsert_env_var(ENV_PATH, f"{creds.prefix}_LAST_TOKEN_REFRESH_TS", str(int(time.time())))
        st.session_state.pop(_OAUTH_STATE_KEY, None)
        st.session_state["_oauth_success"] = creds.alias
        get_runtime.clear()  # clear cached config so new token is picked up
    except Exception as exc:
        st.session_state.pop(_OAUTH_STATE_KEY, None)
        st.error(f"Failed to exchange token: {exc}")


# Poll on every rerun while an OAuth flow is in progress
_poll_oauth_state()

# ─────────────────────────────────────────────────────────────────────────────

st.title("📊 Zerodha Family Holdings Dashboard")
st.caption("Stocks + Mutual Funds across family accounts, with profit analytics and buying-date insights.")

if not config.all_aliases and not st.session_state.get(_OAUTH_STATE_KEY):
    st.error("No Zerodha accounts configured. Add credentials in .env (see .env.example), then rerun.")

with st.sidebar:
    st.header("Controls")
    if st.button("Sync now", type="primary", use_container_width=True):
        results = sync_service.sync_all_accounts()
        for account, message in results.items():
            st.write(f"{account}: {message}")
        st.rerun()
    st.write(f"Auto-sync every {config.sync_interval_hours} hours")

    if config.accounts:
        st.write("Configured accounts:")
        for account in config.accounts:
            st.write(f"• {account.alias}")

    st.divider()
    st.subheader("🔑 Kite OAuth2 Login")

    # Success banner
    success_alias = st.session_state.pop("_oauth_success", None)
    if success_alias:
        st.success(f"✅ Token refreshed for **{success_alias}**. Resyncing...")

    active_flow = st.session_state.get(_OAUTH_STATE_KEY)

    if active_flow:
        alias = active_flow["alias"]
        login_url = active_flow["login_url"]
        elapsed = int(time.time() - active_flow["started_at"])
        remaining = max(0, _OAUTH_TIMEOUT - elapsed)

        st.info(f"Waiting for Kite login — {remaining}s remaining")
        st.markdown(
            f"[🔗 Open Kite Login]({login_url})",
            unsafe_allow_html=False,
        )
        st.caption(
            f"Redirect URL must be set to `http://127.0.0.1:{_OAUTH_PORT}{_OAUTH_CALLBACK_PATH}` in your Kite app."
        )
        if st.button("Cancel", use_container_width=True):
            active_flow["server"].shutdown()
            st.session_state.pop(_OAUTH_STATE_KEY, None)
            st.rerun()
        # Auto-refresh every 2 seconds while waiting
        time.sleep(2)
        st.rerun()
    else:
        aliases_raw = []
        # Show all configured aliases (api_key + api_secret), even without a token yet
        if config.all_aliases:
            aliases_raw = config.all_aliases
        else:
            st.caption("No accounts in config yet. Enter alias below once .env has API_KEY + API_SECRET.")

        alias_choice = st.selectbox("Account alias", options=aliases_raw, key="_oauth_alias") if aliases_raw else None
        manual_alias = st.text_input("Or enter alias manually", key="_oauth_manual_alias")
        chosen_alias = (manual_alias.strip() or alias_choice or "").strip()

        if chosen_alias and st.button("Start OAuth2 Login", type="secondary", use_container_width=True):
            try:
                flow = _start_oauth_flow(chosen_alias)
                st.session_state[_OAUTH_STATE_KEY] = flow
                webbrowser.open(flow["login_url"])
                st.rerun()
            except Exception as exc:
                st.error(f"Could not start OAuth2 flow: {exc}")

        st.divider()
        st.caption("Already have a request_token? Paste it below to exchange directly.")
        manual_request_token = st.text_input("Request token", key="_manual_request_token", placeholder="paste request_token here")
        if chosen_alias and manual_request_token.strip() and st.button("Exchange request_token", use_container_width=True):
            try:
                creds = load_account_credentials(ENV_PATH, chosen_alias)
                kite = KiteConnect(api_key=creds.api_key)
                session = kite.generate_session(manual_request_token.strip(), api_secret=creds.api_secret)
                access_token = (session.get("access_token") or "").strip()
                if not access_token:
                    st.error("Kite did not return an access_token.")
                else:
                    upsert_env_var(ENV_PATH, f"{creds.prefix}_ACCESS_TOKEN", access_token)
                    upsert_env_var(ENV_PATH, f"{creds.prefix}_LAST_TOKEN_REFRESH_TS", str(int(time.time())))
                    st.session_state["_oauth_success"] = creds.alias
                    get_runtime.clear()
                    st.rerun()
            except Exception as exc:
                st.error(f"Failed to exchange request_token: {exc}")

if not config.accounts:
    st.stop()

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
