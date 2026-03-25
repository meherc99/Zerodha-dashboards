# Quick Start Guide: Fixed Deposits Feature

## Overview

Track all your bank fixed deposits in one place with automated interest calculations!

## Features

✅ Upload FD details from Excel file
✅ Automatic interest calculation (simple interest)
✅ Real-time current value tracking
✅ Bank-wise distribution charts
✅ Detailed FD table with all information
✅ Auto-refresh when tab loads
✅ Manual recalculate button

## Quick Start

### Step 1: Prepare Your Excel File

Create an Excel file (.xlsx) with these columns:

| Bank Name | Investment Amount | Investment Date | Interest Rate | Maturity Date |
|-----------|------------------|-----------------|---------------|---------------|
| HDFC Bank | 100000           | 2024-01-15      | 7.5           | 2025-01-15    |
| SBI       | 200000           | 2023-12-01      | 7.25          | 2024-12-01    |
| ICICI Bank| 150000           | 2024-02-10      | 7.75          | 2025-02-10    |

**Required columns:**
- Bank Name (e.g., HDFC Bank, SBI, ICICI)
- Investment Amount (in INR)
- Investment Date (YYYY-MM-DD format)
- Interest Rate (as number, e.g., 7.5 for 7.5% p.a.)

**Optional:**
- Maturity Date (YYYY-MM-DD format)

### Step 2: Start the Application

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

### Step 3: Upload Your FD Records

1. Open http://localhost:5173 in your browser
2. Click "🏦 Fixed Deposits" in the sidebar
3. Either:
   - Drag and drop your Excel file, OR
   - Click "Select File" to browse

4. Click "Upload & Calculate Returns"
5. Your FDs will appear with calculated interest!

### Step 4: View Your FD Portfolio

You'll see:
- **Summary Cards**: Total investment, current value, interest earned
- **FD Table**: Detailed view of all your fixed deposits
- **Charts**: Bank-wise distribution and top FDs

## Interest Calculation

The system uses **Simple Interest** formula:

```
Interest = (Principal × Rate × Time) / 100
Current Value = Principal + Interest
```

**Example:**
- Investment: ₹100,000
- Rate: 7.5% per annum
- Days Elapsed: 100 days
- Interest Earned: ₹2,055
- Current Value: ₹102,055

## What You'll See

### Summary Cards
1. **Total Investment** - Sum of all principal amounts
2. **Current Value** - Investment + Interest earned
3. **Total Interest Earned** - Total interest across all FDs
4. **Average Return** - Average return percentage

### FD Table
Shows for each FD:
- Bank Name
- Investment Amount (Principal)
- Investment Date
- Interest Rate (% p.a.)
- Days Elapsed
- Interest Earned (calculated)
- Current Value (calculated)

### Charts
- **Bank-wise Distribution** - Pie chart showing FD distribution across banks
- **Top FDs by Value** - Bar chart of largest FDs

## Auto-Refresh Feature

- Interest automatically recalculates when you load the tab
- Click "🔄 Recalculate Interest" anytime to update values
- Values update based on current date

## Example FD Scenarios

### Short-term FD (6 months)
```
Bank: HDFC Bank
Investment: ₹50,000
Date: 2024-03-01
Rate: 7.5%
Maturity: 2024-09-01
```

### Medium-term FD (1 year)
```
Bank: SBI
Investment: ₹100,000
Date: 2024-01-01
Rate: 7.25%
Maturity: 2025-01-01
```

### Long-term FD (3 years)
```
Bank: ICICI Bank
Investment: ₹200,000
Date: 2023-01-01
Rate: 7.75%
Maturity: 2026-01-01
```

## Tips

💡 **Upload Once**: Upload all your FDs at once for complete tracking
💡 **Regular Updates**: Check regularly to see interest growth
💡 **Maturity Tracking**: Include maturity dates to plan reinvestments
💡 **Compare Banks**: Use charts to see distribution across banks

## Troubleshooting

### Upload Fails
- Check Excel file has correct column names
- Ensure all required columns are present
- Verify Investment Amount is positive
- Check Interest Rate is between 0-100
- Ensure dates are in YYYY-MM-DD format

### Interest Seems Wrong
- Calculation uses simple interest (not compound)
- Days elapsed calculated from investment date to today
- Formula: (Amount × Rate × Years) / 100

### Need Help?
Check `FD_IMPLEMENTATION.md` for detailed documentation.

## Next Steps

After uploading your FDs:

1. ✅ View total investment and current value
2. ✅ Track interest earned across all FDs
3. ✅ Monitor days elapsed for each FD
4. ✅ Use charts to analyze distribution
5. ✅ Recalculate interest regularly

Start tracking your fixed deposits today! 🏦💰
