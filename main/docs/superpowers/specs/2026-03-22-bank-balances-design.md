# Bank Balances Feature - Design Specification

**Date:** 2026-03-22
**Feature:** Bank Balances Tab with Multi-Bank Support and PDF Statement Upload
**Architecture:** Incremental Intelligence with Template Learning

---

## Executive Summary

Add a comprehensive bank balances management system to the portfolio dashboard. Users can upload PDF bank statements from multiple banks, review automatically extracted transaction data, and view advanced analytics including category breakdowns, spending trends, and cash flow analysis.

**Key Innovation:** A self-improving parsing system that learns from successful extractions. The first upload from a bank uses AI/table detection, but subsequent uploads from the same bank use saved templates for instant processing.

**Core Capabilities:**
- Multi-bank account management with card-based interface
- PDF statement upload with hybrid parsing (simple parsers → AI fallback)
- Interactive review interface for verifying extracted transactions
- AI-powered transaction categorization
- Advanced analytics (balance trends, category breakdown, merchant analysis, anomaly detection)
- Complete authentication and authorization system
- Template learning for progressively faster processing

**Migration Note:** Existing Zerodha `Account` records will be linked to the new `User` model via migration. Each existing account will be assigned to a default user created during migration, or users can be prompted to register/login and claim their accounts.

---

## 1. System Architecture

### 1.1 Backend Components

#### New Database Models

**User Model** (`backend/app/models/user.py`)
```python
User:
  - id (PK)
  - email (unique, required)
  - password_hash (bcrypt hashed)
  - full_name
  - created_at, updated_at, last_login_at
  - is_active (boolean)

  Relationships:
    - has_many bank_accounts
    - has_many accounts (Zerodha)
```

**BankAccount Model** (`backend/app/models/bank_account.py`)
```python
BankAccount:
  - id (PK)
  - user_id (FK → users.id, indexed)
  - bank_name (e.g., "HDFC Bank", "SBI")
  - account_number (partially masked in UI)
  - account_type (savings/current/credit)
  - current_balance (Numeric(15,2))
  - currency (default 'INR')
  - last_statement_date (Date)
  - is_active (boolean)
  - created_at, updated_at

  Relationships:
    - belongs_to user
    - has_many statements
    - has_many transactions

  Indexes:
    - idx_bank_accounts_user (user_id)
```

**BankStatement Model** (`backend/app/models/bank_statement.py`)
```python
BankStatement:
  - id (PK)
  - bank_account_id (FK → bank_accounts.id)
  - statement_period_start (Date)
  - statement_period_end (Date)
  - pdf_file_path (encrypted path to uploaded PDF)
  - upload_date (DateTime)
  - parsing_template_id (FK → parsing_templates.id, nullable)
  - status (enum: 'uploaded', 'parsing', 'review', 'approved', 'failed')
  - error_message (Text, nullable)
  - parsed_data (JSON, temporary storage for review)
  - created_at

  Relationships:
    - belongs_to bank_account
    - belongs_to parsing_template (optional)
    - has_many transactions

  Indexes:
    - idx_statements_bank_account (bank_account_id)
    - idx_statements_status (status)
```

**Transaction Model** (`backend/app/models/transaction.py`)
```python
Transaction:
  - id (PK)
  - statement_id (FK → bank_statements.id)
  - bank_account_id (FK → bank_accounts.id, denormalized for queries)
  - transaction_date (Date, indexed)
  - description (Text)
  - merchant_name (String, extracted/inferred)
  - amount (Numeric(15,2))
  - transaction_type (enum: 'credit', 'debit')
  - running_balance (Numeric(15,2))
  - category_id (FK → transaction_categories.id, nullable)
  - category_confidence (Float, 0-1, from AI)
  - verified (Boolean, user confirmed)
  - notes (Text, user-added)
  - created_at, updated_at

  Relationships:
    - belongs_to statement
    - belongs_to bank_account
    - belongs_to category

  Indexes:
    - idx_transactions_bank_account_date (bank_account_id, transaction_date DESC)
    - idx_transactions_category (category_id)
    - idx_transactions_description (description) - for search
    - idx_transactions_filters (bank_account_id, transaction_date, transaction_type, category_id)
    - idx_transactions_description_fts (full-text search on description - PostgreSQL)
```

**ParsingTemplate Model** (`backend/app/models/parsing_template.py`)
```python
ParsingTemplate:
  - id (PK)
  - bank_name (String, e.g., "HDFC Bank")
  - template_version (Integer, for versioning)
  - extraction_config (JSON: table coordinates, column mappings, date format, etc.)
  - success_count (Integer, incremented on each successful use)
  - last_used_at (DateTime)
  - created_from_statement_id (FK → bank_statements.id, reference)
  - is_active (Boolean, mark stale templates as inactive)
  - created_at, updated_at

  Example extraction_config:
  {
    "table_area": [100, 150, 500, 700],  # PDF coordinates
    "columns": {
      "date": 0,
      "description": 1,
      "withdrawal": 2,
      "deposit": 3,
      "balance": 4
    },
    "date_format": "%d/%m/%Y",
    "header_rows": 2,
    "footer_keywords": ["*** End of Statement ***"],
    "currency_symbol": "₹"
  }

  Indexes:
    - idx_parsing_templates_bank (bank_name, is_active)
```

**TransactionCategory Model** (`backend/app/models/transaction_category.py`)
```python
TransactionCategory:
  - id (PK)
  - name (String, e.g., "Groceries", "Utilities", "Shopping")
  - icon (String, emoji or icon class)
  - color (String, hex color for charts)
  - parent_category_id (FK → self, for hierarchy: Shopping → Groceries)
  - keywords (JSON array, for keyword-based matching)
  - is_system (Boolean, system vs user-created categories)
  - created_at

  Relationships:
    - has_many transactions
    - has_many children (self-referential)
    - belongs_to parent (self-referential)

  Default Categories:
    - Income (Salary, Freelance, Interest, Dividends)
    - Housing (Rent, Mortgage, Maintenance)
    - Utilities (Electricity, Water, Internet, Phone)
    - Groceries
    - Dining (Restaurants, Food Delivery)
    - Transportation (Fuel, Public Transport, Ride-sharing)
    - Shopping (Clothing, Electronics, General)
    - Healthcare (Doctor, Pharmacy, Insurance)
    - Entertainment (Movies, Subscriptions, Events)
    - Education
    - Insurance
    - Investments
    - Transfers (Internal account transfers)
    - Uncategorized
```

#### New Services

**PDFParserService** (`backend/app/services/pdf_parser_service.py`)

Core parsing pipeline with template learning:

