"""
Zerodha Portfolio Dashboard — Flask Application
Beautiful dashboard for analyzing stock & mutual fund holdings.
"""

import json
import os
import logging
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for

import config
from data_fetcher import fetch_all_data, load_cached_data, generate_demo_data

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY

# Global state
_cached_data = None
_last_refresh = None


def get_portfolio_data():
    """Get portfolio data, using cache or fetching fresh data."""
    global _cached_data, _last_refresh

    # Try loading from disk cache first
    if _cached_data is None:
        _cached_data = load_cached_data()
        if _cached_data:
            _last_refresh = datetime.fromisoformat(_cached_data["fetched_at"])

    # Check if we have valid API credentials
    has_credentials = any(
        m.get("access_token") and m["access_token"] != ""
        for m in config.FAMILY_MEMBERS
    )

    if has_credentials:
        # Check if refresh needed
        if _cached_data is None or _last_refresh is None or \
           (datetime.now() - _last_refresh) > timedelta(hours=config.REFRESH_INTERVAL_HOURS):
            try:
                _cached_data = fetch_all_data()
                _last_refresh = datetime.now()
            except Exception as e:
                logger.error(f"Error refreshing data: {e}")
                if _cached_data is None:
                    _cached_data = generate_demo_data()
    else:
        # Use demo data if no credentials
        if _cached_data is None:
            _cached_data = generate_demo_data()
            # Save demo data
            data_file = os.path.join(config.DATA_DIR, "portfolio_data.json")
            with open(data_file, "w") as f:
                json.dump(_cached_data, f, indent=2, default=str)

    return _cached_data


