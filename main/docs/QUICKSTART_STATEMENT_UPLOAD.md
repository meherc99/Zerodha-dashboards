# Quick Start: Bank Statement Upload Feature

## Overview

Users can now upload PDF bank statements and review parsed transactions before saving to the database.

## User Flow

### 1. Upload Statement

```
Bank Balances Tab → Click "Upload Statement" on Bank Card
```

**What happens:**
- Upload modal appears
- Drag and drop or click to select PDF
- File is validated (PDF only, max 10MB)
- Click "Upload" button
- Progress bar shows upload status
- Backend parses the PDF
- Status changes to "Parsing..." (polls every 2 seconds)

### 2. Review Transactions

**Automatic transition when parsing completes:**
- Review modal opens automatically
- Shows parsed transactions in a table
- Displays warnings if any (balance mismatches, low confidence)

**User actions:**
- Review transaction details
- Edit categories via dropdown
- Add notes to transactions
- Check summary (total debits, credits, net change)
- Click "Approve & Save" to finalize

### 3. Completion

- Transactions are saved to database
- Bank account balance is updated
- Modal closes
- Success notification appears

## API Endpoints Used

### Upload Flow
```
POST /api/bank-accounts/:id/statements/upload
→ Returns: { statement_id }

GET /api/statements/:id
→ Returns: { status, error }
→ Poll until status = 'review' or 'failed'
```

### Review Flow
```
GET /api/statements/:id/preview
→ Returns: { transactions, warnings }

POST /api/statements/:id/approve
→ Body: { transactions: [...] }
→ Saves to database
```

### Categories
```
GET /api/categories
→ Returns: [{ id, name, color, icon, ... }]
```

## Component Architecture

```
BankBalancesTab.vue
  ├─ BankCard.vue (emits 'upload' event)
  ├─ BankUploadModal.vue (Teleport to body)
  └─ StatementReviewModal.vue (Teleport to body)
```

## State Management

### Upload Modal State
```javascript
bankAccountsStore.uploadModal = {
  isOpen: boolean,
  bankAccountId: number,
  statementId: number,
  status: 'uploading' | 'parsing' | 'review' | 'failed',
  progress: 0-100,
  error: string | null
}
```

### Review Modal State
```javascript
bankAccountsStore.reviewModal = {
  isOpen: boolean,
  statementId: number,
  transactions: Transaction[],
  warnings: Warning[],
  loading: boolean,
  error: string | null
}
```

## Transaction Structure

```javascript
{
  date: '2024-03-26',
  description: 'Payment to XYZ',
  debit: 5000.00,
  credit: null,
  balance: 95000.00,
  category_id: 3,
  note: 'Optional user note',
  confidence: 0.85  // AI categorization confidence
}
```

## Validation Rules

### File Upload
- File type: PDF only (.pdf)
- File size: Maximum 10MB
- Drag and drop supported
- Single file only

### Transaction Review
- Category is optional (can be null)
- Notes are optional
- Low confidence (<0.7) transactions highlighted in yellow
- All transactions must have valid date, amount, balance

## Error Handling

### Upload Errors
- Invalid file type → Red error message below drop zone
- File too large → Red error message below drop zone
- Upload failed → Error section with retry button
- Parsing timeout (2 min) → Error with retry option

### Review Errors
- Failed to load preview → Error state with retry button
- Failed to approve → Error notification, modal stays open
- Network errors → Caught and displayed to user

## Styling Notes

### Upload Modal
- Dashed border drag zone
- Purple gradient primary button
- Green checkmark when file selected
- Spinner during parsing
- Progress bar with gradient

### Review Modal
- Large modal (1200px max width)
- Yellow warning section
- Transaction table with sticky header
- Color-coded amounts (red/green)
- Category dropdowns with colored borders
- Inline note inputs

## Testing Tips

### Manual Testing
1. Create a test bank account
2. Prepare a sample PDF statement
3. Test upload with valid PDF
4. Test upload with invalid file (should reject)
5. Test file size limit (create >10MB PDF)
6. Verify parsing status updates
7. Review transaction data accuracy
8. Test category editing
9. Test note adding
10. Verify approve workflow

### Expected Backend Behavior
- Upload should return statement_id immediately
- Status should transition: uploaded → parsing → review
- Preview should return transactions array
- Approve should create Transaction records
- Bank account balance should update

## Common Issues

### Modal not opening
- Check `bankAccountsStore.uploadModal.isOpen`
- Verify BankCard emits 'upload' event
- Check console for errors

### Categories not loading
- Verify GET /api/categories works
- Check categories store state
- Look for JWT token issues

### Polling not working
- Check network tab for GET /api/statements/:id calls
- Verify 2-second interval
- Check for max attempts (60)

### Approve fails
- Verify transactions data format
- Check statement_id is correct
- Look for validation errors in backend

## Development Commands

### Start Backend
```bash
cd backend
source venv/bin/activate
python run.py
```

### Start Frontend
```bash
cd frontend
npm run dev
```

### Build Frontend
```bash
cd frontend
npm run build
```

## File Locations

**Frontend:**
- `/frontend/src/components/bank/BankUploadModal.vue`
- `/frontend/src/components/bank/StatementReviewModal.vue`
- `/frontend/src/stores/categories.js`
- `/frontend/src/stores/bankAccounts.js` (updated)
- `/frontend/src/views/dashboard/BankBalancesTab.vue` (updated)

**Backend:**
- `/backend/app/routes/categories.py` (new)
- `/backend/app/routes/bank_statements.py` (existing)
- `/backend/app/models/transaction_category.py`
- `/backend/app/models/bank_statement.py`
- `/backend/app/models/transaction.py`

## Next Steps

1. Implement PDF parsing service (if not done)
2. Add category seeding migration
3. Add unit tests for components
4. Add E2E tests for upload flow
5. Implement parsing templates for different banks
6. Add transaction search/filter
7. Add bulk categorization
8. Add transaction export

---

**Last Updated:** March 26, 2026
**Status:** Implementation Complete ✅