```python
class PDFParserService:
    @staticmethod
    def extract_text(pdf_path: str) -> str:
        """Extract raw text from PDF using pdfplumber"""

    @staticmethod
    def detect_bank_name(text: str) -> Optional[str]:
        """
        Detect bank name from PDF text using regex patterns.
        Patterns: "HDFC Bank", "State Bank of India", "ICICI Bank", etc.
        Returns: Normalized bank name or None
        """

    @staticmethod
    def find_template(bank_name: str) -> Optional[ParsingTemplate]:
        """
        Find active parsing template for bank.
        Returns most recently used active template.
        """

    @staticmethod
    def extract_with_template(pdf_path: str, template: ParsingTemplate) -> List[dict]:
        """
        Use saved template configuration to extract transactions.
        Fast path - no AI required.
        Returns: List of transaction dicts
        """

    @staticmethod
    def extract_with_pdfplumber(pdf_path: str) -> Tuple[List[dict], float]:
        """
        Auto-detect tables and extract transactions.
        Uses pdfplumber's table detection.
        Returns: (transactions list, confidence score)
        """

    @staticmethod
    def fallback_to_ai(pdf_path: str) -> List[dict]:
        """
        Use Claude/GPT-4 Vision API to extract transactions.
        Converts PDF pages to images, sends to API with structured prompt.
        Expected JSON response:
        {
          "bank_name": "...",
          "account_number": "...",
          "statement_period": {"start": "...", "end": "..."},
          "transactions": [
            {"date": "2024-01-15", "description": "...",
             "debit": null, "credit": 5000, "balance": 25000}
          ]
        }
        """

    @staticmethod
    def validate_extraction(transactions: List[dict]) -> Tuple[float, List[str]]:
        """
        Validate extracted transactions:
        - Dates are sequential
        - Running balance matches: balance[i] = balance[i-1] + credit - debit
        - No missing required fields
        Returns: (confidence_score, list_of_errors)
        """

    @staticmethod
    def parse_statement(statement_id: int) -> dict:
        """
        Main orchestration method. Full pipeline:
        1. Get statement and PDF path
        2. Extract text and detect bank name
        3. Check for existing template
        4. If template exists: use it (fast path)
        5. Else: try pdfplumber auto-detection
        6. If low confidence: fall back to AI
        7. Validate extraction
        8. Save parsed data to statement.parsed_data
        9. Update statement.status to 'review'
        Returns: parsed_data dict
        """
```

**BankStatementService** (`backend/app/services/bank_statement_service.py`)

Handles statement lifecycle:

```python
class BankStatementService:
    @staticmethod
    def process_upload(file, bank_account_id: int, user_id: int) -> int:
        """
        1. Validate file (PDF, size < 10MB, not corrupted)
        2. Check for duplicate (same period already uploaded)
        3. Save PDF to encrypted storage
        4. Create BankStatement record (status='uploaded')
        5. Queue background parsing job
        Returns: statement_id
        """

    @staticmethod
    def get_statement_preview(statement_id: int, user_id: int) -> dict:
        """
        Get parsed transactions for review.
        Verify user owns this statement.
        Returns: {
          "statement": {...},
          "transactions": [...],
          "validation_warnings": [...]
        }
        """

    @staticmethod
    def approve_statement(statement_id: int, corrections: List[dict], user_id: int):
        """
        1. Verify ownership
        2. Bulk insert corrected transactions
        3. Update BankAccount.current_balance (from last transaction)
        4. Update BankAccount.last_statement_date
        5. If first successful parse for this bank: save as template
        6. Mark statement as 'approved'
        7. Invalidate relevant caches
        """

    @staticmethod
    def save_template(statement_id: int, extraction_config: dict) -> int:
        """
        Create new ParsingTemplate from successful extraction.
        Store table coordinates, column mappings, date format.
        Returns: template_id
        """

    @staticmethod
    def detect_duplicate_statement(bank_account_id: int, period_start: date, period_end: date) -> bool:
        """Check if statement for this period already exists"""
```

**TransactionCategorizationService** (`backend/app/services/transaction_categorization_service.py`)

AI-powered categorization with learning:

```python
class TransactionCategorizationService:
    @staticmethod
    def auto_categorize(description: str, amount: float) -> Tuple[int, float]:
        """
        Categorize transaction using:
        1. Keyword matching against category.keywords
        2. If no match: AI API call with prompt
        3. Return category_id and confidence score

        AI Prompt example:
        "Categorize this transaction: 'BigBasket Online Purchase' for -2500 INR.
         Available categories: Groceries, Shopping, Food Delivery, ...
         Return JSON: {category: 'Groceries', confidence: 0.95}"
        """

    @staticmethod
    def bulk_categorize(transactions: List[dict]) -> List[dict]:
        """
        Batch categorize transactions.
        Group by similar merchants for efficiency.
        Returns: transactions with category_id and confidence added
        """

    @staticmethod
    def learn_from_user_correction(transaction_id: int, new_category_id: int):
        """
        When user corrects a category:
        1. Extract merchant/description pattern
        2. Add to category.keywords for future matching
        3. Update similar uncategorized transactions
        """
```

**BankAnalyticsService** (`backend/app/services/bank_analytics_service.py`)

Advanced analytics with caching:

```python
class BankAnalyticsService:
    @staticmethod
    @cache.memoize(timeout=3600)
    def get_balance_trend(bank_account_id: int, days: int = 30) -> dict:
        """
        Time series of daily balances.
        Query last transaction balance per day.
        Returns: {dates: [...], balances: [...]}
        """

    @staticmethod
    @cache.memoize(timeout=3600)
    def get_category_breakdown(bank_account_id: int, period_days: int = 30) -> dict:
        """
        Spending by category (debit transactions only).
        Returns: {labels: [...], values: [...], colors: [...]}
        """

    @staticmethod
    @cache.memoize(timeout=3600)
    def get_cashflow_analysis(bank_account_id: int, period_days: int = 30) -> dict:
        """
        Credits vs debits over time.
        Group by week or month.
        Returns: {periods: [...], credits: [...], debits: [...], net: [...]}
        """

    @staticmethod
    def get_spending_by_merchant(bank_account_id: int, limit: int = 10) -> List[dict]:
        """
        Top merchants by total spending.
        Returns: [{merchant: "Amazon", total: 25000, count: 15}, ...]
        """

    @staticmethod
    def detect_anomalies(bank_account_id: int, threshold: float = 2.0) -> List[dict]:
        """
        Find unusual transactions:
        - Amount > threshold * std_dev from mean
        - Transactions on unusual days/times
        Returns: List of flagged transactions with reasons
        """

    @staticmethod
    def predict_spending(bank_account_id: int, forecast_days: int = 30) -> dict:
        """
        Simple linear regression on historical spending.
        Returns: {predicted_balance: float, confidence_interval: [...]}
        """
```

#### New API Routes

**Authentication Routes** (`backend/app/routes/auth.py`)
```
POST   /api/auth/register              # Create new user
POST   /api/auth/login                 # Login and get JWT token
POST   /api/auth/logout                # Logout (client-side token deletion)
GET    /api/auth/me                    # Get current user info
```

**Bank Accounts Routes** (`backend/app/routes/bank_accounts.py`)
```
GET    /api/bank-accounts              # List user's bank accounts
POST   /api/bank-accounts              # Create new bank account
GET    /api/bank-accounts/:id          # Get bank account details
PUT    /api/bank-accounts/:id          # Update bank account
DELETE /api/bank-accounts/:id          # Delete bank account (soft delete)
```

**Bank Statements Routes** (`backend/app/routes/bank_statements.py`)
```
POST   /api/bank-accounts/:id/statements/upload      # Upload PDF statement
GET    /api/bank-accounts/:id/statements             # List statements for bank
GET    /api/statements/:id                           # Get statement details
GET    /api/statements/:id/preview                   # Get parsed data for review
POST   /api/statements/:id/approve                   # Approve and save transactions
DELETE /api/statements/:id                           # Delete statement
```

