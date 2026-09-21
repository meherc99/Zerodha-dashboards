# Zerodha Family Portfolio Dashboard — Wiki & Changelog

> Single source of truth for the project's history, features, data formats, API,
> database schema, configuration, and fixes.
>
> - **Last updated:** 2026-09-22
> - **Current database head:** `855036219916`
> - **Canonical layout:** backend under [src/backend](../src/backend), frontend under [src/frontend](../src/frontend)
> - **Environment:** a single consolidated [.env](../.env) at the repository root

This document consolidates every historical implementation, quickstart, and
review document into one place. The three READMEs hold the *at-a-glance* facts;
this wiki holds the *detailed* record:

- Root overview and setup: [README.md](../README.md)
- Backend detail: [src/backend/README.md](../src/backend/README.md)
- Frontend detail: [src/frontend/README.md](../src/frontend/README.md)

---

## Table of contents

1. [Product overview](#1-product-overview)
2. [Current architecture](#2-current-architecture)
3. [Changelog](#3-changelog)
4. [Feature reference](#4-feature-reference)
5. [Import data formats](#5-import-data-formats)
6. [API reference](#6-api-reference)
7. [Database migration history](#7-database-migration-history)
8. [Configuration and environment](#8-configuration-and-environment)
9. [Behavior contracts](#9-behavior-contracts)
10. [Testing](#10-testing)
11. [Known limitations and future enhancements](#11-known-limitations-and-future-enhancements)
12. [Component change map](#12-component-change-map)
13. [Contributor checklist](#13-contributor-checklist)

---

## 1. Product overview

A self-hosted Flask + Vue application for reviewing a family's investments
without mixing account ownership or currencies. It tracks:

- Indian equities (Zerodha Kite);
- Coin mutual funds;
- US equities (spreadsheet import + Finnhub quotes);
- fixed deposits (spreadsheet import + simple-interest estimates);
- bank balances, PDF statements, transactions, and cash analytics.

Ownership and currency boundaries are explicit:

- every Zerodha account and bank account belongs to exactly one dashboard user;
- every portfolio snapshot belongs to exactly one Zerodha account;
- **Family** scope combines only the latest completed snapshot from each owned,
  active account; **Member** scope targets exactly one owned account;
- domestic assets and fixed deposits stay in INR; US holdings stay in USD; bank
  accounts keep their configured INR/USD/EUR/GBP currency;
- amounts in different currencies are never silently added or converted.

---

## 2. Current architecture

```text
Zerodha-dashboards/
├── .env                        # Single consolidated environment file (root)
├── docker-compose.yml          # Postgres + backend + frontend services
├── README.md                   # Root overview and setup
├── docs/
│   └── wiki.md                 # This document
└── src/
    ├── backend/
    │   ├── alembic/versions/   # Ordered, tested schema upgrades
    │   ├── app/
    │   │   ├── models/         # Ownership-aware SQLAlchemy models
    │   │   ├── routes/         # Authenticated HTTP boundary
    │   │   ├── services/       # Portfolio, import, statement, analytics logic
    │   │   └── utils/          # Auth, encryption, validation, rate limiting
    │   ├── scripts/            # One-off maintenance scripts
    │   ├── tests/              # Backend unit, route, migration, security tests
    │   ├── run.py              # Sole entry point that starts the scheduler
    │   └── wsgi.py             # Gunicorn entry point
    └── frontend/
        ├── src/
        │   ├── components/     # Dashboard, chart, bank, common components
        │   ├── stores/         # Pinia state and request orchestration
        │   ├── utils/          # Currency, holdings, session, query helpers
        │   └── views/          # Auth, account, and asset pages
        ├── tests/              # Vitest contracts and store tests
        └── vite.config.js      # envDir points to the repo-root .env
```

Key structural rules:

- `create_app()` constructs the Flask application **without** starting
  background threads, keeping imports, Alembic, and tests deterministic.
- [src/backend/run.py](../src/backend/run.py) is the only normal entry point
  that starts the APScheduler worker.
- Both backend entry points and Alembic load the **root** `.env`; Vite's
  `envDir` also points to the root so a single file configures the whole stack.

---

## 3. Changelog

Entries are reverse-chronological. Fixes are written as **Issue → Solution**.
Where a source document did not record a calendar date, the entry is labeled
accordingly rather than inventing one.

### 2026-09-22 — Repository restructure and environment consolidation

**Structure**

- Moved the backend and frontend under a top-level `src/` directory
  (`src/backend`, `src/frontend`).
- Consolidated the previously separate `backend/.env` and `frontend/.env`
  files into a single [.env](../.env) at the repository root.

**Refactors to read the root `.env`**

- [src/backend/run.py](../src/backend/run.py) now loads the root `.env`
  explicitly (`../../.env`) instead of relying on the current working
  directory.
- [src/backend/alembic/env.py](../src/backend/alembic/env.py) was pointed at the
  root `.env` (`../../../.env`); it previously loaded the now-removed
  `src/backend/.env`.
- [src/frontend/vite.config.js](../src/frontend/vite.config.js) sets `envDir` to
  the repository root so Vite reads `VITE_*` values from the shared file.
- [docker-compose.yml](../docker-compose.yml) `backend` service `env_file` was
  changed from `./backend/.env` to `./.env`.

**`.env` cleanup fixes**

- **Issue:** the merged file contained two overlapping templates; empty
  duplicate keys appeared *after* real values and silently overrode them (most
  importantly a blank `JWT_SECRET_KEY` clobbered the real one, which breaks the
  production requirement that `SECRET_KEY` and `JWT_SECRET_KEY` be distinct).
  **Solution:** deduplicated to single keys, generated a distinct valid
  `JWT_SECRET_KEY`, and grouped variables by concern.
- **Issue:** several variables were no longer read by any code
  (`ACCOUNT_ALIASES`, `SELF_*`/`SPOUSE_*`/`PARENTS_*` aliases, `KITE_API_KEY`,
  `KITE_API_SECRET`, `DB_PATH`, `FLASK_APP`). **Solution:** removed them; Kite
  credentials are stored encrypted per-account in the database, not in the
  environment.
- Re-added the two frontend variables the client actually reads
  (`VITE_API_BASE_URL`, `VITE_DEMO_MODE`) under a dedicated section.

**Documentation**

- Consolidated all `docs/*.md` implementation, quickstart, and review files into
  this single wiki and slimmed the three READMEs to at-a-glance summaries that
  link here.

### 2026-08-05 and later — Post-consolidation schema additions

Three migrations were added after the 2026-07-31 hardening release and advance
the head from `b15a7e4c2d90` to the current `855036219916`:

- **`c3a7d9e81f05` — add `needs_reauth` to accounts** (2026-08-05). Records when
  a Zerodha account's Kite session has expired so the UI can prompt a reconnect
  without treating the account as broken.
- **`a04d1b7c8e92` — make Kite credentials optional.** Accounts can now be
  created with only a name and populated with manually imported holdings (fixed
  deposits, US stocks) without Zerodha Kite Connect credentials. Credentials can
  be added later via a `PUT` request.
- **`855036219916` — consolidate `portfolio_timeseries` to daily buckets**
  (current head). Each row's datetime is normalized to UTC midnight so multiple
  intraday syncs update a single authoritative point per account-day-currency
  rather than scattering many rows. Rows arising from the same calendar day are
  deduplicated by keeping the one with the latest original datetime.

### 2026-07-31 — Consolidation and hardening release (major)

A large security, multi-tenant, and data-integrity pass. The existing
Flask/Vue structure was retained and clarified rather than replaced. Database
head at the time: `b15a7e4c2d90`. Recorded validation at release: **329**
backend tests passing, **83** frontend tests across **9** Vitest files, Vite
production build transforming **465** modules, one Alembic head.

**Frontend changes**

- Reorganized into explicit authenticated routes with lazy-loaded dashboard
  child pages and an auth-bootstrap guard so a stored session is never briefly
  treated as logged out. Routes: `/dashboard/overview`, `/dashboard/stocks`,
  `/dashboard/mutual-funds`, `/dashboard/us-stocks`, `/dashboard/fixed-deposits`,
  `/dashboard/bank-balances`, `/accounts`.
- Rebuilt the shell and sidebar (page title, active-route styling, collapsible
  mobile menu, touch-friendly controls, stable nested content area, safe logout).
- Added reusable visual primitives (KPI/summary cards, chart panels with
  loading/empty/error states, responsive line/bar/pie wrappers, desktop tables
  that become cards on narrow screens).
- Added explicit **Family** and **Member** scope handling in
  `AccountSelector.vue` with safe rebinding, Family-mode import owner selection,
  and single-path reloads that ignore stale responses.
- Introduced one shared search/filter/sort implementation for holdings
  (`utils/holdings.js`) and for transactions (`utils/transactions.js`), matched
  by validated backend query parameters.
- Added dedicated Overview, Indian Stocks, Mutual Funds (folio-aware), US Stocks
  (USD, provenance, all-or-nothing refresh), Fixed Deposits (simple-interest
  estimates), and Bank Balances pages.
- Centralized currency display in `utils/currency.js` (ISO normalization,
  `Intl.NumberFormat`, per-currency groups instead of a false aggregate).
- Hardened session/request handling: tab-scoped `sessionStorage` JWT, single
  Axios client with bearer injection, `401` cleanup, request generations and
  `AbortController` so late responses cannot overwrite newer state.

**Backend changes**

- Deterministic, production-safe application factory: overrides applied before
  extension init; unknown/omitted environments never fall back to development;
  production requires distinct ≥32-byte Flask/JWT secrets, a valid Fernet key,
  explicit non-wildcard CORS, and database-backed rate limiting; scheduler
  attached but started only by `run.py`; security and no-cache headers on API
  responses (`X-Content-Type-Options`, `X-Frame-Options: DENY`, API CSP,
  `Referrer-Policy`, `Permissions-Policy`, `Cache-Control: no-store`, HSTS in
  secure production).
- Authentication: normalized-email registration, 8–1024 char passwords,
  PBKDF2-SHA256 hashing, active-user checks, database-persisted JWT revocation on
  logout, bounded auth rate limits. New models `RevokedToken` and
  `RateLimitBucket`.
- Tenant isolation across API and services (per-user unique account names,
  non-null owners, ownership checks on every sync/import/analytics/reconnect,
  request-aware JWT subject caching).
- Encryption: Kite API keys/secrets/access tokens and full bank account numbers
  encrypted with Fernet; only last-four stored for display; sensitive fields
  omitted from serialization.
- Account-scoped **immutable** snapshots with `account_id`, `batch_id`,
  `status`, `trigger`, currency, and error metadata; reads use only the latest
  completed snapshot per account; concurrent writers serialized via
  `Account.portfolio_version`.
- Hardened Kite sync, spreadsheet upload boundary, US import/refresh integrity,
  FD `Decimal` calculations, owner/currency-aware analytics, permanent bank
  account deletion, private fail-closed statement storage, retry-safe statement
  lifecycle, transaction/balance integrity, system-controlled category taxonomy,
  bank analytics contracts, and a database-backed rate limiter.

**Fixes (Issue → Solution)**

These resolve gaps found during earlier development and the 2026-03-27 review:

- **Mixed-currency false totals.** *Issue:* INR and USD were summed into a
  single misleading number. *Solution:* per-currency summary groups; the
  Overview renders separate INR/USD sections and never implicitly converts.
- **A failed refresh could replace good data.** *Issue:* global timestamp
  snapshots meant a failed sync overwrote the last good state. *Solution:*
  account-scoped immutable snapshots; failed attempts are recorded but never
  become current; reads use the latest *completed* snapshot.
- **Brokerage access token reached the browser.** *Issue:* the legacy
  `POST /api/auth/access-token` flow returned tokens client-side. *Solution:*
  the backend exchanges the one-time `request_token` server-side, encrypts the
  access token, and the old endpoint now returns `410 Gone`; reconnect uses a
  server-owned login URL.
- **Concurrent snapshot writers could interleave.** *Issue:* simultaneous
  writers could publish a partial snapshot. *Solution:* `portfolio_version`
  compare-and-set; the losing writer fails cleanly.
- **US price refresh could publish mixed-age data.** *Issue:* partial quote
  success produced a snapshot mixing fresh and stale prices. *Solution:*
  all-or-nothing refresh per account; a new snapshot is published only when
  every symbol receives a valid quote, otherwise positions remain visibly at
  import cost.
- **US/FD imports skipped invalid rows silently.** *Issue:* the initial import
  logged and skipped bad rows, so a malformed sheet produced a partial,
  misleading portfolio. *Solution:* all-or-nothing validation — any invalid,
  duplicate, non-finite, or out-of-precision row rejects the entire workbook
  before any replacement snapshot is created.
- **FD values used float math.** *Issue:* floating-point accrual produced
  rounding drift. *Solution:* `Decimal` with round-half-up money quantization;
  accrual stops at maturity; values are disclosed as estimates.
- **Spreadsheet uploads were an attack surface.** *Issue:* unbounded uploads and
  user-supplied filenames. *Solution:* `MAX_UPLOAD_BYTES` enforcement,
  `.xlsx`/`.xls` signature checks, `.xlsx` archive caps (2,000 members / 50 MiB
  expanded), randomized private temp paths, and cleanup.
- **Statements could be approved twice or overlap.** *Issue:* duplicate PDFs and
  overlapping periods corrupted balances. *Solution:* SHA-256 content hashes,
  inclusive-boundary overlap detection, and claim-once parse/approval leases.
- **Statement templates leaked across tenants.** *Issue:* user-derived layouts
  were learned into a global object. *Solution:* private statement layouts are
  no longer learned globally; legacy templates remain migration-compatible.
- **Late async responses overwrote newer state.** *Issue:* a slow response from a
  previous scope/account clobbered the current selection. *Solution:* request
  generations and `AbortController` guards.
- **Logout did not invalidate tokens.** *Issue:* the review noted logout was
  client-side only. *Solution:* database-persisted JWT revocation checked on
  every protected request.
- **Rate limiter was unverified and process-local.** *Issue:* the review could
  not confirm the limiter or production storage. *Solution:*
  `utils/rate_limiter.py` with hashed bucket keys, database-backed fixed-window
  counters in production, expired-bucket cleanup, and startup rejection of
  process-local counters in production; covered by tests.
- **New environment variables were undocumented.** *Issue:* `ANTHROPIC_API_KEY`,
  `OPENAI_API_KEY`, `CELERY_BROKER_URL` were missing from docs. *Solution:*
  documented in the environment configuration (now the root `.env` and the
  backend README table).
- **Orphaned pre-auth accounts were invisible.** *Issue:* accounts created
  before user ownership had `user_id = NULL`. *Solution:* the
  [migrate_orphaned_accounts.py](../src/backend/scripts/migrate_orphaned_accounts.py)
  helper assigns them to a user (see [§8](#8-configuration-and-environment)).
- **PDF file paths stored as plaintext (partial).** *Issue:* the spec asked for
  encrypted paths. *Solution (mitigation):* paths are never serialized, storage
  is owner-only (`0700`/`0600`), traversal is file-descriptor-relative with
  `O_NOFOLLOW`, and startup fails closed on symlinks/special files. Full path
  encryption remains a documented, non-blocking deviation.
- **Synchronous PDF parsing blocked requests (partial).** *Issue:* large PDFs
  blocked the request thread. *Solution:* optional Celery support via
  `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`; when unset, parsing runs
  synchronously as before.

Still deferred by design: AI-assisted PDF parsing and AI categorization remain
optional (gated behind provider keys); PostgreSQL full-text search on
transaction descriptions still uses `LIKE` queries.

### 2026-03-27 — Bank analytics

New service [bank_analytics_service.py](../src/backend/app/services/bank_analytics_service.py)
and routes [bank_analytics.py](../src/backend/app/routes/bank_analytics.py),
built test-first. All endpoints are JWT-protected and ownership-checked,
returning `404` (not `403`) for unauthorized access to avoid information leakage.
Analytics use only verified transactions; category breakdown counts debits only;
balance trend uses the last transaction per day. Recorded results: **22/22**
analytics tests passing; overall backend **199/200** (the single failure was a
pre-existing, unrelated PDF-upload test). Endpoints delivered:

- `GET /analytics/balance-trend` (`days`, default 30) — daily balance series.
- `GET /analytics/category-breakdown` (`period_days`, default 30) — spending by
  category with percentages summing to 100%.
- `GET /analytics/cashflow` (`period_days`, default 30) — credits vs debits per
  week with net.
- `GET /analytics/top-merchants` (`limit`, default 10) — top merchants with
  totals, counts, and averages; merchant extraction recognizes common brands
  (Amazon, Swiggy, Zomato, …), falls back to `merchant_name`, then to the first
  20 characters of the description.

Later hardened (2026-07-31) to add `anomalies` (statistical detection, SD > 2.0)
and `predictions` (linear regression via numpy), bounded period parameters,
exact transaction counts, and system-category redaction.

### 2026-03-27 — Code review (Grade A-, 88%)

Independent senior review of the Bank Balances feature. **0 critical**, **4
major**, **6 minor** issues; grades: Requirements A- (90%), Code Quality A-
(90%), Architecture A (92%), Testing A (95%), Security B+ (85%), Performance B+
(85%), Documentation C+ (75%). Highlighted strengths: complete normalized schema
with cascade deletes and composite indexes (e.g.
`idx_transactions_bank_account_date (bank_account_id, transaction_date DESC)`);
the parsing-template learning system (auto-deactivation when failure rate > 30%
with ≥5 failures); JWT auth with user-id-from-token authorization; comprehensive
12-file test suite. The major/minor findings and their resolutions are captured
in the 2026-07-31 **Fixes** section above.

### 2026-03-26 — Bank statement upload and review UI + preview/approve API

**Task 3.6 (backend):** added `GET /api/statements/:id/preview` (auto-categorizes
and returns validation warnings for statements in `review` status) and
`POST /api/statements/:id/approve` (validates and bulk-inserts transactions,
updates `current_balance` and `last_statement_date`, sets status `approved`).
Validation warning types: `missing_date` (error), `missing_amount` (error),
`balance_mismatch` (warning, 0.01 tolerance), `low_confidence_category`
(warning, confidence < 0.6). Delivered **13** passing tests (6 preview, 7
approve).

**Frontend (Status: DONE, ~1,885 lines across 12 files):** `BankUploadModal.vue`
(drag-and-drop PDF upload, type/size validation, progress, 2-second status
polling with 60-attempt / 2-minute timeout) and `StatementReviewModal.vue`
(≤1200px transaction table, warning section, editable categories/notes,
low-confidence row highlighting < 0.7, debit/credit/net summary). Added
`stores/categories.js` (5-minute cache) and extended `stores/bankAccounts.js`
with `uploadModal`/`reviewModal` state and actions. New API methods:
`uploadStatement`, `getStatement`, `getStatementPreview`, `approveStatement`,
`getCategories`. New backend route `GET /api/categories` (JWT-required, ordered
by parent then name). Design system: purple/blue gradient (#667eea → #764ba2),
16px rounded modals, Teleport-to-body, mobile full-screen.

### March 2026 — Bank Balances feature foundation

Introduced the bank domain (Tasks 3.2–3.6). Statement upload API:
`POST /api/bank-accounts/:id/statements/upload`
(PDF only, ≤10 MB, `202 Accepted`, UUID-named storage under
`uploads/bank_statements/{user_id}/{account_id}/{uuid}.pdf`),
`GET /api/bank-accounts/:id/statements`, `GET /api/statements/:id`,
`DELETE /api/statements/:id` (removes DB row, PDF, and empty dirs). Statement
status states: `uploaded → parsing → review → approved`, plus `failed`.
Unauthorized access returns `404` to prevent disclosure; **21** statement-route
tests. Models added: `User`, `BankAccount`, `BankStatement`, `Transaction`,
`ParsingTemplate`, `TransactionCategory`. Services: PDF parsing with template
learning, keyword-based transaction categorization with
`learn_from_user_correction()`.

### Undated — US Stocks and Fixed Deposits features

> Source documents did not record calendar dates for these features.

**US Stocks.** Added Finnhub integration and Excel import. New services
`finnhub_service.py` and `us_holdings_service.py`; endpoints
`POST /api/holdings/us/upload` and `POST /api/holdings/us/refresh-prices`; a
`market` field (`IN`/`US`) on `Holding` and `us_equity` instrument type
(`instrument_type` widened to 20 chars); dependencies `openpyxl==3.1.2` and
`finnhub-python==2.4.19`; `FINNHUB_API_KEY` (free tier 60 calls/min, sequential
fetch). Frontend `USStocksTab.vue`, sidebar entry, store getters/actions,
`/dashboard/us-stocks` route. *Initial semantics* (later hardened): invalid
symbols/negative quantities were logged and skipped, and a missing quote fell
back to average price.

**Fixed Deposits.** New service `fd_service.py`; endpoints
`POST /api/holdings/fd/upload` and `POST /api/holdings/fd/refresh-values`; reused
the `Holding` model (`instrument_type='fd'`, bank name in `tradingsymbol`,
principal in `average_price`, rate in `sector`, investment date in
`purchase_date`, `exchange='FD'`, `quantity=1`). Simple-interest formula
`Interest = (Principal × Rate × Years) / 100`, `Years = Days / 365`, accruing to
the current date or maturity if provided. Frontend `FixedDepositsTab.vue`,
sidebar entry, store getters/actions, `/dashboard/fixed-deposits` route.

### Undated — Initial dashboard release

> Source document (`PROJECT_SUMMARY.md`) did not record a calendar date.

The original multi-account Zerodha dashboard: encrypted-credential accounts,
Kite Connect holdings sync, automated 12-hour APScheduler sync, ~15 REST
endpoints, a 6-table SQLite schema (`accounts`, `holdings`, `snapshots`,
`portfolio_timeseries`, `sector_allocation`, `historical_prices`), Fernet
credential encryption, and a Vue 3 dashboard (Pie/Bar/Line/Heatmap charts,
summary cards, sortable/filterable holdings table, Pinia stores, Axios client,
notifications). Advanced analytics included total/annualized/daily returns,
volatility, Sharpe ratio, max drawdown, sector allocation, top/worst-5
performers, and correlation matrices. Approx. 4,400+ lines. Original tooling:
Flask 3.0, SQLAlchemy 3.1, APScheduler 3.10, Kite Connect 5.0, Vue 3.4,
Pinia 2.1, Vue Router 4.3, Chart.js 4.4, Vite 5.1.

---

## 4. Feature reference

### 4.1 Portfolio scope and currency

- **Family** combines the current completed state of all active accounts owned
  by the authenticated user. **Member** requires one selected account and is
  used for account-specific sync, quote refresh, and FD recalculation.
- The selected member is kept valid across account-list changes; deactivated
  selections are rebound safely; Family-mode imports require choosing the
  destination owner.
- Domestic equities, mutual funds, and fixed deposits display in INR; US
  equities display in USD and are excluded from the INR total. The Overview
  renders the two currencies as separate sections.

### 4.2 Asset pages

- **Overview** — separate INR/USD summaries, allocation and sector charts,
  value-growth / value-path metrics with honest labels, currency-aware history
  (shown only when currency is unambiguous), top and bottom performers,
  responsive current holdings, and loading/no-account/no-holdings/empty/error
  states.
- **Indian Stocks** — domestic-equity-only summary, allocation/sector visuals,
  shared search/filter/sort, responsive table/cards, account attribution in
  Family scope.
- **Mutual Funds** — dedicated INR summary, fractional units, folio-aware
  identity, scheme/folio/account search, largest-fund and return insights,
  scheme allocation and scheme-return charts. Separate folios are preserved
  rather than merged by scheme name.
- **US Stocks** — USD summary and holdings, `.xlsx`/`.xls` import with explicit
  destination account and replacement warnings, quote source and valuation date,
  a visible import-cost fallback, and refresh status distinguishing complete /
  partial / failed / skipped / no-holdings outcomes. A refresh publishes a new
  snapshot only when every symbol in the account receives a valid quote.
- **Fixed Deposits** — principal, accrued interest, current-value estimate, and
  maturity state; interest rate and dates; bank concentration and maturity
  insights; `.xlsx`/`.xls` replacement imports; optional stable `Deposit ID`;
  Member-scope recalculation; explicit disclosure that values are simple-interest
  estimates.
- **Bank Balances** — account cards with masked numbers and currency; account
  creation for INR/USD/EUR/GBP; preserved opening balances; permanent-delete
  confirmation; statement upload/parse/review/approve/retry/discard/history;
  paginated transaction search/filter; transaction edit/verify/categorize/delete;
  balance trend, category breakdown, cash flow, top merchants, anomalies, and
  spending-prediction panels with period selectors.

### 4.3 Accounts and Kite reconnection

Brokerage access tokens never pass through the browser. A new account submits
its Kite API key, secret, and one-time `request_token`; the backend exchanges
the token, encrypts the access token, and returns only nonsensitive metadata.
The legacy `POST /api/auth/access-token` returns `410 Gone`. For an expired
session, **Reconnect** calls `GET /api/accounts/:id/login-url`; the backend
builds the Kite URL server-side from the encrypted API key, and the frontend
only navigates to HTTPS on `kite.zerodha.com`. Accounts may also be created with
a name only (no Kite credentials) and populated with manual imports; the
`needs_reauth` flag tracks expired sessions.

### 4.4 Bank statement lifecycle

```text
uploading → uploaded → parsing → review → approving → approved
                     ↘ failed                  ↘ deleting
```

- A durable `uploading` row is committed before sensitive bytes are written.
- SHA-256 content hashes prevent approving the same PDF twice per bank account.
- Parse and approval use compare-and-set leases; stale leases can be recovered.
- PDFs are capped at 200 pages; compatible tables are combined across pages and
  repeated headers removed; parsed rows normalize to one canonical review DTO.
- Statement periods cannot overlap (inclusive boundaries); approving an older
  statement recalculates canonical state instead of moving `last_statement_date`
  backward.
- Private storage is owner-only, file-descriptor-relative, and fails closed on
  symlinks/special files.

### 4.5 Transactions, categories, balances

- Owner-scoped queries with bounded filters, pagination, and allowlisted
  sorting; unknown query parameters are rejected.
- Approving a statement creates verified transactions atomically; changing
  verification or deleting a transaction recalculates account state.
- Current balance = latest verified running balance, falling back to the
  preserved opening balance when none remains (removing the final verified
  transaction restores the opening balance, not zero).
- Categories are a system-controlled taxonomy; user corrections may update
  similar unverified transactions in the same bank account but never append
  private merchant words to global rules; category serialization omits keywords.

---

## 5. Import data formats

### 5.1 US holdings workbook (`.xlsx`/`.xls`)

| Column | Required | Example |
| --- | --- | --- |
| `Symbol` | Yes | `AAPL` |
| `Quantity` | Yes | `2.5` |
| `Average Price` | Yes | `182.50` |
| `Purchase Date` | No | `2025-01-15` |

Rules: complete-list replacement for one account; ≤100 positions; strict ticker
validation; duplicate-symbol rejection; positive finite quantities/prices;
six-decimal precision and money bounds; USD-only. Any invalid or duplicate row
rejects the whole workbook and leaves prior positions intact. Other asset
classes are carried forward. If a live quote is unavailable at import, the
position is visibly retained at import cost.

### 5.2 Fixed-deposit workbook (`.xlsx`/`.xls`)

| Column | Required | Example |
| --- | --- | --- |
| `Bank Name` | Yes | `HDFC Bank` |
| `Investment Amount` | Yes | `250000` |
| `Investment Date` | Yes | `2025-01-15` |
| `Interest Rate` | Yes | `7.25` |
| `Maturity Date` | No | `2027-01-15` |
| `Deposit ID` | No | `FD-2025-001` |

Rules: positive amount; interest rate > 0 and ≤ 100; maturity not before
investment; unique `Deposit ID`; complete-list replacement; INR-only.

Simple-interest estimate (accrual stops at maturity):

```text
interest = principal × annual_rate × elapsed_days / (100 × 365)
```

*Worked example:* ₹100,000 at 7.5% for 100 days →
`years = 100/365 = 0.274`, `interest = (100000 × 7.5 × 0.274)/100 ≈ ₹2,055`,
`current value ≈ ₹102,055`. Compounding, payout schedules, taxes, and
bank-specific terms are not modeled.

### 5.3 Upload safety (both types)

`MAX_UPLOAD_BYTES` enforced; `.xlsx`/`.xls` extension and file signature checked;
`.xlsx` archives capped at 2,000 members / 50 MiB expanded; processed from
randomized private temporary paths and removed afterwards; destination must be an
active account owned by the JWT user.

---

## 6. API reference

Except registration, login, and health, all endpoints require a valid dashboard
JWT and perform their own ownership checks.

**Authentication**

- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`,
  `POST /api/auth/logout`, `POST /api/auth/login-url`
- `POST /api/auth/access-token` — retired, returns `410 Gone`

**Zerodha accounts**

- `GET /api/accounts`, `POST /api/accounts`, `GET /api/accounts/:id`,
  `GET /api/accounts/:id/login-url`, `PUT /api/accounts/:id`,
  `DELETE /api/accounts/:id` (soft-deactivates)

**Holdings and imports**

- `GET /api/holdings` (`account_id`, `instrument_type` ∈
  `equity`/`mf`/`us_equity`/`fd`, `search`, `sort_by`, `sort_order`),
  `GET /api/holdings/aggregated`, `POST /api/holdings/sync`,
  `POST /api/holdings/us/upload`, `POST /api/holdings/us/refresh-prices`,
  `POST /api/holdings/fd/upload`, `POST /api/holdings/fd/refresh-values`

**Portfolio analytics**

- `GET /api/analytics/portfolio-value-history`,
  `GET /api/analytics/sector-breakdown`,
  `GET /api/analytics/performance-metrics` (fields labeled `value_growth` and
  `value_path_metrics`), `GET /api/analytics/correlation-matrix`,
  `GET /api/analytics/heatmap`

**Bank accounts and statements**

- `GET/POST /api/bank-accounts`, `GET/PUT /api/bank-accounts/:id`,
  `DELETE /api/bank-accounts/:id` (permanent),
  `POST /api/bank-accounts/:id/statements/upload`,
  `GET /api/bank-accounts/:id/statements`, `POST /api/statements/:id/parse`,
  `GET /api/statements/:id`, `DELETE /api/statements/:id`,
  `GET /api/statements/:id/preview`, `POST /api/statements/:id/approve`

**Transactions, categories, bank analytics**

- `GET /api/bank-accounts/:id/transactions`, `GET /api/transactions/search`,
  `PUT /api/transactions/:id`, `DELETE /api/transactions/:id`,
  `POST /api/transactions/bulk-recategorize`, `GET /api/categories`
- `GET /api/bank-accounts/:id/analytics/balance-trend`,
  `.../category-breakdown`, `.../cashflow`, `.../top-merchants`,
  `.../anomalies`, `.../predictions`

**System**

- `GET /api/health`

---

## 7. Database migration history

The chain is one linear history with a single head. Apply from
[src/backend](../src/backend):

```bash
python -m alembic upgrade head
```

| Revision | Change |
| --- | --- |
| `4b86235fc91f` | Users table and core portfolio schema; `accounts.user_id` nullable FK. |
| `5fc1369292e0` | Owned bank accounts with indexes/constraints. |
| `a6640608403a` | Transaction-category taxonomy. |
| `751d9fc01792` | Bank transactions, indexes, category links, account relationships. |
| `7c612302520e` | Bank statements and lifecycle fields. |
| `b1f00545dd90` | Parsing-template compatibility. |
| `d71c4a9e2f30` | Non-null account ownership, per-user account names, account snapshots, status/batch/currency metadata, source-aware holding fields, quarantine of unowned legacy data. |
| `e82b91a7c4d6` | Encrypt existing bank account numbers (store last-four only); replace learned private category keywords with safe defaults. |
| `f93c20b8d5e1` | `accounts.portfolio_version` to serialize concurrent snapshot writers. |
| `a04f31c9e762` | Statement content hashes and parsing leases, JWT revocation, database rate-limit buckets, canonical system categories. |
| `b15a7e4c2d90` | Preserved bank opening balances; initialize from current balance. |
| `c3a7d9e81f05` | Add `needs_reauth` to accounts (2026-08-05). |
| `a04d1b7c8e92` | Make Kite credentials optional (name-only accounts with manual holdings). |
| `855036219916` | **Head.** Consolidate `portfolio_timeseries` to one row per account-day-currency (UTC-midnight normalization, dedup). |

Upgrade behavior: orphan legacy accounts/snapshots are assigned to disabled
quarantine owners rather than exposed; existing bank-account encryption requires
the stable production `ENCRYPTION_KEY`; `db.create_all()` is not a substitute for
migrations. Back up a persistent database before upgrading.

---

## 8. Configuration and environment

All configuration lives in the single root [.env](../.env). The backend loads it
via `run.py` and Alembic; the frontend reads `VITE_*` values through Vite's
`envDir`.

| Variable | Purpose | Local default |
| --- | --- | --- |
| `FLASK_ENV` | `development` or `production` | `development` |
| `PORT` | HTTP listen port used by `run.py` | `5000` |
| `SECRET_KEY` | Flask signing secret | insecure dev fallback |
| `JWT_SECRET_KEY` | JWT signing secret (must differ from `SECRET_KEY` in prod) | falls back to `SECRET_KEY` |
| `ENCRYPTION_KEY` | Fernet key for Kite credentials and bank numbers | required when accounts/bank data are saved |
| `DATABASE_URL` | Runtime and Alembic database URL | `sqlite:///zerodha_dashboard.db` |
| `SCHEDULER_ENABLED` | Start APScheduler from `run.py` | `true` |
| `SYNC_INTERVAL_HOURS` | Scheduled Kite sync interval | `12` |
| `KITE_API_TIMEOUT` | Kite request timeout (seconds) | `30` |
| `KITE_RETRY_ATTEMPTS` | Kite retry attempts | `3` |
| `CORS_ORIGINS` | Comma-separated trusted frontend origins | `http://localhost:5173` |
| `MAX_UPLOAD_BYTES` | Flask request-size limit | `10485760` |
| `RATELIMIT_ENABLED` | Enforce request limits | `true` |
| `RATELIMIT_STORAGE` | `memory` locally; `database` required in production | `memory` |
| `FINNHUB_API_KEY` | Optional live US quote provider | unset |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Optional AI-assisted statement parsing | unset |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Optional async PDF parsing; sync when unset | unset |
| `VITE_API_BASE_URL` | Frontend API base URL | `http://localhost:5000/api` |
| `VITE_DEMO_MODE` | Frontend demo flag | `false` |

Generate secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"   # SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"   # JWT_SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # ENCRYPTION_KEY
```

**Production invariants:** `FLASK_ENV=production` requires distinct ≥32-byte
Flask/JWT secrets, a valid Fernet key, explicit non-wildcard CORS, and
`RATELIMIT_STORAGE=database`; an unknown/omitted environment never falls back to
development. Use HTTPS, run as an unprivileged user, run exactly one scheduler
process in a multi-worker deployment, and apply migrations before starting a new
version.

### Linking orphaned Zerodha accounts

Accounts created before user ownership existed have `user_id = NULL` and are
invisible to the authenticated API. Fix with the idempotent helper from
[src/backend](../src/backend):

```bash
python scripts/migrate_orphaned_accounts.py --dry-run   # preview
python scripts/migrate_orphaned_accounts.py             # apply
```

It reports orphan counts, creates an admin user if none exist, assigns orphans
to the single user or an interactively chosen one, and commits after
confirmation.

### Troubleshooting

- **`ModuleNotFoundError` on backend start** — activate the environment and
  `python -m pip install -r requirements.txt`.
- **Encryption-key errors** — `ENCRYPTION_KEY` must be a valid Fernet key and
  the *same* key that encrypted existing rows.
- **Frontend connection/CORS errors** — confirm the backend on port 5000,
  `VITE_API_BASE_URL` ends in `/api`, `CORS_ORIGINS` includes the exact origin
  (with port); restart after editing `.env`.
- **Auth rate-limited** — wait for the window; do not retry continuously.
- **Expired Kite session** — reconnect and submit a fresh one-time request
  token.
- **US quote missing** — check `FINNHUB_API_KEY` and provider limits; positions
  remain at cost with a source marker.
- **Empty page after import** — confirm Family/Member scope and the destination
  account; US/FD workbooks replace only that asset class for the chosen account.

---

## 9. Behavior contracts

These are intentional and should not change accidentally:

1. No implicit FX conversion — currencies stay separate until an explicit
   exchange-rate feature is designed.
2. Snapshots are account-scoped and immutable; refreshes create history.
3. Failed refreshes are not current state; reads use the last completed
   snapshot.
4. US and FD imports replace one asset slice (complete lists, not deltas) and
   preserve other asset classes.
5. A US refresh is all-or-nothing per account.
6. FD values are disclosed simple-interest estimates.
7. Mutual-fund folios remain distinct; fractional units are preserved.
8. Kite access tokens never reach the browser; reconnection uses a server-owned
   login URL and one-time request token.
9. Zerodha account deletion is soft; bank account deletion is permanent.
10. Statement periods cannot overlap (inclusive boundaries).
11. Bank balance uses the latest verified running balance, falling back to the
    preserved opening balance.
12. Private statement storage fails closed; links and special entries are never
    followed.
13. Categories are a safe system taxonomy; private merchant descriptions are not
    learned into global rules.
14. Late frontend responses cannot overwrite newer scope/account state.

---

## 10. Testing

Recorded at the 2026-07-31 consolidation release: **329** backend tests passing;
**83** frontend tests across **9** Vitest files; Vite build transformed **465**
modules; `pip check` clean; one Alembic head; `git diff --check` clean.

Backend suite highlights: application-factory ordering and security headers;
production-config rejection; auth/revocation; account ownership and server-owned
reconnect; Kite sync partial failures; account-scoped snapshots and concurrent
writer serialization; family/member isolation; snapshot overflow rejection;
atomic US/FD imports; FD `Decimal` calculations; bank-number encryption;
statement idempotency/leases/multi-page/overlap/preview/approve/retry/discard;
permission reconciliation and symlink refusal; permanent deletion and recovery;
transaction/balance integrity; bank-analytics contracts; clean and populated
migration upgrades. Statement storage is redirected to a temp path by an autouse
fixture so tests never write documents into the repo.

Run everything:

```bash
cd src/backend && python -m alembic upgrade head && python -m pytest -q
cd ../frontend && npm test && npm run build
```

There are also repository-level integration tests under
[src/tests](../src/tests) (accounts/holdings, analytics, auth, bank, foreign
holdings, and a frontend/backend contract test).

---

## 11. Known limitations and future enhancements

- **Access tokens expire daily** (Zerodha rule) — reconnect to refresh.
- **API rate limits** — syncing too frequently can error; Finnhub free tier is
  60 calls/min and fetched sequentially.
- **SQLite concurrency** — use PostgreSQL for production.
- **Historical trends** require multiple snapshots over time.
- **AI PDF parsing / AI categorization** remain optional (keyword-based by
  default; provider keys enable AI).
- **Full-text search** on transaction descriptions uses `LIKE`, not PostgreSQL
  FTS.
- **PDF file-path encryption** is deferred (mitigated by fail-closed private
  storage).
- **FD model** uses simple interest, a 365-day year, INR only, and does not
  model TDS, compounding, or premature withdrawal.

Recorded future ideas: batched/cached US quotes, symbol and exchange validation,
sector data, FD compounding/TDS/maturity alerts, transaction export, budget
tracking, year-over-year comparisons, and API (OpenAPI) documentation.

---

## 12. Component change map

| Area | Components |
| --- | --- |
| Backend bootstrap | `app/__init__.py`, `app/config.py`, `app/database.py`, `run.py`, `wsgi.py` |
| Portfolio models | `models/account.py`, `models/holding.py`, `models/snapshot.py`, `models/user.py` |
| Bank models | `models/bank_account.py`, `models/bank_statement.py`, `models/transaction.py`, `models/transaction_category.py`, `models/parsing_template.py` |
| Security models | `models/revoked_token.py`, `models/rate_limit_bucket.py` |
| Portfolio routes | `routes/accounts.py`, `routes/holdings.py`, `routes/analytics.py`, `routes/auth.py` |
| Bank routes | `routes/bank_accounts.py`, `routes/bank_statements.py`, `routes/transactions.py`, `routes/categories.py`, `routes/bank_analytics.py` |
| Portfolio services | `services/portfolio_service.py`, `services/kite_service.py`, `services/scheduler_service.py`, `services/analytics_service.py` |
| Import services | `services/us_holdings_service.py`, `services/finnhub_service.py`, `services/fd_service.py` |
| Bank services | `services/bank_statement_service.py`, `services/pdf_parser_service.py`, `services/transaction_service.py`, `services/transaction_categorization_service.py`, `services/bank_analytics_service.py` |
| Backend utilities | `utils/auth.py`, `utils/encryption.py`, `utils/rate_limiter.py`, `utils/validators.py` |
| Frontend shell | `App.vue`, `main.js`, `router/index.js`, `assets/styles/main.css`, `index.html` |
| Frontend state/API | `services/api.js`; `accounts`, `auth`, `bankAccounts`, `categories`, `holdings`, `ui` stores |
| Frontend utilities | `utils/authSession.js`, `utils/currency.js`, `utils/holdings.js`, `utils/transactions.js` |
| Dashboard components | `AccountSelector.vue`, `HoldingsTable.vue`, `PortfolioSummary.vue`, `Sidebar.vue`, `ChartPanel.vue`, `FixedDepositTable.vue` |
| Bank components | account/upload/review modals, analytics charts, bank cards, transaction lists, `StatementHistory.vue` |
| Shared visual components | `DataCard.vue`; bar/line/pie chart wrappers |
| Frontend views | Accounts, Dashboard, Login, Register, Overview, Stocks, Mutual Funds, US Stocks, Fixed Deposits, Bank Balances |

---

## 13. Contributor checklist

Before changing or releasing this dashboard:

- Preserve JWT and resource-level ownership checks.
- Never serialize encrypted credentials, full bank numbers, private paths,
  hashes, parser leases, or tokens.
- Preserve account and currency dimensions in new queries.
- Create snapshots for valuation changes instead of mutating history.
- Validate source rows and derived totals before committing imports.
- Keep uploads private, bounded, content-checked, and temporary where possible.
- Keep request-generation guards when adding asynchronous frontend loads.
- Provide loading, empty, error, desktop, and mobile behavior for new pages.
- Add backend and frontend regressions for behavior changes.
- Run migrations and both test suites before release:

```bash
cd src/backend && python -m alembic upgrade head && python -m pytest -q
cd ../frontend && npm test && npm run build
```
