"""
Zerodha Data Fetcher — Uses KiteConnect Python API to fetch holdings,
positions, and portfolio data for all family members.
"""

import json
import os
import time
import logging
from datetime import datetime, timedelta
from kiteconnect import KiteConnect

import config

logger = logging.getLogger(__name__)

os.makedirs(config.DATA_DIR, exist_ok=True)


def get_kite_client(api_key, access_token):
    """Create a KiteConnect client instance."""
    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)
    return kite


def fetch_member_data(member):
    """Fetch all portfolio data for a single family member."""
    name = member["name"]
    logger.info(f"Fetching data for {name}...")

    try:
        kite = get_kite_client(member["api_key"], member["access_token"])

        # Profile
        profile = kite.profile()

        # Holdings (long-term stocks/MFs)
        holdings = kite.holdings()

        # Positions (intraday + overnight)
        positions = kite.positions()

        # Get instruments for enrichment
        # We'll fetch quotes for all holding trading symbols to get live prices
        trading_symbols = []
        for h in holdings:
            symbol = h.get("tradingsymbol", "")
            exchange = h.get("exchange", "NSE")
            trading_symbols.append(f"{exchange}:{symbol}")

        quotes = {}
        if trading_symbols:
            # Kite API allows max ~500 instruments per call
            batch_size = 200
            for i in range(0, len(trading_symbols), batch_size):
                batch = trading_symbols[i:i + batch_size]
                try:
                    batch_quotes = kite.quote(batch)
                    quotes.update(batch_quotes)
                except Exception as e:
                    logger.warning(f"Error fetching quotes batch: {e}")

        # Enrich holdings with live data
        enriched_holdings = []
        for h in holdings:
            symbol = h.get("tradingsymbol", "")
            exchange = h.get("exchange", "NSE")
            key = f"{exchange}:{symbol}"

            quote = quotes.get(key, {})
            ohlc = quote.get("ohlc", {})

            enriched = {
                "tradingsymbol": symbol,
                "exchange": exchange,
                "isin": h.get("isin", ""),
                "quantity": h.get("quantity", 0),
                "average_price": h.get("average_price", 0),
                "last_price": h.get("last_price", 0) or quote.get("last_price", 0),
                "close_price": h.get("close_price", 0) or ohlc.get("close", 0),
                "pnl": h.get("pnl", 0),
                "day_change": h.get("day_change", 0),
                "day_change_percentage": h.get("day_change_percentage", 0),
                "instrument_token": h.get("instrument_token", 0),
                "product": h.get("product", ""),
                "t1_quantity": h.get("t1_quantity", 0),
                "realised_quantity": h.get("realised_quantity", 0),
                "opening_quantity": h.get("opening_quantity", 0),
                "collateral_quantity": h.get("collateral_quantity", 0),
                # Computed fields
                "invested_value": h.get("quantity", 0) * h.get("average_price", 0),
                "current_value": h.get("quantity", 0) * (h.get("last_price", 0) or quote.get("last_price", 0)),
                "profit": h.get("pnl", 0),
                "profit_pct": (
                    (h.get("pnl", 0) / (h.get("quantity", 0) * h.get("average_price", 0)) * 100)
                    if (h.get("quantity", 0) * h.get("average_price", 0)) > 0 else 0
                ),
                # 52w high/low from quote
                "week_52_high": ohlc.get("high", 0),
                "week_52_low": ohlc.get("low", 0),
                "open": ohlc.get("open", 0),
                "volume": quote.get("volume", 0),
            }
            enriched_holdings.append(enriched)

        # Process positions
        net_positions = positions.get("net", [])
        day_positions = positions.get("day", [])

        member_data = {
            "name": name,
            "profile": {
                "user_name": profile.get("user_name", name),
                "email": profile.get("email", ""),
                "user_id": profile.get("user_id", ""),
                "broker": profile.get("broker", "ZERODHA"),
            },
            "holdings": enriched_holdings,
            "positions_net": net_positions,
            "positions_day": day_positions,
            "fetched_at": datetime.now().isoformat(),
        }

        return member_data

    except Exception as e:
        logger.error(f"Error fetching data for {name}: {e}")
        return {
            "name": name,
            "error": str(e),
            "holdings": [],
            "positions_net": [],
            "positions_day": [],
            "profile": {"user_name": name},
            "fetched_at": datetime.now().isoformat(),
        }