**Transactions Routes** (`backend/app/routes/transactions.py`)
```
GET    /api/bank-accounts/:id/transactions           # List transactions with filters
       Query params: date_from, date_to, type, category_id, search, sort_by, order, page, limit
GET    /api/transactions/search                      # Global search across all banks
PUT    /api/transactions/:id                         # Update transaction (category, notes, verified)
POST   /api/transactions/:id/recategorize            # Change category
DELETE /api/transactions/:id                         # Delete transaction
```

**Bank Analytics Routes** (`backend/app/routes/bank_analytics.py`)
```
GET    /api/bank-accounts/:id/analytics/balance-trend
       Query params: days (default: 30)
GET    /api/bank-accounts/:id/analytics/category-breakdown
       Query params: period_days (default: 30)
GET    /api/bank-accounts/:id/analytics/cashflow
       Query params: period_days (default: 30)
GET    /api/bank-accounts/:id/analytics/merchants
       Query params: limit (default: 10)
GET    /api/bank-accounts/:id/analytics/anomalies
       Query params: threshold (default: 2.0)
GET    /api/bank-accounts/:id/analytics/predictions
       Query params: forecast_days (default: 30)
```

### 1.2 Frontend Components

#### New Views

**BankBalancesTab** (`frontend/src/views/dashboard/BankBalancesTab.vue`)

Main view with card grid layout:
- Top section: Card grid of all banks (3-column responsive grid)
- Each card shows: bank name, current balance, monthly change %, upload button
- Click card to select → shows transactions below
- Bottom section: Selected bank's transactions and analytics

**Login/Register Views** (`frontend/src/views/auth/`)
- `Login.vue` - Email/password login form
- `Register.vue` - User registration form

#### New Components

**Bank Management** (`frontend/src/components/bank/`)
```
BankCard.vue
  Props: bank (object)
  Emits: select, upload
  Features: Shows balance, monthly change with color-coded indicator, upload button

BankUploadModal.vue
  Props: bankAccountId
  Emits: success, cancel
  Features: File drag-and-drop, upload progress, parsing status polling

StatementReviewTable.vue
  Props: statement (object with parsed transactions)
  Emits: approve, cancel, update-transaction
  Features:
    - Editable table with inline editing
    - Category dropdown per row
    - Validation warnings (balance mismatches, missing fields)
    - Bulk actions (approve all, verify all)
    - Pagination for large statements

TransactionTable.vue
  Props: bankAccountId
  Features:
    - Sortable columns
    - Inline category editing
    - Pagination
    - Row selection
    - Export to CSV

TransactionFilters.vue
  Props: filters (object)
  Emits: filter-change
  Features:
    - Date range picker
    - Type selector (all/credit/debit)
    - Category multi-select
    - Search input (debounced)
    - Amount range slider

TransactionRow.vue
  Props: transaction, editable
  Emits: update, delete
  Features: Inline editing with validation

CategoryPicker.vue
  Props: selectedCategoryId, categories
  Emits: select
  Features: Searchable dropdown with icons and colors
```

**Charts** (`frontend/src/components/charts/`)
```
CashFlowChart.vue
  Type: Stacked bar chart (credits vs debits by period)
  Library: Chart.js

SpendingByCategoryChart.vue
  Type: Donut/Pie chart
  Features: Interactive legend, click to filter

MerchantBarChart.vue
  Type: Horizontal bar chart
  Shows: Top 10 merchants by spending

BalanceTrendLine.vue
  Type: Line chart with area fill
  Features: Tooltips with date and balance
```

#### New Stores

**Auth Store** (`frontend/src/stores/auth.js`)
```javascript
State:
  - user (object or null)
  - token (string or null)
  - isAuthenticated (boolean)

Actions:
  - register(email, password, fullName)
  - login(email, password)
  - logout()
  - fetchCurrentUser()
  - setAuth(data) - helper to set token and user
```

**Bank Accounts Store** (`frontend/src/stores/bankAccounts.js`)
```javascript
State:
  - bankAccounts (array)
  - selectedBank (object or null)
  - statements (array)
  - currentStatement (object or null - for review)
  - transactions (array)
  - transactionFilters (object)
  - analytics (object)
  - loading (boolean)
  - error (string or null)

Actions:
  - fetchBankAccounts()
  - createBankAccount(data)
  - updateBankAccount(id, data)
  - deleteBankAccount(id)
  - selectBank(id)
  - uploadStatement(bankAccountId, file)
  - fetchStatementPreview(statementId)
  - approveStatement(statementId, corrections)
  - fetchTransactions(bankAccountId, filters)
  - updateTransaction(transactionId, data)
  - recategorizeTransaction(transactionId, categoryId)
  - fetchAnalytics(bankAccountId, type, params)
  - pollStatementStatus(statementId) - polls until status != 'parsing'

Getters:
  - totalBalance - sum of all bank balances
  - filteredTransactions - apply client-side filters
  - transactionsByCategory - group for quick stats
```

---

## 2. Data Flow & Processing

### 2.1 PDF Upload & Parsing Pipeline

**Complete Flow:**

