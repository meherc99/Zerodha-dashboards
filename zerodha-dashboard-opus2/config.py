"""
Configuration for Zerodha Dashboard
Update these values with your Kite Connect API credentials.
You can get these from https://developers.kite.trade/
"""

import os

# --- Kite Connect API Credentials ---
# You can set these as environment variables or edit directly here
KITE_API_KEY = os.environ.get("KITE_API_KEY", "your_api_key_here")
KITE_API_SECRET = os.environ.get("KITE_API_SECRET", "your_api_secret_here")
KITE_ACCESS_TOKEN = os.environ.get("KITE_ACCESS_TOKEN", "")

# --- Family Members ---
# Add each family member's Kite credentials here.
# Each entry: { "name": "...", "api_key": "...", "api_secret": "...", "access_token": "..." }
FAMILY_MEMBERS = [
    {
        "name": "Primary",
        "api_key": KITE_API_KEY,
        "api_secret": KITE_API_SECRET,
        "access_token": KITE_ACCESS_TOKEN,
    },
    # Add more family members:
    # {
    #     "name": "Spouse",
    #     "api_key": os.environ.get("KITE_API_KEY_2", ""),
    #     "api_secret": os.environ.get("KITE_API_SECRET_2", ""),
    #     "access_token": os.environ.get("KITE_ACCESS_TOKEN_2", ""),
    # },
]

# --- App Settings ---
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "zerodha-dashboard-secret-key-change-me")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
REFRESH_INTERVAL_HOURS = 12
PORT = 5050
DEBUG = True