def fetch_all_data():
    """Fetch data for all family members and save to disk."""
    all_data = {
        "members": [],
        "fetched_at": datetime.now().isoformat(),
        "next_refresh": (datetime.now() + timedelta(hours=config.REFRESH_INTERVAL_HOURS)).isoformat(),
    }

    for member in config.FAMILY_MEMBERS:
        if not member.get("access_token"):
            logger.warning(f"Skipping {member['name']}: no access token configured")
            all_data["members"].append({
                "name": member["name"],
                "error": "No access token configured. Please complete Kite login.",
                "holdings": [],
                "positions_net": [],
                "positions_day": [],
                "profile": {"user_name": member["name"]},
                "fetched_at": datetime.now().isoformat(),
            })
            continue
        member_data = fetch_member_data(member)
        all_data["members"].append(member_data)

    # Save to file
    data_file = os.path.join(config.DATA_DIR, "portfolio_data.json")
    with open(data_file, "w") as f:
        json.dump(all_data, f, indent=2, default=str)

    logger.info(f"Data saved to {data_file}")
    return all_data


def load_cached_data():
    """Load cached data from disk."""
    data_file = os.path.join(config.DATA_DIR, "portfolio_data.json")
    if os.path.exists(data_file):
        with open(data_file, "r") as f:
            return json.load(f)
    return None