```
1. USER INITIATES UPLOAD
   ↓
   User clicks bank card → BankUploadModal opens
   User selects PDF file
   Frontend validates: file type, size < 10MB
   ↓
   POST /api/bank-accounts/:id/statements/upload
   Body: multipart/form-data with PDF file
   Headers: Authorization: Bearer <token>

2. SERVER RECEIVES UPLOAD
   ↓
   BankStatementService.process_upload():
     - Verify user owns bank_account_id
     - Validate PDF (not corrupted, readable)
     - Check for duplicate statement (same period)
     - Save PDF to: backend/uploads/bank_statements/{user_id}/{bank_account_id}/{uuid}.pdf
     - Encrypt file path before storing in DB
     - Create BankStatement record (status='uploaded')
     - Queue background parsing job (Celery task)
   ↓
   Return: {statement_id: 123, status: 'parsing'} with 202 Accepted

3. BACKGROUND PARSING (Celery Worker or Immediate)
   ↓
   **Note:** If Celery is configured (CELERY_BROKER_URL set), parsing runs asynchronously in a Celery worker. If Celery is not available, parsing runs synchronously in the request handler (blocking, but functional). For production deployments, Celery is strongly recommended for better user experience.

   PDFParserService.parse_statement(statement_id):

     a) Extract Text
        - pdfplumber.open(pdf_path)
        - Extract all text content
        - If < 100 chars: PDF is image-based, skip to AI

     b) Detect Bank Name
        - Regex search for known bank patterns:
          "HDFC Bank", "State Bank of India", "ICICI Bank", "Axis Bank", etc.
        - Normalize to standard name
        - If not detected: mark for user selection later

     c) Find Existing Template
        - Query: ParsingTemplate.filter_by(bank_name=detected_name, is_active=True)
        - Order by last_used_at DESC
        - If found: FAST PATH ↓

     d) FAST PATH: Use Template
        - Extract using saved extraction_config
        - pdfplumber.extract_table(bbox=template.table_area)
        - Map columns using template.columns indices
        - Parse dates using template.date_format
        - Validate extraction (check balances)
        - If validation passes (confidence > 0.9):
            → Set status='review'
            → Increment template.success_count
            → Skip to step 5 (Categorization)
        - If validation fails:
            → Mark template as stale (too many failures)
            → Fall through to step e

     e) AUTO-DETECTION: pdfplumber Table Detection
        - pdfplumber.extract_tables() - auto-detect all tables
        - Infer structure:
            * Find date column (regex: \d{2}/\d{2}/\d{4})
            * Find amount columns (regex: -?\d+,?\d*\.?\d*)
            * Identify debit/credit columns
            * Find balance column (usually last numeric)
        - Extract transactions
        - Validate:
            * Dates sequential
            * Running balance matches: balance[i] = balance[i-1] + credit - debit
            * No missing critical fields
        - If confidence > 0.7:
            → Set status='review'
            → Skip to step 5 (Categorization)
        - Else: fall through to AI

     f) AI FALLBACK: Claude/GPT-4 Vision
        - Convert PDF pages to images (pdf2image)
        - For each page, send to API:

        System Prompt:
        "You are a bank statement parser. Extract transactions from the image
         and return valid JSON. Be precise with amounts and dates."

        User Prompt:
        "Extract all transactions from this bank statement page. Return JSON:
         {
           'bank_name': '...',
           'account_number': '...',
           'statement_period': {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'},
           'transactions': [
             {
               'date': 'YYYY-MM-DD',
               'description': '...',
               'debit': null or amount,
               'credit': null or amount,
               'balance': amount
             }
           ]
         }
         Important: Every transaction must have exactly ONE of debit or credit
         (not both, not neither). Balance must be present for all transactions."

        - Parse JSON response
        - Merge transactions from all pages
        - Validate extraction
        - Set status='review'

     g) Handle Failures
        - If all methods fail:
            → Set status='failed'
            → Store error_message
            → Notify user via UI

4. CATEGORIZATION (for all parsed transactions)
   ↓
   TransactionCategorizationService.bulk_categorize(transactions):

     For each transaction:
       a) Keyword Matching
          - Check description against category.keywords
          - Example: "BigBasket" → keywords: ["bigbasket", "grocery"] → Groceries
          - If match found: assign category_id, confidence=0.8

       b) AI Categorization (if no keyword match)
          - Call AI API:
            Prompt: "Categorize transaction: '{description}' amount: {amount}.
                     Categories: Groceries, Dining, Shopping, Utilities, ...
                     Return JSON: {category: 'Groceries', confidence: 0.95}"
          - Parse response, map category name to category_id

       c) Store category_id and confidence with transaction

5. UPDATE STATEMENT STATUS
   ↓
   - statement.status = 'review'
   - statement.parsed_data = transactions (JSON)
   - db.session.commit()

6. FRONTEND POLLING
   ↓
   Frontend polls: GET /api/statements/:id/preview every 2 seconds
   When status changes to 'review':
     - Stop polling
     - Display StatementReviewTable with parsed transactions
     - Show validation warnings if any

7. USER REVIEW
   ↓
   StatementReviewTable displays:
     - All transactions in editable table
     - Warnings: balance mismatches, missing fields, low confidence categories
     - User can:
         * Edit dates, descriptions, amounts
         * Change categories via dropdown
         * Add notes
         * Mark rows as verified
         * Merge/split transactions (optional feature)

   When satisfied, user clicks "Approve & Save"

8. APPROVAL & SAVE
   ↓
   POST /api/statements/:id/approve
   Body: {
     transactions: [
       {id: temp_id, date: '...', description: '...', amount: ..., category_id: ...},
       ...
     ]
   }

   BankStatementService.approve_statement():
     a) Verify user owns this statement
     b) Bulk insert transactions into Transaction table
     c) Update BankAccount:
         - current_balance = last_transaction.balance
         - last_statement_date = statement.period_end
     d) If this was first successful parse for this bank:
         - Extract extraction pattern (table coords, column indices)
         - Save as new ParsingTemplate
         - Future uploads from same bank will use this template
     e) Update statement.status = 'approved'
     f) Invalidate caches (analytics, etc.)
     g) db.session.commit()

   Return: 200 OK

9. REDIRECT & REFRESH
   ↓
   Frontend:
     - Show success toast: "Statement approved, transactions saved!"
     - Refresh bank account details (new balance)
     - Redirect to transactions view
     - Auto-load analytics
```

### 2.2 Template Learning Details

**What Gets Saved:**
```json
{
  "bank_name": "HDFC Bank",
  "template_version": 1,
  "extraction_config": {
    "table_area": [80, 140, 520, 720],
    "columns": {
      "date": 0,
      "description": 1,
      "cheque_no": 2,
      "withdrawal": 3,
      "deposit": 4,
      "balance": 5
    },
    "date_format": "%d/%m/%Y",
    "header_rows": 3,
    "footer_keywords": ["*** End of Statement ***", "This is system generated"],
    "currency_symbol": "₹",
    "amount_regex": "([0-9,]+\\.?[0-9]*)"
  },
  "created_from_statement_id": 123
}
```

**How It's Used:**
- Next upload from HDFC: template found → direct table extraction using saved coords
- Processing time: ~1-2 seconds (vs 30-60 seconds for AI)
- Cost: $0 (vs ~$0.10-0.50 per AI call)

**Template Versioning:**
- Track success rate per template
- If template fails 3+ times consecutively: mark as stale
- Create new template version from next successful parse
- Keep old versions for historical statements

---

## 3. Authentication & Authorization

### 3.1 User Authentication

**Registration Flow:**
```
Frontend: /register
  ↓
  User enters: email, password, full_name
  Client-side validation: email format, password strength
  ↓
POST /api/auth/register
  ↓
  Backend validates:
    - Email unique (not already registered)
    - Password meets requirements (min 8 chars, etc.)
  ↓
  Create User:
    - Hash password with bcrypt (work factor 12)
    - Store hashed password (never plaintext)
  ↓
  Generate JWT token:
    - Payload: {user_id: 123, iat: timestamp, exp: timestamp + 24h}
    - Sign with SECRET_KEY
  ↓
  Return: {user: {...}, access_token: "eyJ...", expires_in: 86400}
  ↓
Frontend:
  - Store token in localStorage
  - Set Authorization header for all future API calls
  - Redirect to /dashboard
```

**Login Flow:**
```
Frontend: /login
  ↓
POST /api/auth/login {email, password}
  ↓
  Backend:
    - Find user by email
    - Verify password: bcrypt.check_password_hash(stored_hash, provided_password)
    - If invalid: return 401 Unauthorized
  ↓
  Generate JWT token
  Update user.last_login_at
  ↓
  Return: {user, access_token}
  ↓
Frontend: same as registration (store token, redirect)
```

**Token Refresh (Optional Enhancement):**
- Short-lived access tokens (1 hour) + long-lived refresh tokens (7 days)
- When access token expires, use refresh token to get new access token
- More secure than single long-lived token

### 3.2 Authorization on All Endpoints

**Decorator Pattern:**
```python
from flask_jwt_extended import jwt_required, get_jwt_identity

@app.route('/api/bank-accounts', methods=['GET'])
@jwt_required()  # Validates JWT token
def get_bank_accounts():
    user_id = get_jwt_identity()  # Extract user_id from token

    # CRITICAL: Filter by user_id
    accounts = BankAccount.query.filter_by(
        user_id=user_id,
        is_active=True
    ).all()

    return jsonify([acc.to_dict() for acc in accounts])
```

