# US Stocks Feature Implementation

## Overview

This document outlines the implementation of the US Stocks feature, which allows users to upload Excel files containing their US stock holdings and automatically fetch real-time prices using the Finnhub API.

## What Was Implemented

### Backend Changes

1. **New Dependencies** (`backend/requirements.txt`)
   - `openpyxl==3.1.2` - For reading Excel files
   - `finnhub-python==2.4.19` - For fetching US stock prices

2. **Database Model Updates** (`backend/app/models/holding.py`)
   - Added `market` field to distinguish between Indian ('IN') and US ('US') holdings
   - Updated `instrument_type` to support 'us_equity' in addition to 'equity' and 'mf'
   - Added `market` to the `to_dict()` serialization

3. **New Services**
   - **FinnhubService** (`backend/app/services/finnhub_service.py`)
     - Integrates with Finnhub API for real-time US stock quotes
     - Methods: `get_quote()`, `get_quotes_batch()`
     - Handles API errors gracefully

   - **USHoldingsService** (`backend/app/services/us_holdings_service.py`)
     - Parses Excel files with holdings data
     - Creates holdings in database with current prices
     - Methods: `parse_excel_file()`, `fetch_current_prices()`, `create_holdings()`

4. **New API Endpoints** (`backend/app/routes/holdings.py`)
   - `POST /api/holdings/us/upload` - Upload Excel file with US holdings
   - `POST /api/holdings/us/refresh-prices` - Refresh prices for existing US holdings

5. **Environment Configuration** (`backend/.env`)
   - Added `FINNHUB_API_KEY` configuration

### Frontend Changes

1. **API Client Updates** (`frontend/src/services/api.js`)
   - `uploadUSHoldings(file, accountId)` - Upload Excel file
   - `refreshUSPrices(accountId)` - Refresh US stock prices

2. **Store Updates** (`frontend/src/stores/holdings.js`)
   - New getters: `usHoldings`, `usSummary`
   - New actions: `uploadUSHoldings()`, `refreshUSPrices()`

3. **New Component** (`frontend/src/views/dashboard/USStocksTab.vue`)
   - Complete US Stocks dashboard tab
   - File upload interface with drag-and-drop
   - Portfolio summary cards
   - Charts (allocation pie chart, top holdings bar chart)
   - Holdings table
   - Auto-refresh prices on component mount
   - Manual refresh button

4. **Router Updates** (`frontend/src/router/index.js`)
   - Added `/dashboard/us-stocks` route

5. **Sidebar Updates** (`frontend/src/components/dashboard/Sidebar.vue`)
   - Added "US Stocks" navigation link with 🇺🇸 icon

## How It Works

### Upload Workflow

1. User navigates to "US Stocks" tab
2. If no US holdings exist, upload interface is shown
3. User selects or drags an Excel file (.xlsx)
4. File is uploaded to backend
5. Backend parses Excel file and validates data
6. For each stock symbol, Finnhub API is called to fetch current price
7. Holdings are saved to database with current prices
8. Frontend refreshes to show the uploaded holdings

### Price Refresh Workflow

1. User clicks "Refresh Prices" button (or tab loads)
2. Backend fetches latest snapshot of US holdings
3. Finnhub API is called for each unique symbol
4. Holdings are updated with new prices
5. P&L calculations are refreshed
6. Frontend displays updated data

## Excel File Format

Required columns:
- **Symbol** - Stock ticker (e.g., AAPL, TSLA)
- **Quantity** - Number of shares
- **Average Price** - Average purchase price per share

Optional columns:
- **Purchase Date** - Date of purchase

See `sample_us_holdings.xlsx.md` for example.

## API Integration

### Finnhub API