def generate_demo_data():
    """Generate realistic demo data for testing the dashboard without API credentials."""
    import random

    stocks = [
        ("RELIANCE", "NSE", 2480.50, 2150.00, 15, "2024-03-15"),
        ("TCS", "NSE", 3890.25, 3450.00, 10, "2023-11-20"),
        ("HDFCBANK", "NSE", 1685.75, 1520.00, 25, "2024-01-10"),
        ("INFY", "NSE", 1520.30, 1380.00, 20, "2023-08-05"),
        ("ICICIBANK", "NSE", 1125.60, 980.00, 30, "2024-06-12"),
        ("HINDUNILVR", "NSE", 2650.80, 2780.00, 8, "2023-05-18"),
        ("SBIN", "NSE", 785.40, 620.00, 40, "2024-02-28"),
        ("BHARTIARTL", "NSE", 1580.90, 1350.00, 12, "2023-09-14"),
        ("ITC", "NSE", 465.20, 420.00, 50, "2024-04-22"),
        ("KOTAKBANK", "NSE", 1825.65, 1750.00, 15, "2023-12-01"),
        ("LT", "NSE", 3450.00, 3100.00, 8, "2024-07-05"),
        ("WIPRO", "NSE", 485.30, 520.00, 35, "2023-10-30"),
        ("AXISBANK", "NSE", 1155.40, 1020.00, 20, "2024-05-15"),
        ("MARUTI", "NSE", 12450.80, 11200.00, 3, "2023-06-20"),
        ("SUNPHARMA", "NSE", 1720.50, 1580.00, 10, "2024-08-10"),
        ("TATAMOTORS", "NSE", 925.60, 780.00, 25, "2023-07-25"),
        ("POWERGRID", "NSE", 310.40, 275.00, 60, "2024-01-28"),
        ("NTPC", "NSE", 385.70, 340.00, 45, "2023-04-12"),
        ("BAJFINANCE", "NSE", 7250.30, 6800.00, 5, "2024-09-01"),
        ("TITAN", "NSE", 3560.80, 3200.00, 7, "2023-11-08"),
    ]

    mutual_funds = [
        ("NIFTYBEES", "NSE", 265.40, 230.00, 100, "2023-01-15"),
        ("JUNIORBEES", "NSE", 680.20, 590.00, 30, "2023-03-20"),
        ("GOLDBEES", "NSE", 52.80, 45.00, 200, "2022-12-10"),
        ("BANKBEES", "NSE", 445.60, 410.00, 50, "2024-02-01"),
        ("LIQUIDBEES", "NSE", 1000.05, 1000.00, 20, "2024-06-15"),
    ]

    # MF symbols for identification
    MF_SYMBOLS = {"NIFTYBEES", "JUNIORBEES", "GOLDBEES", "BANKBEES", "LIQUIDBEES"}

    # Multiple purchase tranches for mutual funds (for drill-down)
    mf_purchases = {
        "NIFTYBEES": [
            {"date": "2022-06-10", "qty": 20, "price": 198.50, "member": "Primary"},
            {"date": "2022-11-15", "qty": 30, "price": 210.20, "member": "Primary"},
            {"date": "2023-01-15", "qty": 50, "price": 225.80, "member": "Primary"},
            {"date": "2023-06-20", "qty": 25, "price": 238.40, "member": "Spouse"},
            {"date": "2023-10-05", "qty": 40, "price": 245.60, "member": "Spouse"},
            {"date": "2024-02-14", "qty": 35, "price": 252.10, "member": "Spouse"},
            {"date": "2024-08-22", "qty": 20, "price": 258.30, "member": "Primary"},
            {"date": "2025-01-10", "qty": 15, "price": 261.00, "member": "Spouse"},
        ],
        "JUNIORBEES": [
            {"date": "2023-03-20", "qty": 10, "price": 560.00, "member": "Primary"},
            {"date": "2023-07-11", "qty": 10, "price": 575.30, "member": "Primary"},
            {"date": "2023-11-28", "qty": 10, "price": 598.50, "member": "Primary"},
            {"date": "2024-01-05", "qty": 15, "price": 610.20, "member": "Spouse"},
            {"date": "2024-05-18", "qty": 15, "price": 640.80, "member": "Spouse"},
            {"date": "2024-11-30", "qty": 10, "price": 665.00, "member": "Spouse"},
        ],
        "GOLDBEES": [
            {"date": "2022-03-15", "qty": 50, "price": 38.20, "member": "Primary"},
            {"date": "2022-07-22", "qty": 50, "price": 40.50, "member": "Primary"},
            {"date": "2022-12-10", "qty": 100, "price": 43.80, "member": "Primary"},
            {"date": "2023-04-05", "qty": 80, "price": 46.10, "member": "Spouse"},
            {"date": "2023-09-18", "qty": 60, "price": 48.30, "member": "Spouse"},
            {"date": "2024-03-01", "qty": 40, "price": 49.70, "member": "Spouse"},
            {"date": "2024-10-12", "qty": 30, "price": 51.20, "member": "Primary"},
        ],
        "BANKBEES": [
            {"date": "2023-08-10", "qty": 20, "price": 385.00, "member": "Spouse"},
            {"date": "2024-02-01", "qty": 30, "price": 405.50, "member": "Spouse"},
            {"date": "2024-06-15", "qty": 25, "price": 418.20, "member": "Primary"},
            {"date": "2024-12-03", "qty": 15, "price": 430.80, "member": "Primary"},
            {"date": "2025-02-10", "qty": 10, "price": 440.00, "member": "Spouse"},
        ],
        "LIQUIDBEES": [
            {"date": "2024-01-20", "qty": 5, "price": 1000.00, "member": "Primary"},
            {"date": "2024-06-15", "qty": 10, "price": 1000.01, "member": "Spouse"},
            {"date": "2024-09-30", "qty": 5, "price": 1000.02, "member": "Primary"},
            {"date": "2025-01-15", "qty": 10, "price": 1000.03, "member": "Spouse"},
        ],
    }

    def make_holdings(stock_list, seed_offset=0):
        holdings = []
        for i, (symbol, exchange, ltp, avg, qty, buy_date) in enumerate(stock_list):
            random.seed(42 + i + seed_offset)
            day_chg_pct = random.uniform(-3, 4)
            day_chg = ltp * day_chg_pct / 100
            invested = qty * avg
            current = qty * ltp
            pnl = current - invested
            pnl_pct = (pnl / invested * 100) if invested > 0 else 0

            holding = {
                "tradingsymbol": symbol,
                "exchange": exchange,
                "isin": f"INE{random.randint(100000, 999999)}",
                "quantity": qty,
                "average_price": round(avg, 2),
                "last_price": round(ltp, 2),
                "close_price": round(ltp - day_chg, 2),
                "pnl": round(pnl, 2),
                "day_change": round(day_chg, 2),
                "day_change_percentage": round(day_chg_pct, 2),
                "instrument_token": random.randint(100000, 9999999),
                "product": "CNC",
                "t1_quantity": 0,
                "realised_quantity": qty,
                "opening_quantity": qty,
                "collateral_quantity": 0,
                "invested_value": round(invested, 2),
                "current_value": round(current, 2),
                "profit": round(pnl, 2),
                "profit_pct": round(pnl_pct, 2),
                "week_52_high": round(ltp * random.uniform(1.05, 1.35), 2),
                "week_52_low": round(ltp * random.uniform(0.55, 0.85), 2),
                "open": round(ltp + random.uniform(-20, 20), 2),
                "volume": random.randint(100000, 50000000),
                "buy_date": buy_date,
                "is_mutual_fund": symbol in MF_SYMBOLS,
            }
            holdings.append(holding)
        return holdings

    members = [
        {
            "name": "Primary",
            "profile": {
                "user_name": "Mohit Changlani",
                "email": "mohit@example.com",
                "user_id": "AB1234",
                "broker": "ZERODHA",
            },
            "holdings": make_holdings(stocks[:14] + mutual_funds[:3], seed_offset=0),
            "positions_net": [],
            "positions_day": [],
            "fetched_at": datetime.now().isoformat(),
        },
        {
            "name": "Spouse",
            "profile": {
                "user_name": "Priya Changlani",
                "email": "priya@example.com",
                "user_id": "CD5678",
                "broker": "ZERODHA",
            },
            "holdings": make_holdings(stocks[5:20] + mutual_funds[1:], seed_offset=100),
            "positions_net": [],
            "positions_day": [],
            "fetched_at": datetime.now().isoformat(),
        },
    ]

    # Fixed Deposit investments
    fixed_deposits = [
        {
            "id": "FD001",
            "bank": "SBI",
            "scheme": "SBI Tax Saving FD",
            "principal": 500000,
            "interest_rate": 7.10,
            "compounding": "quarterly",
            "investment_date": "2023-04-15",
            "maturity_date": "2028-04-15",
            "tenure_months": 60,
            "member": "Primary",
        },
        {
            "id": "FD002",
            "bank": "HDFC Bank",
            "scheme": "HDFC Regular FD",
            "principal": 300000,
            "interest_rate": 7.25,
            "compounding": "quarterly",
            "investment_date": "2024-01-10",
            "maturity_date": "2026-01-10",
            "tenure_months": 24,
            "member": "Primary",
        },
        {
            "id": "FD003",
            "bank": "ICICI Bank",
            "scheme": "ICICI 5Y Tax Saver",
            "principal": 150000,
            "interest_rate": 7.00,
            "compounding": "quarterly",
            "investment_date": "2022-07-01",
            "maturity_date": "2027-07-01",
            "tenure_months": 60,
            "member": "Spouse",
        },
        {
            "id": "FD004",
            "bank": "Post Office",
            "scheme": "NSC VIII Issue",
            "principal": 200000,
            "interest_rate": 7.70,
            "compounding": "yearly",
            "investment_date": "2023-10-20",
            "maturity_date": "2028-10-20",
            "tenure_months": 60,
            "member": "Spouse",
        },
        {
            "id": "FD005",
            "bank": "Axis Bank",
            "scheme": "Axis Fixed Deposit",
            "principal": 250000,
            "interest_rate": 7.15,
            "compounding": "quarterly",
            "investment_date": "2024-06-01",
            "maturity_date": "2025-12-01",
            "tenure_months": 18,
            "member": "Primary",
        },
        {
            "id": "FD006",
            "bank": "Bajaj Finance",
            "scheme": "Bajaj Finance FD",
            "principal": 400000,
            "interest_rate": 8.25,
            "compounding": "quarterly",
            "investment_date": "2023-01-15",
            "maturity_date": "2026-01-15",
            "tenure_months": 36,
            "member": "Spouse",
        },
        {
            "id": "FD007",
            "bank": "SBI",
            "scheme": "SBI Regular FD",
            "principal": 100000,
            "interest_rate": 6.80,
            "compounding": "quarterly",
            "investment_date": "2024-09-01",
            "maturity_date": "2025-09-01",
            "tenure_months": 12,
            "member": "Primary",
        },
    ]

    return {
        "members": members,
        "mf_purchases": mf_purchases,
        "fixed_deposits": fixed_deposits,
        "fetched_at": datetime.now().isoformat(),
        "next_refresh": (datetime.now() + timedelta(hours=config.REFRESH_INTERVAL_HOURS)).isoformat(),
        "is_demo": True,
    }