**Ownership Verification Helper:**
```python
def require_ownership(model_class, param_name='id'):
    """
    Decorator to verify user owns the resource.
    Usage: @require_ownership(BankAccount, 'account_id')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_jwt_identity()
            resource_id = kwargs.get(param_name)

            resource = model_class.query.filter_by(
                id=resource_id,
                user_id=user_id
            ).first_or_404()

            # Pass verified resource to handler
            kwargs['resource'] = resource
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage:
@app.route('/api/bank-accounts/<int:account_id>/statements/upload', methods=['POST'])
@jwt_required()
@require_ownership(BankAccount, 'account_id')
def upload_statement(account_id, resource):
    # resource is guaranteed to belong to authenticated user
    # Proceed with upload...
```

**Cascading Authorization:**
- Transaction belongs to Statement belongs to BankAccount belongs to User
- When accessing transaction, verify BankAccount ownership
- Database query: JOIN transactions → bank_accounts WHERE user_id = current_user

### 3.3 Security Best Practices

**Password Hashing:**
```python
from werkzeug.security import generate_password_hash, check_password_hash

# On registration:
password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

# On login:
is_valid = check_password_hash(user.password_hash, provided_password)
```

**SQL Injection Prevention:**
- Use SQLAlchemy ORM (parameterized queries)
- Never use raw SQL with string concatenation
- Validate and sanitize all user inputs

**File Upload Security:**
```python
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_pdf(file):
    # Check extension
    if not file.filename.lower().endswith('.pdf'):
        raise ValidationError("Only PDF files allowed")

    # Check MIME type (not just extension)
    if file.mimetype != 'application/pdf':
        raise ValidationError("Invalid file type")

    # Check size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        raise ValidationError("File too large")

    # Validate PDF structure (detect malicious files)
    try:
        pdf = pdfplumber.open(file)
        pdf.close()
    except:
        raise ValidationError("Invalid or corrupted PDF")
```

**Rate Limiting:**
```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: get_jwt_identity())

@limiter.limit("10 per hour")
@app.route('/api/bank-accounts/<id>/statements/upload', methods=['POST'])
def upload_statement(id):
    # Max 10 uploads per user per hour
```

**CORS Configuration:**
```python
from flask_cors import CORS

CORS(app,
     origins=[os.getenv('FRONTEND_URL')],
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization'])
```

**Encrypted Storage:**
```python
# Encrypt sensitive file paths before storing
from app.utils.encryption import encrypt_string, decrypt_string

# On save:
encrypted_path = encrypt_string(actual_file_path)
statement.pdf_file_path = encrypted_path

# On retrieval:
actual_path = decrypt_string(statement.pdf_file_path)
```

---

## 4. Error Handling & Edge Cases

### 4.1 PDF Parsing Failures

**Image-based PDF (Scanned Document):**
- Detection: pdfplumber extracts < 100 characters
- Action: Skip text extraction, go directly to AI with vision
- User notification: "Processing scanned statement (may take longer)"

**Table Detection Fails:**
- pdfplumber returns empty or malformed tables
- Action: Fall back to AI extraction
- If AI also fails: status='failed', error_message stored
- User sees: "Unable to parse PDF. Please try a different file or contact support."

**Ambiguous Bank Detection:**
- Multiple bank names found or no bank name
- Action: Set status='review' but flag for user selection
- UI shows: "Which bank is this statement from?" with dropdown
- User selects, system saves for next upload from same format

**Date Format Ambiguity:**
- Example: "01/02/2024" could be Jan 2 or Feb 1
- Detection: Try common formats (%d/%m/%Y, %m/%d/%Y, %d-%b-%Y)
- Action: Show warning in review table: "Please verify dates are correct"
- Let user specify format if needed

**Balance Calculation Mismatch:**
```python
# Validation logic:
for i, txn in enumerate(transactions):
    if i == 0:
        continue
    expected_balance = transactions[i-1]['balance'] + txn['credit'] - txn['debit']
    actual_balance = txn['balance']
    if abs(expected_balance - actual_balance) > 0.01:  # Allow small rounding errors
        txn['warning'] = f"Balance mismatch: expected {expected_balance}, got {actual_balance}"
```
- Display warning icon in review table
- User can correct before approving

### 4.2 Duplicate Detection

**Same Statement Uploaded Twice:**
```python
def check_duplicate(bank_account_id, period_start, period_end):
    existing = BankStatement.query.filter(
        BankStatement.bank_account_id == bank_account_id,
        BankStatement.statement_period_start == period_start,
        BankStatement.statement_period_end == period_end,
        BankStatement.status != 'failed'
    ).first()

    if existing:
        raise ValidationError(f"Statement for {period_start} to {period_end} already uploaded")
```

**Hash-based Detection:**
```python
import hashlib

def get_file_hash(file):
    hasher = hashlib.sha256()
    for chunk in iter(lambda: file.read(4096), b""):
        hasher.update(chunk)
    file.seek(0)
    return hasher.hexdigest()

# Before processing:
file_hash = get_file_hash(uploaded_file)
if BankStatement.query.filter_by(file_hash=file_hash).first():
    raise ValidationError("This exact file has already been uploaded")
```

### 4.3 AI Service Failures

**API Timeout or Error:**
```python
import requests
from requests.exceptions import Timeout, RequestException

def call_ai_api(prompt, images):
    try:
        response = requests.post(
            AI_API_URL,
            json={'prompt': prompt, 'images': images},
            headers={'Authorization': f'Bearer {AI_API_KEY}'},
            timeout=60  # 60 second timeout
        )
        response.raise_for_status()
        return response.json()

    except Timeout:
        logger.error("AI API timeout")
        raise AIServiceError("AI service timed out. Please try again.")

    except RequestException as e:
        logger.error(f"AI API error: {e}")
        raise AIServiceError("AI service unavailable. Please try again later.")
```

**Fallback Strategy:**
- For categorization: Fall back to keyword matching, leave uncategorized if no match
- For parsing: Mark statement as failed, allow manual upload of CSV instead
- Queue for retry when service recovers

### 4.4 Large File Handling

**50-Page Statement:**
- Challenge: 500+ transactions, long processing time
- Solutions:
  * Stream processing: Process pages one at a time, update progress
  * Pagination in review UI: Show 100 transactions at a time
  * Background job with progress tracking
  * WebSocket for real-time progress updates

**File Size Limits:**
```python
MAX_PDF_SIZE = 10 * 1024 * 1024  # 10MB
MAX_PDF_PAGES = 100

def validate_pdf_size(pdf_path):
    file_size = os.path.getsize(pdf_path)
    if file_size > MAX_PDF_SIZE:
        raise ValidationError(f"PDF too large ({file_size/1024/1024:.1f}MB). Max 10MB.")

    pdf = pdfplumber.open(pdf_path)
    if len(pdf.pages) > MAX_PDF_PAGES:
        raise ValidationError(f"PDF has {len(pdf.pages)} pages. Max 100 pages.")
```

### 4.5 Template Versioning & Staleness

**Bank Changes PDF Format:**
- Detection: Template-based extraction fails 3 times in a row
- Action:
  ```python
  template.failure_count += 1
  if template.failure_count >= 3:
      template.is_active = False
      # Next upload will create new template version
  ```