def compute_analytics(data):
    """Compute summary analytics from portfolio data."""
    if not data or "members" not in data:
        return {}

    total_invested = 0
    total_current = 0
    total_pnl = 0
    total_day_change = 0
    all_holdings = []
    member_summaries = []

    for member in data["members"]:
        m_invested = 0
        m_current = 0
        m_pnl = 0
        m_day_change = 0

        for h in member.get("holdings", []):
            invested = h.get("invested_value", 0)
            current = h.get("current_value", 0)
            pnl = h.get("profit", 0)
            day_chg = h.get("day_change", 0) * h.get("quantity", 0)

            m_invested += invested
            m_current += current
            m_pnl += pnl
            m_day_change += day_chg

            h_copy = dict(h)
            h_copy["member"] = member.get("name", "Unknown")
            all_holdings.append(h_copy)

        total_invested += m_invested
        total_current += m_current
        total_pnl += m_pnl
        total_day_change += m_day_change

        member_summaries.append({
            "name": member.get("name", "Unknown"),
            "user_name": member.get("profile", {}).get("user_name", member.get("name", "")),
            "invested": round(m_invested, 2),
            "current": round(m_current, 2),
            "pnl": round(m_pnl, 2),
            "pnl_pct": round((m_pnl / m_invested * 100) if m_invested > 0 else 0, 2),
            "day_change": round(m_day_change, 2),
            "holdings_count": len(member.get("holdings", [])),
        })

    # Sector allocation (by stock grouping)
    sector_map = {
        "RELIANCE": "Energy", "ONGC": "Energy", "BPCL": "Energy", "IOC": "Energy",
        "POWERGRID": "Energy", "NTPC": "Energy", "ADANIGREEN": "Energy",
        "TCS": "IT", "INFY": "IT", "WIPRO": "IT", "HCLTECH": "IT", "TECHM": "IT",
        "HDFCBANK": "Banking", "ICICIBANK": "Banking", "SBIN": "Banking",
        "KOTAKBANK": "Banking", "AXISBANK": "Banking", "BANKBEES": "Banking",
        "HINDUNILVR": "FMCG", "ITC": "FMCG", "NESTLEIND": "FMCG",
        "BHARTIARTL": "Telecom", "IDEA": "Telecom",
        "MARUTI": "Auto", "TATAMOTORS": "Auto", "BAJAJ-AUTO": "Auto",
        "SUNPHARMA": "Pharma", "DRREDDY": "Pharma", "CIPLA": "Pharma",
        "BAJFINANCE": "Finance", "BAJAJFINSV": "Finance",
        "TITAN": "Consumer", "ASIANPAINT": "Consumer",
        "LT": "Infra", "ULTRACEMCO": "Infra",
        "NIFTYBEES": "Index ETF", "JUNIORBEES": "Index ETF",
        "GOLDBEES": "Gold ETF", "LIQUIDBEES": "Debt ETF",
    }

    sector_allocation = {}
    for h in all_holdings:
        sym = h.get("tradingsymbol", "")
        sector = sector_map.get(sym, "Others")
        if sector not in sector_allocation:
            sector_allocation[sector] = 0
        sector_allocation[sector] += h.get("current_value", 0)

    # Top gainers/losers
    sorted_by_pnl_pct = sorted(all_holdings, key=lambda x: x.get("profit_pct", 0), reverse=True)
    top_gainers = sorted_by_pnl_pct[:5]
    top_losers = sorted_by_pnl_pct[-5:][::-1]

    # Holdings by exchange
    exchange_split = {}
    for h in all_holdings:
        ex = h.get("exchange", "NSE")
        exchange_split[ex] = exchange_split.get(ex, 0) + h.get("current_value", 0)

    # Compute FD totals for net worth
    fds = data.get("fixed_deposits", [])
    fd_total_principal = 0
    fd_total_current = 0
    fd_member_totals = {}
    for fd in fds:
        principal = fd.get("principal", 0)
        inv_date_str = fd.get("investment_date", "")
        rate = fd.get("interest_rate", 0)
        comp = fd.get("compounding", "quarterly")
        member = fd.get("member", "Unknown")
        if inv_date_str:
            inv_date = datetime.strptime(inv_date_str, "%Y-%m-%d")
            days_elapsed = (datetime.now() - inv_date).days
            years_elapsed = days_elapsed / 365.25
            n = {"quarterly": 4, "monthly": 12, "half-yearly": 2}.get(comp, 1)
            current_val = principal * ((1 + (rate / 100) / n) ** (n * years_elapsed))
        else:
            current_val = principal
        fd_total_principal += principal
        fd_total_current += current_val
        if member not in fd_member_totals:
            fd_member_totals[member] = {"principal": 0, "current": 0}
        fd_member_totals[member]["principal"] += principal
        fd_member_totals[member]["current"] += current_val

    # Add FD values to member summaries
    for ms in member_summaries:
        fd_m = fd_member_totals.get(ms["name"], {"principal": 0, "current": 0})
        ms["fd_principal"] = round(fd_m["principal"], 2)
        ms["fd_current"] = round(fd_m["current"], 2)
        ms["net_worth"] = round(ms["current"] + fd_m["current"], 2)

    # Net worth = stocks/MFs current + FD current
    net_worth = total_current + fd_total_current

    return {
        "total_invested": round(total_invested, 2),
        "total_current": round(total_current, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round((total_pnl / total_invested * 100) if total_invested > 0 else 0, 2),
        "total_day_change": round(total_day_change, 2),
        "total_day_change_pct": round((total_day_change / total_current * 100) if total_current > 0 else 0, 2),
        "fd_total_principal": round(fd_total_principal, 2),
        "fd_total_current": round(fd_total_current, 2),
        "net_worth": round(net_worth, 2),
        "member_summaries": member_summaries,
        "member_names": [m.get("name", "Unknown") for m in data.get("members", [])],
        "all_holdings": sorted(all_holdings, key=lambda x: x.get("current_value", 0), reverse=True),
        "sector_allocation": sector_allocation,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "exchange_split": exchange_split,
        "holdings_count": len(all_holdings),
        "fetched_at": data.get("fetched_at", ""),
        "next_refresh": data.get("next_refresh", ""),
        "is_demo": data.get("is_demo", False),
    }


# --- Scheduled Refresh ---
def scheduled_refresh():
    """Background thread to refresh data every REFRESH_INTERVAL_HOURS."""
    while True:
        time.sleep(config.REFRESH_INTERVAL_HOURS * 3600)
        logger.info("Scheduled refresh triggered...")
        try:
            global _cached_data, _last_refresh
            _cached_data = fetch_all_data()
            _last_refresh = datetime.now()
            logger.info("Scheduled refresh completed.")
        except Exception as e:
            logger.error(f"Scheduled refresh failed: {e}")


# --- Routes ---
@app.route("/")
def index():
    """Main dashboard page."""
    return render_template("dashboard.html")


@app.route("/mutual-funds")
def mutual_funds_page():
    """Dedicated mutual funds view."""
    return render_template("mutual_funds.html")


@app.route("/fixed-deposits")
def fixed_deposits_page():
    """Dedicated fixed deposits view."""
    return render_template("fixed_deposits.html")


@app.route("/api/portfolio")
def api_portfolio():
    """API endpoint returning full portfolio data with analytics."""
    data = get_portfolio_data()
    analytics = compute_analytics(data)
    return jsonify(analytics)


@app.route("/api/mutual-funds")
def api_mutual_funds():
    """API endpoint returning mutual fund holdings with per-purchase drill-down."""
    data = get_portfolio_data()
    if not data or "members" not in data:
        return jsonify({"funds": []})

    # Known MF/ETF symbols (expand as needed)
    MF_SYMBOLS = {"NIFTYBEES", "JUNIORBEES", "GOLDBEES", "BANKBEES", "LIQUIDBEES",
                  "SETFNIF50", "ICICIMCAP", "MOTILALNIFTY", "HABORNNIFTY",
                  "MOM100", "ITBEES", "PSUBNKBEES", "INFRABEES", "CPSEETF",
                  "SILVERBEES", "MOM50", "SHARIABEES", "CONSUMBEES",
                  "PHARMABEES", "MAN50ETF", "MON100", "NIF100BEES"}

    # Also detect by suffix pattern
    def is_mf(symbol):
        s = symbol.upper()
        return (s in MF_SYMBOLS or
                s.endswith("BEES") or
                s.endswith("ETF") or
                s.startswith("MOTILAL") or
                s.startswith("ICICI"))

    # Forecasted 2Y CAGR benchmarks (from Zerodha Coin / analyst consensus)
    # In production, these come from kite.mf_instruments() scheme metadata or
    # Zerodha's Coin API historical category returns extrapolated forward.
    FORECASTED_CAGR_2Y = {
        "NIFTYBEES": 13.5,    # Nifty 50 ETF — long-term equity ~12-15%
        "JUNIORBEES": 14.8,   # Nifty Next 50 — slightly higher growth
        "GOLDBEES": 9.2,      # Gold ETF — moderate, inflation hedge
        "BANKBEES": 12.0,     # Bank Nifty ETF — banking sector growth
        "LIQUIDBEES": 6.8,    # Liquid fund — near risk-free rate
        "SETFNIF50": 13.5,
        "ITBEES": 15.2,
        "PSUBNKBEES": 11.5,
        "INFRABEES": 14.0,
        "CPSEETF": 12.5,
        "SILVERBEES": 8.5,
        "PHARMABEES": 13.8,
        "NIF100BEES": 13.2,
        "CONSUMBEES": 14.5,
    }

    # Collect all MF holdings across members
    mf_map = {}  # symbol -> aggregated fund info
    for member in data["members"]:
        member_name = member.get("name", "Unknown")
        user_name = member.get("profile", {}).get("user_name", member_name)
        for h in member.get("holdings", []):
            sym = h.get("tradingsymbol", "")
            if not (h.get("is_mutual_fund") or is_mf(sym)):
                continue
            if sym not in mf_map:
                mf_map[sym] = {
                    "tradingsymbol": sym,
                    "exchange": h.get("exchange", "NSE"),
                    "last_price": h.get("last_price", 0),
                    "day_change_percentage": h.get("day_change_percentage", 0),
                    "week_52_high": h.get("week_52_high", 0),
                    "week_52_low": h.get("week_52_low", 0),
                    "total_quantity": 0,
                    "total_invested": 0,
                    "total_current": 0,
                    "total_profit": 0,
                    "members": {},
                    "purchases": [],
                }
            fund = mf_map[sym]
            qty = h.get("quantity", 0)
            invested = h.get("invested_value", 0)
            current = h.get("current_value", 0)
            profit = h.get("profit", 0)
            fund["total_quantity"] += qty
            fund["total_invested"] += invested
            fund["total_current"] += current
            fund["total_profit"] += profit

            if member_name not in fund["members"]:
                fund["members"][member_name] = {
                    "member": member_name,
                    "user_name": user_name,
                    "quantity": 0,
                    "invested": 0,
                    "current": 0,
                    "profit": 0,
                    "average_price": h.get("average_price", 0),
                }
            m = fund["members"][member_name]
            m["quantity"] += qty
            m["invested"] += invested
            m["current"] += current
            m["profit"] += profit

    # Add purchase tranches from demo data
    mf_purchases = data.get("mf_purchases", {})
    for sym, purchases in mf_purchases.items():
        if sym in mf_map:
            ltp = mf_map[sym]["last_price"]
            for p in purchases:
                current_val = p["qty"] * ltp
                invested_val = p["qty"] * p["price"]
                profit = current_val - invested_val
                profit_pct = (profit / invested_val * 100) if invested_val > 0 else 0
                days_held = (datetime.now() - datetime.strptime(p["date"], "%Y-%m-%d")).days
                annual_return = (profit_pct / days_held * 365) if days_held > 0 else 0
                # CAGR = (ending/beginning)^(1/years) - 1
                years_held = days_held / 365.25 if days_held > 0 else 0
                if invested_val > 0 and years_held > 0:
                    cagr_2y = ((current_val / invested_val) ** (1 / min(years_held, 2)) - 1) * 100
                else:
                    cagr_2y = 0
                mf_map[sym]["purchases"].append({
                    "date": p["date"],
                    "member": p["member"],
                    "quantity": p["qty"],
                    "purchase_price": round(p["price"], 2),
                    "current_price": round(ltp, 2),
                    "invested": round(invested_val, 2),
                    "current_value": round(current_val, 2),
                    "profit": round(profit, 2),
                    "profit_pct": round(profit_pct, 2),
                    "days_held": days_held,
                    "annualized_return": round(annual_return, 2),
                    "cagr_2y": round(cagr_2y, 2),
                })
            # Sort purchases by date
            mf_map[sym]["purchases"].sort(key=lambda x: x["date"])

    # Finalize
    funds = []
    for sym, fund in mf_map.items():
        fund["total_invested"] = round(fund["total_invested"], 2)
        fund["total_current"] = round(fund["total_current"], 2)
        fund["total_profit"] = round(fund["total_profit"], 2)
        fund["profit_pct"] = round(
            (fund["total_profit"] / fund["total_invested"] * 100)
            if fund["total_invested"] > 0 else 0, 2
        )
        # Compute fund-level 2Y CAGR from weighted average of purchase CAGRs
        if fund["purchases"]:
            total_inv_w = sum(p["invested"] for p in fund["purchases"])
            if total_inv_w > 0:
                fund["cagr_2y"] = round(
                    sum(p["cagr_2y"] * p["invested"] for p in fund["purchases"]) / total_inv_w, 2
                )
            else:
                fund["cagr_2y"] = 0
        else:
            # Fallback: compute from total invested/current assuming 2 year horizon
            if fund["total_invested"] > 0:
                fund["cagr_2y"] = round(
                    ((fund["total_current"] / fund["total_invested"]) ** 0.5 - 1) * 100, 2
                )
            else:
                fund["cagr_2y"] = 0
        # Forecasted 2Y CAGR from Zerodha/analyst consensus benchmarks
        fund["forecasted_cagr_2y"] = FORECASTED_CAGR_2Y.get(sym, None)
        fund["members"] = list(fund["members"].values())
        for m in fund["members"]:
            m["invested"] = round(m["invested"], 2)
            m["current"] = round(m["current"], 2)
            m["profit"] = round(m["profit"], 2)
            m["profit_pct"] = round(
                (m["profit"] / m["invested"] * 100) if m["invested"] > 0 else 0, 2
            )
        funds.append(fund)

    funds.sort(key=lambda x: x["total_current"], reverse=True)

    # Summary
    total_invested = sum(f["total_invested"] for f in funds)
    total_current = sum(f["total_current"] for f in funds)
    total_profit = total_current - total_invested

    return jsonify({
        "funds": funds,
        "summary": {
            "total_funds": len(funds),
            "total_invested": round(total_invested, 2),
            "total_current": round(total_current, 2),
            "total_profit": round(total_profit, 2),
            "total_profit_pct": round((total_profit / total_invested * 100) if total_invested > 0 else 0, 2),
        },
        "is_demo": data.get("is_demo", False),
    })

@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """Force refresh portfolio data."""
    global _cached_data, _last_refresh
    try:
        has_credentials = any(
            m.get("access_token") and m["access_token"] != ""
            for m in config.FAMILY_MEMBERS
        )
        if has_credentials:
            _cached_data = fetch_all_data()
        else:
            _cached_data = generate_demo_data()

        _last_refresh = datetime.now()
        data_file = os.path.join(config.DATA_DIR, "portfolio_data.json")
        with open(data_file, "w") as f:
            json.dump(_cached_data, f, indent=2, default=str)

        return jsonify({"status": "ok", "message": "Data refreshed successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def compute_fd_current_value(principal, annual_rate, compounding, investment_date_str):
    """Compute current value of an FD using compound interest."""
    inv_date = datetime.strptime(investment_date_str, "%Y-%m-%d")
    now = datetime.now()
    days_elapsed = (now - inv_date).days
    years_elapsed = days_elapsed / 365.25

    if compounding == "quarterly":
        n = 4
    elif compounding == "monthly":
        n = 12
    elif compounding == "half-yearly":
        n = 2
    else:  # yearly
        n = 1

    # A = P * (1 + r/n)^(n*t)
    current_value = principal * ((1 + (annual_rate / 100) / n) ** (n * years_elapsed))
    return round(current_value, 2), days_elapsed


def compute_fd_maturity_value(principal, annual_rate, compounding, tenure_months):
    """Compute maturity value of an FD."""
    years = tenure_months / 12

    if compounding == "quarterly":
        n = 4
    elif compounding == "monthly":
        n = 12
    elif compounding == "half-yearly":
        n = 2
    else:
        n = 1

    maturity_value = principal * ((1 + (annual_rate / 100) / n) ** (n * years))
    return round(maturity_value, 2)


@app.route("/api/fixed-deposits")
def api_fixed_deposits():
    """API endpoint returning fixed deposit investments with computed values."""
    data = get_portfolio_data()
    if not data:
        return jsonify({"deposits": [], "summary": {}})

    fds = data.get("fixed_deposits", [])
    now = datetime.now()

    deposits = []
    for fd in fds:
        current_value, days_elapsed = compute_fd_current_value(
            fd["principal"], fd["interest_rate"], fd.get("compounding", "quarterly"), fd["investment_date"]
        )
        maturity_value = compute_fd_maturity_value(
            fd["principal"], fd["interest_rate"], fd.get("compounding", "quarterly"), fd["tenure_months"]
        )

        maturity_date = datetime.strptime(fd["maturity_date"], "%Y-%m-%d")
        days_to_maturity = max((maturity_date - now).days, 0)
        is_matured = days_to_maturity == 0

        interest_earned = current_value - fd["principal"]
        total_interest_at_maturity = maturity_value - fd["principal"]
        progress_pct = min((days_elapsed / (fd["tenure_months"] * 30.44)) * 100, 100)

        deposits.append({
            "id": fd.get("id", ""),
            "bank": fd["bank"],
            "scheme": fd.get("scheme", fd["bank"] + " FD"),
            "principal": fd["principal"],
            "interest_rate": fd["interest_rate"],
            "compounding": fd.get("compounding", "quarterly"),
            "investment_date": fd["investment_date"],
            "maturity_date": fd["maturity_date"],
            "tenure_months": fd["tenure_months"],
            "member": fd["member"],
            "current_value": current_value,
            "maturity_value": maturity_value,
            "interest_earned": round(interest_earned, 2),
            "total_interest_at_maturity": round(total_interest_at_maturity, 2),
            "days_elapsed": days_elapsed,
            "days_to_maturity": days_to_maturity,
            "is_matured": is_matured,
            "progress_pct": round(progress_pct, 1),
        })

    # Summary
    total_principal = sum(d["principal"] for d in deposits)
    total_current = sum(d["current_value"] for d in deposits)
    total_maturity = sum(d["maturity_value"] for d in deposits)
    total_interest = total_current - total_principal

    # Per-member summary
    member_fd_summary = {}
    for d in deposits:
        m = d["member"]
        if m not in member_fd_summary:
            member_fd_summary[m] = {"principal": 0, "current_value": 0, "count": 0}
        member_fd_summary[m]["principal"] += d["principal"]
        member_fd_summary[m]["current_value"] += d["current_value"]
        member_fd_summary[m]["count"] += 1

    return jsonify({
        "deposits": sorted(deposits, key=lambda x: x["current_value"], reverse=True),
        "summary": {
            "total_deposits": len(deposits),
            "total_principal": round(total_principal, 2),
            "total_current": round(total_current, 2),
            "total_maturity": round(total_maturity, 2),
            "total_interest": round(total_interest, 2),
            "interest_pct": round((total_interest / total_principal * 100) if total_principal > 0 else 0, 2),
        },
        "member_summary": {k: {**v, "principal": round(v["principal"], 2), "current_value": round(v["current_value"], 2)} for k, v in member_fd_summary.items()},
        "is_demo": data.get("is_demo", False),
    })


@app.route("/api/holdings/<member_name>")
def api_member_holdings(member_name):
    """Get holdings for a specific family member."""
    data = get_portfolio_data()
    if data and "members" in data:
        for member in data["members"]:
            if member.get("name", "").lower() == member_name.lower():
                return jsonify(member)
    return jsonify({"error": "Member not found"}), 404


# --- Auth Routes for Kite Login ---
@app.route("/login")
def login():
    """Redirect to Kite login."""
    login_url = f"https://kite.zerodha.com/connect/login?v=3&api_key={config.KITE_API_KEY}"
    return redirect(login_url)


@app.route("/callback")
def callback():
    """Handle Kite login callback."""
    request_token = request.args.get("request_token")
    if request_token:
        try:
            from kiteconnect import KiteConnect
            kite = KiteConnect(api_key=config.KITE_API_KEY)
            data = kite.generate_session(request_token, api_secret=config.KITE_API_SECRET)
            access_token = data["access_token"]
            # Update config
            config.FAMILY_MEMBERS[0]["access_token"] = access_token
            logger.info(f"Login successful. Access token obtained.")
            return redirect(url_for("index"))
        except Exception as e:
            return f"Login failed: {e}", 400
    return "No request token received", 400


if __name__ == "__main__":
    # Start background refresh thread
    refresh_thread = threading.Thread(target=scheduled_refresh, daemon=True)
    refresh_thread.start()
    logger.info(f"Starting Zerodha Dashboard on port {config.PORT}...")
    logger.info(f"Open http://localhost:{config.PORT} in your browser")
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG, use_reloader=False)
