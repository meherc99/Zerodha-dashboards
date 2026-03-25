# Sample US Holdings Excel File

To test the US Stocks upload feature, create an Excel file (.xlsx) with the following format:

## Required Columns

| Symbol | Quantity | Average Price | Purchase Date |
|--------|----------|--------------|---------------|
| AAPL   | 10       | 150.50       | 2024-01-15    |
| TSLA   | 5        | 240.00       | 2024-02-01    |
| MSFT   | 8        | 380.25       | 2024-01-20    |
| GOOGL  | 3        | 140.00       | 2024-03-01    |
| NVDA   | 12       | 450.75       | 2023-12-15    |

## Column Descriptions

- **Symbol** (Required): Stock ticker symbol (e.g., AAPL, TSLA, GOOGL)
- **Quantity** (Required): Number of shares owned
- **Average Price** (Required): Average purchase price per share in USD
- **Purchase Date** (Optional): Date when the shares were purchased (format: YYYY-MM-DD)

## Notes

1. The file must be in Excel format (.xlsx or .xls)
2. Column names must match exactly (case-sensitive)
3. Empty rows will be skipped automatically
4. Invalid data (negative quantities, invalid symbols) will be logged and skipped
5. When uploaded, the system will automatically fetch current prices from Finnhub API

## Creating the Excel File

You can create this file using:
- Microsoft Excel
- Google Sheets (export as .xlsx)
- LibreOffice Calc
- Any spreadsheet application that exports to Excel format