- Notification: "We've detected a new statement format. Processing may take longer this time."

**Keep Old Templates for Historical Data:**
- Don't delete old templates
- Use template_version field
- When re-parsing old statements, use their original template

---

## 5. Performance Optimization

### 5.1 Database Optimization

**Critical Indexes:**
```sql
-- Most important indexes for query performance
CREATE INDEX idx_transactions_bank_account_date
    ON transactions(bank_account_id, transaction_date DESC);

CREATE INDEX idx_transactions_category
    ON transactions(category_id);

CREATE INDEX idx_transactions_filters
    ON transactions(bank_account_id, transaction_date, transaction_type, category_id);

-- Full-text search (PostgreSQL)
CREATE INDEX idx_transactions_description_fts
    ON transactions USING gin(to_tsvector('english', description));

-- User ownership lookups
CREATE INDEX idx_bank_accounts_user ON bank_accounts(user_id);
CREATE INDEX idx_accounts_user ON accounts(user_id);
```

**Query Optimization:**
```python
# Bad: N+1 queries
transactions = Transaction.query.filter_by(bank_account_id=account_id).all()
for txn in transactions:
    category = txn.category  # Separate query!

# Good: Eager loading
from sqlalchemy.orm import joinedload

transactions = Transaction.query\
    .options(joinedload(Transaction.category))\
    .filter_by(bank_account_id=account_id)\
    .all()

# Even better: Only load needed fields
transactions = db.session.query(
    Transaction.id,
    Transaction.date,
    Transaction.description,
    Transaction.amount,
    TransactionCategory.name.label('category_name')
).join(TransactionCategory)\
 .filter(Transaction.bank_account_id == account_id)\
 .all()
```

**Pagination:**
```python
# Always paginate large result sets
def get_transactions(bank_account_id, page=1, per_page=50):
    pagination = Transaction.query\
        .filter_by(bank_account_id=bank_account_id)\
        .order_by(Transaction.transaction_date.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return {
        'transactions': [txn.to_dict() for txn in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    }
```

### 5.2 Caching Strategy

**Redis Caching:**
```python
from flask_caching import Cache

cache = Cache(app, config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'CACHE_DEFAULT_TIMEOUT': 3600  # 1 hour
})

# Cache expensive analytics
@cache.memoize(timeout=3600)
def get_category_breakdown(bank_account_id, period_days=30):
    # Expensive GROUP BY query
    result = db.session.query(
        TransactionCategory.name,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction)\
     .filter(Transaction.bank_account_id == bank_account_id)\
     .filter(Transaction.transaction_date >= date.today() - timedelta(days=period_days))\
     .filter(Transaction.transaction_type == 'debit')\
     .group_by(TransactionCategory.id)\
     .all()

    return result

# Cache balance trends
@cache.memoize(timeout=21600)  # 6 hours
def get_balance_trend(bank_account_id, days=30):
    # Complex time-series query
    ...

# Invalidate cache on data changes
def approve_statement(statement_id):
    # ... save transactions ...
    bank_account_id = statement.bank_account_id

    # Clear related caches
    cache.delete_memoized(get_category_breakdown, bank_account_id)
    cache.delete_memoized(get_balance_trend, bank_account_id)
```

**Client-Side Caching:**
```javascript
// Cache analytics data in Pinia store
const analyticsStore = useAnalyticsStore()

// Only fetch if not cached or stale
async function loadAnalytics(bankAccountId, type) {
  const cached = analyticsStore.getCached(bankAccountId, type)

  if (cached && !isStale(cached.timestamp)) {
    return cached.data
  }

  const data = await api.get(`/api/bank-accounts/${bankAccountId}/analytics/${type}`)
  analyticsStore.cache(bankAccountId, type, data)
  return data
}
```

### 5.3 Background Job Processing

**Celery Configuration:**
```python
# backend/celery_app.py
from celery import Celery

celery = Celery(
    'tasks',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Task definition
@celery.task(bind=True, max_retries=3)
def parse_statement_async(self, statement_id):
    try:
        statement = BankStatement.query.get(statement_id)
        statement.status = 'parsing'
        db.session.commit()

        # Run parsing pipeline
        parsed_data = PDFParserService.parse_statement(statement_id)

        # Update statement
        statement.status = 'review'
        statement.parsed_data = parsed_data
        db.session.commit()

    except Exception as e:
        logger.error(f"Parsing failed for statement {statement_id}: {e}")
        statement.status = 'failed'
        statement.error_message = str(e)
        db.session.commit()

        # Retry up to 3 times with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
```

**Progress Tracking:**
```python
# Update task progress
@celery.task(bind=True)
def parse_statement_with_progress(self, statement_id):
    self.update_state(state='PROGRESS', meta={'current': 0, 'total': 100})

    # Extract text
    self.update_state(state='PROGRESS', meta={'current': 20, 'total': 100, 'status': 'Extracting text'})
    text = PDFParserService.extract_text(pdf_path)

    # Detect bank
    self.update_state(state='PROGRESS', meta={'current': 40, 'total': 100, 'status': 'Detecting bank'})
    bank_name = PDFParserService.detect_bank_name(text)

    # Parse transactions
    self.update_state(state='PROGRESS', meta={'current': 60, 'total': 100, 'status': 'Extracting transactions'})
    transactions = PDFParserService.extract_transactions(pdf_path, bank_name)

    # Categorize
    self.update_state(state='PROGRESS', meta={'current': 80, 'total': 100, 'status': 'Categorizing transactions'})
    categorized = TransactionCategorizationService.bulk_categorize(transactions)

    # Done
    self.update_state(state='SUCCESS', meta={'current': 100, 'total': 100, 'status': 'Complete'})
    return categorized
```

### 5.4 Frontend Performance

**Code Splitting:**
```javascript
// Lazy load heavy components
const BankBalancesTab = defineAsyncComponent(() =>
  import('@/views/dashboard/BankBalancesTab.vue')
)

const HeavyChart = defineAsyncComponent({
  loader: () => import('@/components/charts/HeavyChart.vue'),
  loadingComponent: LoadingSpinner,
  delay: 200,
  timeout: 3000
})
```

**Virtual Scrolling:**
```vue
<!-- For 1000+ transactions -->
<template>
  <RecycleScroller
    :items="transactions"
    :item-size="60"
    key-field="id"
    class="scroller"
  >
    <template #default="{ item }">
      <TransactionRow :transaction="item" />
    </template>
  </RecycleScroller>
</template>

<script setup>
import { RecycleScroller } from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'
</script>
```

**Debounced Search:**
```javascript
import { debounce } from 'lodash-es'

const searchQuery = ref('')

const handleSearch = debounce((query) => {
  emit('search', query)
}, 300)  // Wait 300ms after user stops typing

watch(searchQuery, (newQuery) => {
  handleSearch(newQuery)
})
```

**Optimistic Updates:**
```javascript
// Update UI immediately, rollback on error
async function updateCategory(transactionId, newCategoryId) {
  const transaction = transactions.value.find(t => t.id === transactionId)
  const oldCategoryId = transaction.category_id

  // Optimistic update
  transaction.category_id = newCategoryId

  try {
    await api.put(`/api/transactions/${transactionId}`, {
      category_id: newCategoryId
    })
  } catch (error) {
    // Rollback on failure
    transaction.category_id = oldCategoryId
    uiStore.showError('Failed to update category')
  }
}
```

