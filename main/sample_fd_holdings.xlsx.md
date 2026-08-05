# Sample Fixed Deposit Excel File

To test the Fixed Deposits upload feature, create an Excel file (.xlsx) with the following format:

## Required Columns

| Bank Name | Investment Amount | Investment Date | Interest Rate | Maturity Date |
|-----------|------------------|-----------------|---------------|---------------|
| HDFC Bank | 100000           | 2024-01-15      | 7.5           | 2025-01-15    |
| SBI       | 200000           | 2023-12-01      | 7.25          | 2024-12-01    |
| ICICI Bank| 150000           | 2024-02-10      | 7.75          | 2025-02-10    |
| Axis Bank | 75000            | 2024-03-01      | 7.5           | 2024-09-01    |
| Yes Bank  | 50000            | 2023-11-15      | 8.0           | 2024-11-15    |

## Column Descriptions

- **Bank Name** (Required): Name of the bank where FD is held (e.g., HDFC Bank, SBI, ICICI)
- **Investment Amount** (Required): Principal amount invested in INR
- **Investment Date** (Required): Date when FD was booked (format: YYYY-MM-DD)
- **Interest Rate** (Required): Annual interest rate as a number (e.g., 7.5 for 7.5% per annum)
- **Maturity Date** (Optional): Date when FD matures (format: YYYY-MM-DD)

## Interest Calculation

The system automatically calculates:
- **Days Elapsed**: Number of days since investment date
- **Interest Earned**: Using simple interest formula: `(Principal × Rate × Time) / 100`
- **Current Value**: Principal + Interest Earned

### Formula Details

```
Interest Earned = (Investment Amount × Interest Rate × Years Elapsed) / 100
Current Value = Investment Amount + Interest Earned
Years Elapsed = Days Elapsed / 365
```

### Example Calculation

For an FD with:
- Investment Amount: ₹100,000
- Interest Rate: 7.5% p.a.
- Investment Date: 2024-01-15
- Days Elapsed: 100 days (approx.)

```
Years Elapsed = 100 / 365 = 0.274 years
Interest Earned = (100000 × 7.5 × 0.274) / 100 = ₹2,055
Current Value = 100000 + 2055 = ₹102,055
```

## Notes

1. The file must be in Excel format (.xlsx or .xls)
2. Column names must match exactly (case-sensitive)
3. Empty rows will be skipped automatically
4. Invalid data (negative amounts, invalid dates) will be logged and skipped
5. Interest is calculated from investment date to current date (or maturity date if provided)
6. Simple interest method is used (not compound interest)

## Creating the Excel File

You can create this file using:
- Microsoft Excel
- Google Sheets (export as .xlsx)
- LibreOffice Calc
- Any spreadsheet application that exports to Excel format

## Auto-Refresh Feature

- Interest values are automatically recalculated when you load the tab
- Click "Recalculate Interest" button to update values on demand
- Values update dynamically as time passes since investment date

## Sample Data Scenarios

### Short-term FD
```
Bank Name: HDFC Bank
Investment: ₹50,000
Date: 2024-03-01
Rate: 7.5%
Maturity: 2024-09-01 (6 months)
```

### Long-term FD
```
Bank Name: SBI
Investment: ₹200,000
Date: 2023-01-01
Rate: 7.25%
Maturity: 2026-01-01 (3 years)
```

### High-rate FD
```
Bank Name: Yes Bank
Investment: ₹100,000
Date: 2024-01-01
Rate: 8.5%
Maturity: 2025-01-01 (1 year)
```
