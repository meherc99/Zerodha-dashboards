# Zerodha Family Wealth Dashboard

A web-based Streamlit dashboard for analyzing family-level stocks and mutual fund holdings from Zerodha (Kite Connect API).

## What you get

- Family-wide summary: invested amount, current value, profit, profit %
- Combined view across stocks and mutual funds
- Account-wise profit comparison
- Asset allocation chart
- Top winners and losers
- Historical trend across sync snapshots
- First buy date for stocks (derived from trade history)
- Background auto-sync every 12 hours (configurable)

## Project structure

- `app.py` - Streamlit web app
- `src/zerodha_dashboard/config.py` - environment config loader
- `src/zerodha_dashboard/zerodha_client.py` - Zerodha API wrappers
- `src/zerodha_dashboard/sync_service.py` - sync orchestration
- `src/zerodha_dashboard/data_store.py` - SQLite persistence
- `src/zerodha_dashboard/analytics.py` - portfolio calculations
- `src/zerodha_dashboard/scheduler.py` - 12-hour scheduler

## Setup

1. Create a virtual environment and install dependencies:

```bash
cd ~/zerodha-family-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy env template and add credentials:

```bash
cp .env.example .env
```

3. Fill `.env`:

- Add `ACCOUNT_ALIASES`, for example `Self,Spouse,Parents`
- For each alias, fill:
  - `<ALIAS>_API_KEY`
  - `<ALIAS>_API_SECRET`
  - `<ALIAS>_ACCESS_TOKEN`

Alias mapping example:
- `Self` -> `SELF_API_KEY`, `SELF_API_SECRET`, `SELF_ACCESS_TOKEN`
- `Parents` -> `PARENTS_API_KEY`, `PARENTS_API_SECRET`, `PARENTS_ACCESS_TOKEN`

4. Run the dashboard:

```bash
streamlit run app.py
```

## Zerodha auth note

Kite `access_token` generally expires daily. Auto-sync every 12 hours works while token is valid. Update tokens in `.env` whenever they expire, then rerun the app.

## Sync behavior

- Manual sync via **Sync now** button
- Automatic sync runs every `SYNC_INTERVAL_HOURS` (default 12)
- Data is stored in SQLite at `data/portfolio.db`

## Future investment decision support

Use these sections to guide decisions:
- **Account-wise P&L**: compare who is outperforming
- **Asset allocation**: identify concentration risk
- **Top losers**: review weak positions and thesis
- **Trend chart**: monitor trajectory over time
- **First buy date**: evaluate holding period and timing