---

## 6. Testing Strategy

### 6.1 Backend Tests

**Unit Tests - Services:**
```python
# tests/backend/services/test_pdf_parser_service.py
class TestPDFParserService:
    def test_detect_hdfc_bank(self):
        text = "HDFC Bank Limited\nCurrent Account Statement\n..."
        assert PDFParserService.detect_bank_name(text) == "HDFC Bank"

    def test_detect_sbi_bank(self):
        text = "STATE BANK OF INDIA\nSavings Account\n..."
        assert PDFParserService.detect_bank_name(text) == "SBI"

    def test_validate_extraction_success(self):
        transactions = [
            {'date': '2024-01-01', 'debit': 0, 'credit': 1000, 'balance': 1000},
            {'date': '2024-01-02', 'debit': 200, 'credit': 0, 'balance': 800},
            {'date': '2024-01-03', 'debit': 0, 'credit': 500, 'balance': 1300}
        ]
        confidence, errors = PDFParserService.validate_extraction(transactions)
        assert confidence > 0.9
        assert len(errors) == 0

    def test_validate_extraction_balance_mismatch(self):
        transactions = [
            {'date': '2024-01-01', 'debit': 0, 'credit': 1000, 'balance': 1000},
            {'date': '2024-01-02', 'debit': 200, 'credit': 0, 'balance': 900}  # Wrong!
        ]
        confidence, errors = PDFParserService.validate_extraction(transactions)
        assert confidence < 0.5
        assert 'balance_mismatch' in errors[0]

# tests/backend/services/test_transaction_categorization_service.py
class TestCategorizationService:
    def test_categorize_grocery_keyword(self):
        category, confidence = TransactionCategorizationService.auto_categorize(
            "BigBasket Online Purchase", -2500
        )
        assert category.name == "Groceries"
        assert confidence > 0.8

    def test_categorize_salary_credit(self):
        category, confidence = TransactionCategorizationService.auto_categorize(
            "Monthly Salary Credit", 75000
        )
        assert category.name == "Income"

    @patch('services.transaction_categorization_service.call_ai_api')
    def test_ai_fallback_for_unknown(self, mock_ai):
        mock_ai.return_value = {'category': 'Entertainment', 'confidence': 0.85}

        category, confidence = TransactionCategorizationService.auto_categorize(
            "Netflix Subscription", -799
        )
        assert category.name == "Entertainment"
        assert confidence == 0.85
        mock_ai.assert_called_once()
```

**Integration Tests - API Endpoints:**
```python
# tests/backend/routes/test_bank_accounts.py
class TestBankAccountsAPI:
    def test_list_bank_accounts_authenticated(self, auth_client, sample_bank):
        response = auth_client.get('/api/bank-accounts')
        assert response.status_code == 200
        assert len(response.json) >= 1
        assert response.json[0]['bank_name'] == sample_bank.bank_name

    def test_list_bank_accounts_unauthenticated(self, client):
        response = client.get('/api/bank-accounts')
        assert response.status_code == 401

    def test_create_bank_account(self, auth_client):
        response = auth_client.post('/api/bank-accounts', json={
            'bank_name': 'ICICI Bank',
            'account_number': '9876543210',
            'account_type': 'savings'
        })
        assert response.status_code == 201
        assert response.json['bank_name'] == 'ICICI Bank'

    def test_cannot_access_other_user_account(self, auth_client, other_user_bank):
        response = auth_client.get(f'/api/bank-accounts/{other_user_bank.id}')
        assert response.status_code == 404  # Not found due to user_id filter

# tests/backend/integration/test_statement_upload_flow.py
class TestStatementUploadFlow:
    def test_complete_upload_approve_flow(self, auth_client, sample_bank, hdfc_pdf):
        # 1. Upload PDF
        upload_resp = auth_client.post(
            f'/api/bank-accounts/{sample_bank.id}/statements/upload',
            data={'file': (hdfc_pdf, 'statement.pdf')},
            content_type='multipart/form-data'
        )
        assert upload_resp.status_code == 202
        statement_id = upload_resp.json['statement_id']

        # 2. Wait for parsing (mock as synchronous in tests)
        # In real test, process_statement_sync(statement_id)

        # 3. Get preview
        preview_resp = auth_client.get(f'/api/statements/{statement_id}/preview')
        assert preview_resp.status_code == 200
        transactions = preview_resp.json['transactions']
        assert len(transactions) > 0

        # 4. Approve statement
        approve_resp = auth_client.post(
            f'/api/statements/{statement_id}/approve',
            json={'transactions': transactions}
        )
        assert approve_resp.status_code == 200

        # 5. Verify transactions saved
        trans_resp = auth_client.get(f'/api/bank-accounts/{sample_bank.id}/transactions')
        assert len(trans_resp.json['transactions']) == len(transactions)

        # 6. Verify balance updated
        bank_resp = auth_client.get(f'/api/bank-accounts/{sample_bank.id}')
        assert bank_resp.json['current_balance'] == transactions[-1]['balance']

        # 7. Verify template created
        template = ParsingTemplate.query.filter_by(bank_name='HDFC Bank').first()
        assert template is not None
        assert template.success_count == 1
```

### 6.2 Frontend Tests

**Component Tests:**
```javascript
// tests/frontend/components/BankCard.test.js
import { mount } from '@vue/test-utils'
import BankCard from '@/components/bank/BankCard.vue'

describe('BankCard', () => {
  it('renders bank details correctly', () => {
    const bank = {
      id: 1,
      bank_name: 'HDFC Bank',
      current_balance: 245678.50,
      monthly_change: 12500
    }

    const wrapper = mount(BankCard, { props: { bank } })

    expect(wrapper.text()).toContain('HDFC Bank')
    expect(wrapper.text()).toContain('₹2,45,678.50')
    expect(wrapper.text()).toContain('↑')  // Positive change icon
  })

  it('emits select event on click', async () => {
    const wrapper = mount(BankCard, { props: { bank: {...} } })
    await wrapper.trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')[0]).toEqual([1])
  })

  it('shows negative change in red', () => {
    const wrapper = mount(BankCard, {
      props: { bank: { monthly_change: -5200 } }
    })
    const changeEl = wrapper.find('.monthly-change')
    expect(changeEl.classes()).toContain('negative')
    expect(changeEl.text()).toContain('↓')
  })
})

// tests/frontend/components/TransactionTable.test.js
describe('TransactionTable', () => {
  it('displays transactions in correct format', () => {
    const transactions = [
      {
        id: 1,
        date: '2024-01-15',
        description: 'BigBasket',
        amount: -2500,
        category: { name: 'Groceries' }
      }
    ]

    const wrapper = mount(TransactionTable, { props: { transactions } })

    expect(wrapper.text()).toContain('2024-01-15')
    expect(wrapper.text()).toContain('BigBasket')
    expect(wrapper.text()).toContain('₹2,500')
    expect(wrapper.text()).toContain('Groceries')
  })

  it('allows inline category editing', async () => {
    const wrapper = mount(TransactionTable, { props: {...} })

    const categorySelect = wrapper.find('select.category')
    await categorySelect.setValue(5)

    expect(wrapper.emitted('update-category')).toBeTruthy()
    expect(wrapper.emitted('update-category')[0][0]).toEqual({
      transaction_id: 1,
      category_id: 5
    })
  })
})
```

