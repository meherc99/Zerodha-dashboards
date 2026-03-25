# Fixed Deposits Feature Implementation

## Overview

This document outlines the implementation of the Fixed Deposits (FD) feature, which allows users to upload Excel files containing their bank FD details and automatically calculate interest earned and current value based on investment date and interest rate.

## What Was Implemented

### Backend Changes

1. **New Service** (`backend/app/services/fd_service.py`)
   - **FDService** class for managing FD holdings
   - Methods:
     - `calculate_fd_returns()` - Calculates interest using simple interest formula
     - `parse_excel_file()` - Parses Excel file with FD data
     - `create_fd_holdings()` - Creates FD holdings in database
     - `refresh_fd_values()` - Recalculates interest for existing FDs

2. **New API Endpoints** (`backend/app/routes/holdings.py`)
   - `POST /api/holdings/fd/upload` - Upload Excel file with FD details
   - `POST /api/holdings/fd/refresh-values` - Recalculate interest for existing FDs

3. **Data Model** (Reusing existing `Holding` model)
   - `instrument_type = 'fd'` - Identifies Fixed Deposit holdings
   - `tradingsymbol` - Stores bank name
   - `average_price` - Stores investment amount (principal)
   - `last_price` / `current_value` - Stores current value (principal + interest)
   - `pnl` - Stores interest earned
   - `sector` - Stores interest rate (e.g., "7.5% p.a.")
   - `purchase_date` - Stores investment date

### Frontend Changes

1. **API Client Updates** (`frontend/src/services/api.js`)
   - `uploadFDHoldings(file, accountId)` - Upload Excel file
   - `refreshFDValues(accountId)` - Recalculate interest

2. **Store Updates** (`frontend/src/stores/holdings.js`)
   - New getters: `fdHoldings`, `fdSummary`
   - New actions: `uploadFDHoldings()`, `refreshFDValues()`

3. **New Component** (`frontend/src/views/dashboard/FixedDepositsTab.vue`)
   - Complete Fixed Deposits dashboard tab
   - File upload interface with drag-and-drop
   - Summary cards showing total investment, current value, interest earned
   - Detailed FD table with all holdings
   - Charts (bank-wise distribution, top FDs by value)
   - Auto-refresh interest on component mount
   - Manual recalculate button

4. **Router Updates** (`frontend/src/router/index.js`)
   - Added `/dashboard/fixed-deposits` route

5. **Sidebar Updates** (`frontend/src/components/dashboard/Sidebar.vue`)
   - Added "Fixed Deposits" navigation link with 🏦 icon

## How It Works

### Interest Calculation

The system uses **Simple Interest** formula:

```
Interest = (Principal × Rate × Time) / 100
```

Where:
- **Principal** = Investment Amount
- **Rate** = Annual Interest Rate (%)
- **Time** = Years Elapsed (Days Elapsed / 365)

Example:
```
Investment: ₹100,000
Rate: 7.5% p.a.
Days Elapsed: 100 days
Years Elapsed: 100/365 = 0.274 years

Interest = (100000 × 7.5 × 0.274) / 100 = ₹2,055
Current Value = 100000 + 2055 = ₹102,055
```

### Upload Workflow

1. User navigates to "Fixed Deposits" tab
2. If no FD holdings exist, upload interface is shown
3. User selects or drags an Excel file (.xlsx)
4. File is uploaded to backend
5. Backend parses Excel file and validates data
6. For each FD record, interest is calculated based on:
   - Investment amount
   - Investment date
   - Interest rate
   - Current date (or maturity date if provided)
7. FD holdings are saved to database with calculated values
8. Frontend refreshes to show the uploaded FDs

### Refresh Workflow

1. User clicks "Recalculate Interest" button (or tab loads)
2. Backend fetches all FD holdings
3. For each FD, interest is recalculated based on current date
4. Holdings are updated with new values
5. Frontend displays updated data

## Excel File Format

Required columns:
- **Bank Name** - Name of bank (e.g., HDFC, SBI)
- **Investment Amount** - Principal amount in INR
- **Investment Date** - Date of FD booking (YYYY-MM-DD)
- **Interest Rate** - Annual rate as number (e.g., 7.5)

Optional columns:
- **Maturity Date** - FD maturity date (YYYY-MM-DD)

See `sample_fd_holdings.xlsx.md` for detailed examples.

## Features

✅ **File Upload**: Drag-and-drop or file picker
✅ **Automatic Interest Calculation**: Using simple interest formula
✅ **Auto-Refresh**: Interest recalculated when tab loads
✅ **Manual Recalculate**: Update values on demand
✅ **Summary Cards**: Total investment, current value, interest earned
✅ **Detailed Table**: Bank name, dates, rates, interest, current value
✅ **Charts**: Bank-wise distribution and top FDs by value
✅ **Days Elapsed**: Shows how many days since investment
✅ **Dynamic Values**: Updates as time passes

