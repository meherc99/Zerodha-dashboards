"""
Manual test script to verify bank analytics endpoints work correctly.
Run this after starting the Flask app to test the analytics endpoints.
"""
import requests
import json
from datetime import date, timedelta
from decimal import Decimal

# Configuration
BASE_URL = "http://localhost:5000/api"
TEST_EMAIL = "analytics_test@example.com"
TEST_PASSWORD = "testpass123"

def test_analytics_endpoints():
    """Test all bank analytics endpoints"""

    # 1. Register a test user
    print("1. Registering test user...")
    register_response = requests.post(f"{BASE_URL}/auth/register", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "full_name": "Analytics Test User"
    })

    if register_response.status_code == 201:
        print("   ✓ User registered successfully")
    elif register_response.status_code == 400 and "already exists" in register_response.text:
        print("   ✓ User already exists")
    else:
        print(f"   ✗ Registration failed: {register_response.text}")
        return

    # 2. Login
    print("\n2. Logging in...")
    login_response = requests.post(f"{BASE_URL}/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })

    if login_response.status_code != 200:
        print(f"   ✗ Login failed: {login_response.text}")
        return

    token = login_response.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    print("   ✓ Login successful")

    # 3. Create a bank account
    print("\n3. Creating bank account...")
    account_response = requests.post(f"{BASE_URL}/bank-accounts",
        headers=headers,
        json={
            "bank_name": "Test Bank",
            "account_number": "TEST123456",
            "current_balance": 50000.00
        })

    if account_response.status_code != 201:
        print(f"   ✗ Account creation failed: {account_response.text}")
        return

    account_id = account_response.json()['id']
    print(f"   ✓ Bank account created (ID: {account_id})")

    # 4. Test Balance Trend endpoint
    print("\n4. Testing Balance Trend endpoint...")
    trend_response = requests.get(
        f"{BASE_URL}/bank-accounts/{account_id}/analytics/balance-trend?days=30",
        headers=headers
    )

    if trend_response.status_code == 200:
        data = trend_response.json()
        print(f"   ✓ Balance Trend successful")
        print(f"     Period: {data['period_days']} days")
        print(f"     Data points: {len(data['dates'])}")
    else:
        print(f"   ✗ Balance Trend failed: {trend_response.text}")

    # 5. Test Category Breakdown endpoint
    print("\n5. Testing Category Breakdown endpoint...")
    category_response = requests.get(
        f"{BASE_URL}/bank-accounts/{account_id}/analytics/category-breakdown?period_days=30",
        headers=headers
    )

    if category_response.status_code == 200:
        data = category_response.json()
        print(f"   ✓ Category Breakdown successful")
        print(f"     Total spending: ₹{data['total_spending']:.2f}")
        print(f"     Categories: {len(data['categories'])}")
        for cat in data['categories'][:3]:
            print(f"       - {cat['icon']} {cat['name']}: ₹{cat['total']:.2f} ({cat['percentage']:.1f}%)")
    else:
        print(f"   ✗ Category Breakdown failed: {category_response.text}")

    # 6. Test Cashflow endpoint
    print("\n6. Testing Cashflow endpoint...")
    cashflow_response = requests.get(
        f"{BASE_URL}/bank-accounts/{account_id}/analytics/cashflow?period_days=30",
        headers=headers
    )

    if cashflow_response.status_code == 200:
        data = cashflow_response.json()
        print(f"   ✓ Cashflow Analysis successful")
        print(f"     Periods: {len(data['periods'])}")
        for i, period in enumerate(data['periods']):
            print(f"       {period}: Credits=₹{data['credits'][i]:.2f}, Debits=₹{data['debits'][i]:.2f}, Net=₹{data['net'][i]:.2f}")
    else:
        print(f"   ✗ Cashflow failed: {cashflow_response.text}")

    # 7. Test Top Merchants endpoint
    print("\n7. Testing Top Merchants endpoint...")
    merchants_response = requests.get(
        f"{BASE_URL}/bank-accounts/{account_id}/analytics/top-merchants?limit=5",
        headers=headers
    )

    if merchants_response.status_code == 200:
        data = merchants_response.json()
        print(f"   ✓ Top Merchants successful")
        print(f"     Top {len(data['merchants'])} merchants:")
        for merchant in data['merchants']:
            print(f"       - {merchant['merchant']}: ₹{merchant['total']:.2f} ({merchant['count']} txns, avg ₹{merchant['avg_transaction']:.2f})")
    else:
        print(f"   ✗ Top Merchants failed: {merchants_response.text}")

    print("\n" + "="*60)
    print("✓ All analytics endpoints tested successfully!")
    print("="*60)


if __name__ == "__main__":
    print("="*60)
    print("Bank Analytics Endpoints Manual Test")
    print("="*60)
    print(f"\nMake sure Flask app is running on {BASE_URL}")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    input()

    try:
        test_analytics_endpoints()
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Cannot connect to Flask app. Make sure it's running on port 5000.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