- **Free Tier**: 60 API calls per minute
- **Authentication**: API key required (sign up at https://finnhub.io/register)
- **Data Returned**: Current price, day change, day change %, high, low, open, previous close

### Rate Limiting

Current implementation:
- Fetches prices sequentially (one API call per symbol)
- No batching in free tier
- Errors are handled gracefully per symbol
- Failed price fetches fall back to average price

## Configuration Required

1. **Get Finnhub API Key**
   - Sign up at https://finnhub.io/register
   - Copy API key from dashboard

2. **Update Backend .env**
   ```bash
   FINNHUB_API_KEY=your_actual_api_key_here
   ```

3. **Install Dependencies**
   ```bash
   cd backend
   pip install openpyxl==3.1.2 finnhub-python==2.4.19
   ```

4. **Database Migration** (if needed)
   ```bash
   cd backend
   alembic revision --autogenerate -m "Add market field to holdings"
   alembic upgrade head
   ```

## Testing

### Backend Testing

1. Start backend server:
   ```bash
   cd backend
   python run.py
   ```

2. Test upload endpoint:
   ```bash
   curl -X POST http://localhost:5000/api/holdings/us/upload \
     -F "file=@sample_holdings.xlsx" \
     -F "account_id=1"
   ```

3. Test price refresh:
   ```bash
   curl -X POST http://localhost:5000/api/holdings/us/refresh-prices \
     -H "Content-Type: application/json" \
     -d '{"account_id": 1}'
   ```

### Frontend Testing

1. Start frontend:
   ```bash
   cd frontend
   npm run dev
   ```

2. Navigate to http://localhost:5173
3. Click "US Stocks" in sidebar
4. Upload a sample Excel file
5. Verify holdings appear with current prices
6. Test refresh prices button
7. Navigate away and back to verify auto-refresh

## Files Modified/Created

### Backend Files Created
- `backend/app/services/finnhub_service.py`
- `backend/app/services/us_holdings_service.py`

### Backend Files Modified
- `backend/requirements.txt` - Added dependencies
- `backend/app/models/holding.py` - Added market field
- `backend/app/routes/holdings.py` - Added upload and refresh endpoints
- `backend/.env` - Added FINNHUB_API_KEY

### Frontend Files Created
- `frontend/src/views/dashboard/USStocksTab.vue`

### Frontend Files Modified
- `frontend/src/services/api.js` - Added US holdings methods
- `frontend/src/stores/holdings.js` - Added US holdings getters and actions
- `frontend/src/router/index.js` - Added us-stocks route
- `frontend/src/components/dashboard/Sidebar.vue` - Added US Stocks link

### Documentation Created
- `sample_us_holdings.xlsx.md` - Example file format
- `US_STOCKS_IMPLEMENTATION.md` - This file

## Known Limitations

1. **Finnhub API Rate Limits**: Free tier limited to 60 calls/minute
2. **No Batch API**: Must fetch prices one symbol at a time
3. **Market Hours**: Prices are delayed outside US market hours
4. **Symbol Validation**: No validation that symbols are valid US stocks
5. **Exchange Detection**: All US stocks marked as 'US' exchange (not NASDAQ/NYSE specific)

## Future Enhancements

1. **Batch Price Fetching**: Implement caching and smarter batching
2. **Symbol Validation**: Validate symbols before accepting upload
3. **Exchange Detection**: Detect and store specific exchange (NASDAQ/NYSE/etc)
4. **Sector Data**: Fetch and store sector information from Finnhub
5. **Historical Data**: Store price history for charting
6. **Upload History**: Track upload history and versioning
7. **Multi-Currency**: Support currency conversion for non-USD holdings
8. **Scheduled Refresh**: Auto-refresh prices on a schedule

## Troubleshooting

### "FINNHUB_API_KEY not found"
- Ensure API key is set in `backend/.env`
- Check that key is not 'your_finnhub_api_key_here'
- Restart backend server after updating .env

### "Invalid file format"
- Ensure file is .xlsx or .xls format
- Check that required columns exist: Symbol, Quantity, Average Price
- Verify column names match exactly (case-sensitive)

### "No valid holdings found"
- Check Excel file has data rows (not just headers)
- Ensure Symbol column is not empty
- Verify Quantity and Average Price are positive numbers

### "Failed to fetch quote"
- Verify API key is valid
- Check internet connection
- Ensure symbol is a valid US stock ticker
- May be rate limited (wait a minute and try again)

### Backend won't start
- Activate virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`
- Check port 5000 is not in use

### Frontend can't upload
- Ensure backend is running on port 5000
- Check browser console for CORS errors
- Verify at least one account exists in database
