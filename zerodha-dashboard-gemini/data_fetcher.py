import os
import pandas as pd
from kiteconnect import KiteConnect
from dotenv import load_dotenv
import datetime
import random

load_dotenv()

def get_kite_sessions():
    """
    To support 'family' holdings, we read credentials for multiple users.
    Format your .env like:
    USER1_API_KEY="..."
    USER1_API_SECRET="..."
    USER1_REQ_TOKEN="..."
    
    USER2_API_KEY="..."
    """
    sessions = []
    # Simple check for multiple users by prefix matching
    user_prefixes = set(k.split('_')[0] for k in os.environ.keys() if 'API_KEY' in k)
    
    for prefix in user_prefixes:
        api_key = os.getenv(f"{prefix}_API_KEY")
        api_secret = os.getenv(f"{prefix}_API_SECRET")
        req_token = os.getenv(f"{prefix}_REQ_TOKEN")
        
        if api_key and api_secret and req_token:
            try:
                kite = KiteConnect(api_key=api_key)
                data = kite.generate_session(req_token, api_secret=api_secret)
                kite.set_access_token(data["access_token"])
                sessions.append({"name": prefix.capitalize(), "session": kite})
            except Exception as e:
                print(f"Error authenticating {prefix}: {e}")
                
    return sessions

def fetch_all_holdings():
    """
    Fetches standard equity/MF holdings from connected Kite sessions.
    Returns a Pandas DataFrame.
    """
    sessions = get_kite_sessions()
    
    if not sessions:
        # Fallback to demo data if no configured sessions found
        print("No valid Kite sessions configured. Returning mock family data...")
        return get_mock_data()
        
    all_data = []
    for s in sessions:
        kite = s["session"]
        try:
            holdings = kite.holdings()
            for h in holdings:
                # Calculate required metrics
                avg_price = h.get('average_price', 0)
                qty = h.get('quantity', 0)
                last_price = h.get('last_price', 0)
                invested = avg_price * qty
                current_val = last_price * qty
                pnl = current_val - invested
                pnl_pct = (pnl / invested * 100) if invested > 0 else 0
                
                # Fetching exact "date of buying" is difficult from the holdings API.
                # Usually authorised_date or relying on backend matching is required.
                # In retail kite APIs, date of buying all stocks requires historical trade book parsing.
                # For this dashboard we use authorised_date or set a placeholder.
                
                all_data.append({
                    "Account": s["name"],
                    "Symbol": h.get("tradingsymbol"),
                    "Instrument": h.get("instrument_token"),
                    "Type": "MF" if "-G" in h.get("tradingsymbol", "") or "BE" in h.get("tradingsymbol", "") else "EQ", 
                    "Quantity": qty,
                    "Avg Buy Price": avg_price,
                    "Last Price": last_price,
                    "Invested Amount": invested,
                    "Current Value": current_val,
                    "Total P&L": pnl,
                    "Total P&L %": pnl_pct,
                    # Fallback purchase date proxy
                    "Buy Date": h.get("authorised_date", "N/A (See note)")
                })
        except Exception as e:
            print(f"Error fetching holdings for {s['name']}: {e}")

    return pd.DataFrame(all_data)

def get_mock_data():
    """Returns realistic mock data to render the dashboard before keys are added."""
    data = []
    users = ["Wife", "Husband", "Parent"]
    symbols = [
        ("RELIANCE", "EQ"), ("TCS", "EQ"), ("INFY", "EQ"), ("HDFCBANK", "EQ"),
        ("ICICIBANK", "EQ"), ("SBI", "EQ"), ("ITC", "EQ"), ("L&T", "EQ"),
        ("BAJFINANCE", "EQ"), ("BHARTIARTL", "EQ"), 
        ("PARAG_PARIKH_FLEXI", "MF"), ("SBI_SMALL_CAP", "MF"), ("HDFC_INDEX", "MF")
    ]
    
    for u in users:
        # Give each user 5-8 random holdings
        user_symbols = random.sample(symbols, random.randint(5, 8))
        for sym, type_ in user_symbols:
            qty = random.randint(10, 200) if type_ == "EQ" else random.randint(100, 1000)
            avg_price = random.uniform(100, 4000)
            
            # Simulate some profit, some loss
            performance_multiplier = random.uniform(0.7, 1.8) 
            last_price = avg_price * performance_multiplier
            
            invested = qty * avg_price
            current_value = qty * last_price
            pnl = current_value - invested
            pnl_pct = (pnl / invested) * 100
            
            # Simulated buy date within last 3 years
            days_ago = random.randint(30, 1000)
            buy_date = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).strftime('%Y-%m-%d')
            
            data.append({
                "Account": u,
                "Symbol": sym,
                "Type": type_,
                "Quantity": qty,
                "Avg Buy Price": round(avg_price, 2),
                "Last Price": round(last_price, 2),
                "Invested Amount": round(invested, 2),
                "Current Value": round(current_value, 2),
                "Total P&L": round(pnl, 2),
                "Total P&L %": round(pnl_pct, 2),
                "Buy Date": buy_date
            })
            
    return pd.DataFrame(data)