**Store Tests:**
```javascript
// tests/frontend/stores/bankAccounts.test.js
import { setActivePinia, createPinia } from 'pinia'
import { useBankAccountsStore } from '@/stores/bankAccounts'
import api from '@/services/api'

vi.mock('@/services/api')

describe('BankAccounts Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('fetches bank accounts successfully', async () => {
    const mockBanks = [
      { id: 1, bank_name: 'HDFC', current_balance: 100000 },
      { id: 2, bank_name: 'SBI', current_balance: 50000 }
    ]

    api.get.mockResolvedValue({ data: mockBanks })

    const store = useBankAccountsStore()
    await store.fetchBankAccounts()

    expect(store.bankAccounts).toHaveLength(2)
    expect(store.bankAccounts[0].bank_name).toBe('HDFC')
  })

  it('uploads statement and polls for completion', async () => {
    const store = useBankAccountsStore()
    const file = new File(['content'], 'statement.pdf', { type: 'application/pdf' })

    api.post.mockResolvedValue({ data: { statement_id: 123, status: 'parsing' } })
    api.get.mockResolvedValueOnce({ data: { status: 'parsing' } })
           .mockResolvedValueOnce({ data: { status: 'review', transactions: [...] } })

    await store.uploadStatement(1, file)

    // Should poll until status is 'review'
    expect(api.get).toHaveBeenCalledTimes(2)
    expect(store.currentStatement.status).toBe('review')
  })
})
```

### 6.3 E2E Tests

```javascript
// tests/e2e/bank-balances-flow.spec.js
import { test, expect } from '@playwright/test'

test.describe('Bank Balances Feature', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login')
    await page.fill('input[type="email"]', 'test@example.com')
    await page.fill('input[type="password"]', 'password')
    await page.click('button:has-text("Login")')
    await expect(page).toHaveURL('/dashboard')
  })

  test('complete bank statement upload flow', async ({ page }) => {
    // Navigate to bank balances
    await page.click('a:has-text("Bank Balances")')

    // Click bank card
    await page.click('.bank-card:has-text("HDFC Bank")')

    // Upload statement
    await page.click('button:has-text("Upload Statement")')
    await page.setInputFiles('input[type="file"]', 'tests/fixtures/hdfc_sample.pdf')
    await page.click('button:has-text("Upload & Parse")')

    // Wait for parsing to complete
    await expect(page.locator('text=Review Transactions')).toBeVisible({ timeout: 60000 })

    // Verify transactions displayed
    const rows = await page.locator('table.review-table tbody tr').count()
    expect(rows).toBeGreaterThan(0)

    // Edit a category
    await page.locator('tbody tr:first-child select.category').selectOption('Groceries')

    // Approve
    await page.click('button:has-text("Approve & Save")')

    // Verify success
    await expect(page.locator('text=Statement approved')).toBeVisible()

    // Verify balance updated
    const balance = await page.locator('.bank-card:has-text("HDFC Bank") .balance').textContent()
    expect(balance).toMatch(/₹[\d,]+/)
  })

  test('filters transactions by category', async ({ page }) => {
    await page.click('a:has-text("Bank Balances")')
    await page.click('.bank-card:has-text("HDFC Bank")')

    // Open filters
    await page.click('button:has-text("Filters")')

    // Select category
    await page.selectOption('select[name="category"]', 'Groceries')
    await page.click('button:has-text("Apply")')

    // Verify filtered results
    await expect(page.locator('tbody tr')).toContainText('Groceries')
  })
})
```

### 6.4 Test Coverage Goals

- **Backend Services:** 80%+ line coverage
- **Backend Routes:** 90%+ coverage (all endpoints tested)
- **Frontend Components:** 70%+ coverage (focus on logic-heavy components)
- **Frontend Stores:** 90%+ coverage (critical for data consistency)
- **E2E Tests:** Cover 3 critical user flows minimum

---

## 7. Deployment & Environment

### 7.1 Environment Variables

**Backend `.env`:**
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/portfolio_db

# Security
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-fernet-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# AI Services
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...

# File Storage
UPLOAD_FOLDER=/path/to/uploads
MAX_UPLOAD_SIZE_MB=10

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# CORS
FRONTEND_URL=http://localhost:5173

# Rate Limiting
RATE_LIMIT_STORAGE_URL=redis://localhost:6379/1
```

**Frontend `.env`:**
```bash
VITE_API_BASE_URL=http://localhost:5000/api
```

### 7.2 Database Migrations

```bash
# Generate migration after model changes
alembic revision --autogenerate -m "Add bank balances tables"

# Review migration file, then apply
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### 7.3 Running Services

**Development:**
```bash
# Backend
cd backend
source venv/bin/activate
python run.py

# Celery worker (separate terminal)
celery -A celery_app worker --loglevel=info

# Frontend
cd frontend
npm run dev

# Redis (if not running as service)
redis-server
```

**Production Considerations:**
- Use Gunicorn for Flask: `gunicorn -w 4 -b 0.0.0.0:5000 app:app`
- Use Supervisor or systemd for Celery workers
- Use Nginx as reverse proxy
- Enable HTTPS with Let's Encrypt
- Use PostgreSQL instead of SQLite
- Enable Redis persistence (RDB or AOF)
- Set up monitoring (Sentry, Datadog, etc.)

---

## 8. Future Enhancements

**Phase 2 Features (Not in Initial Implementation):**
1. **Multi-Account per Bank:** Support multiple accounts (savings + credit card) per bank
2. **Recurring Transactions Detection:** Identify and flag recurring payments
3. **Budget Management:** Set spending limits per category with alerts
4. **Export Functionality:** Export transactions to CSV, Excel, PDF
5. **Mobile App:** React Native app for mobile upload
6. **OCR for Receipts:** Upload receipt photos, extract transaction details
7. **Bank API Integration:** Direct connection to some banks (when available)
8. **Shared Accounts:** Multiple users can access same bank account
9. **Tax Reporting:** Generate tax reports (interest income, deductions)
10. **Goal Tracking:** Save towards financial goals

---

## 9. Success Metrics

**Performance Metrics:**
- PDF parsing time: < 30 seconds for 20-page statement (first time)
- PDF parsing time: < 5 seconds with template (subsequent uploads)
- API response time: < 200ms for transaction list (50 items)
- Page load time: < 2 seconds for dashboard

**Accuracy Metrics:**
- Template extraction accuracy: > 95%
- AI categorization accuracy: > 85%
- Balance validation pass rate: > 90%

**User Experience:**
- Time to first upload: < 2 minutes from signup
- Statement upload success rate: > 95%
- User approval rate (no corrections): > 70%

---

## 10. Summary

This design delivers a comprehensive, production-ready bank balances management system with:

✅ **Intelligent Parsing:** Learns from each upload, gets faster over time
✅ **User Control:** Review interface ensures accuracy before saving
✅ **Advanced Analytics:** Deep insights into spending patterns
✅ **Secure by Default:** Authentication, authorization, encryption throughout
✅ **Scalable Architecture:** Background jobs, caching, optimized queries
✅ **Excellent UX:** Card-based interface, responsive design, real-time feedback

**The system starts simple and grows smarter with use, delivering both immediate value and long-term efficiency gains.**