## Files Created/Modified

### Backend Files Created
- `backend/app/services/fd_service.py`

### Backend Files Modified
- `backend/app/routes/holdings.py` - Added FD upload and refresh endpoints

### Frontend Files Created
- `frontend/src/views/dashboard/FixedDepositsTab.vue`

### Frontend Files Modified
- `frontend/src/services/api.js` - Added FD methods
- `frontend/src/stores/holdings.js` - Added FD getters and actions
- `frontend/src/router/index.js` - Added fixed-deposits route
- `frontend/src/components/dashboard/Sidebar.vue` - Added FD link

### Documentation Created
- `sample_fd_holdings.xlsx.md` - Example file format
- `FD_IMPLEMENTATION.md` - This file

## Usage

### Step 1: Prepare Excel File

Create an Excel file with these columns:

| Bank Name | Investment Amount | Investment Date | Interest Rate | Maturity Date |
|-----------|------------------|-----------------|---------------|---------------|
| HDFC Bank | 100000           | 2024-01-15      | 7.5           | 2025-01-15    |
| SBI       | 200000           | 2023-12-01      | 7.25          | 2024-12-01    |

### Step 2: Upload FD Records

1. Open http://localhost:5173 in browser
2. Click "🏦 Fixed Deposits" in sidebar
3. Upload your Excel file
4. Interest will be calculated automatically
5. View your FDs with current values!

### Step 3: Track Interest Growth

- Interest auto-updates when you load the tab
- Click "Recalculate Interest" to refresh values
- Watch your returns grow over time!

## Technical Details

### Database Storage

FDs are stored in the existing `holdings` table with:
- `instrument_type = 'fd'`
- `market = 'IN'`
- `exchange = 'FD'`
- `quantity = 1` (FDs are single units)
- `average_price` = Investment amount
- `current_value` = Investment + Interest
- `pnl` = Interest earned
- `sector` = Interest rate (stored as "7.5% p.a.")

### Interest Calculation Logic

```python
def calculate_fd_returns(investment_amount, investment_date, interest_rate, maturity_date=None):
    # Calculate days elapsed
    days_elapsed = (end_date - investment_date).days

    # Calculate years
    years_elapsed = days_elapsed / 365.0

    # Simple interest formula
    interest_earned = (investment_amount * interest_rate * years_elapsed) / 100.0

    current_value = investment_amount + interest_earned

    return {
        'days_elapsed': days_elapsed,
        'years_elapsed': years_elapsed,
        'interest_earned': interest_earned,
        'current_value': current_value
    }
```

## Limitations

1. **Simple Interest Only**: Does not support compound interest calculations
2. **No Quarterly Payouts**: Assumes interest is paid at maturity
3. **365-Day Year**: Uses 365 days for year calculation (not 366 for leap years)
4. **No TDS Calculation**: Does not account for Tax Deducted at Source
5. **Single Currency**: Only supports INR

## Future Enhancements

1. **Compound Interest**: Support quarterly/monthly compounding
2. **TDS Calculation**: Auto-calculate tax deducted at source
3. **Maturity Alerts**: Notify when FDs are nearing maturity
4. **Interest Payout Tracking**: Track quarterly/monthly interest payouts
5. **Premature Withdrawal**: Calculate penalty for early withdrawal
6. **Renewal Tracking**: Track renewed FDs
7. **Bank-wise Statistics**: Compare returns across banks
8. **Historical Tracking**: Store interest calculation history

## Troubleshooting

### "No valid FD records found"
- Check Excel file has correct column names
- Ensure Bank Name, Investment Amount, Investment Date, Interest Rate columns exist
- Verify data rows are not empty

### Upload Fails
- Ensure file is .xlsx or .xls format
- Check Investment Amount is positive number
- Verify Interest Rate is between 0 and 100
- Ensure Investment Date is valid date format

### Interest Calculation Seems Wrong
- Verify Investment Date is in the past
- Check Interest Rate is entered as number (7.5, not 7.5%)
- Calculation uses simple interest, not compound
- Days elapsed is calculated from investment date to today

### Values Don't Update
- Click "Recalculate Interest" button to refresh
- Interest auto-recalculates when tab loads
- Check that purchase_date is properly stored

## Benefits

✅ **Easy Tracking**: Upload all FDs once, track automatically
✅ **Real-time Values**: Always shows current value and interest
✅ **Visual Analytics**: Charts help understand distribution
✅ **No Manual Calculation**: Interest calculated automatically
✅ **Historical View**: See how long each FD has been running
✅ **Portfolio Overview**: Total value across all FDs at a glance

Track all your bank fixed deposits in one place with automated interest calculations! 🏦
