# Quick Start Guide: US Stocks Feature

## Prerequisites

1. **Get Finnhub API Key** (Free)
   - Visit https://finnhub.io/register
   - Sign up for a free account
   - Copy your API key from the dashboard

## Setup Steps

### 1. Configure Backend

```bash
# Navigate to backend directory
cd backend

# Update .env file with your Finnhub API key
# Replace 'your_finnhub_api_key_here' with your actual API key
nano .env  # or use any text editor
```

Update this line in `.env`:
```
FINNHUB_API_KEY=your_actual_api_key_here
```

### 2. Install Dependencies

Backend dependencies are already installed (openpyxl and finnhub-python).

### 3. Start the Application

**Terminal 1 - Backend:**
```bash
cd backend
python run.py
# Server will start on http://localhost:5000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
# App will open on http://localhost:5173
```

## Using the US Stocks Feature

### Step 1: Prepare Your Excel File

Create an Excel file (.xlsx) with these columns:

| Symbol | Quantity | Average Price | Purchase Date |
|--------|----------|---------------|---------------|
| AAPL   | 10       | 150.50        | 2024-01-15    |
| TSLA   | 5        | 240.00        | 2024-02-01    |
| MSFT   | 8        | 380.25        | 2024-01-20    |

**Required columns:**
- Symbol (stock ticker)
- Quantity (number of shares)
- Average Price (in USD)

**Optional:**
- Purchase Date (YYYY-MM-DD format)

### Step 2: Upload Holdings

1. Open http://localhost:5173 in your browser
2. Click "🇺🇸 US Stocks" in the sidebar
3. Either:
   - Drag and drop your Excel file, OR
   - Click "Select File" to browse

4. Click "Upload & Fetch Prices"
5. Wait for upload and price fetching to complete
6. Your holdings will appear with real-time prices!

### Step 3: Refresh Prices

- Prices auto-refresh when you load the tab
- Click "🔄 Refresh Prices" button anytime for latest prices

## Features

✅ **File Upload**: Drag-and-drop or file picker
✅ **Real-Time Prices**: Automatic price fetching from Finnhub
✅ **Portfolio Summary**: Total value, P&L, day change
✅ **Charts**: Allocation pie chart and top holdings bar chart
✅ **Holdings Table**: Sortable table with all holdings
✅ **Auto-Refresh**: Prices refresh when tab loads
✅ **Manual Refresh**: Update prices on demand

## Example Excel File

See `sample_us_holdings.xlsx.md` for detailed format specifications.

## Troubleshooting

### "FINNHUB_API_KEY not found" Error
- Make sure you updated the `.env` file with your actual API key
- Restart the backend server after updating `.env`

### Upload Fails
- Check that your Excel file has the correct column names
- Ensure Symbol, Quantity, and Average Price columns exist
- Make sure at least one account exists in the system

### Prices Show as $0
- Invalid stock symbols
- API rate limit exceeded (wait 1 minute)
- Check internet connection
- Verify Finnhub API key is valid

### Need Help?
Check `US_STOCKS_IMPLEMENTATION.md` for detailed documentation.

## Rate Limits

Finnhub free tier allows:
- 60 API calls per minute
- Each symbol requires one API call
- Upload with 50 stocks = 50 API calls

If you have many stocks, they'll be fetched sequentially.

## Next Steps

After successfully uploading your US holdings:

1. ✅ View your portfolio summary
2. ✅ Analyze allocation with pie chart
3. ✅ Monitor top holdings with bar chart
4. ✅ Track P&L in the holdings table
5. ✅ Refresh prices regularly for latest data

Enjoy tracking your US stock portfolio! 🚀
