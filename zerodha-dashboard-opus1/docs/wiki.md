# Claude Code Dashboard Consolidation Wiki

> Status: implementation complete  
> Canonical project: `zerodha-dashboard-opus1`  
> Last documented: 2026-07-31  
> Database head: `b15a7e4c2d90`

## 1. Purpose and scope

This document records the complete consolidation performed on the Claude Code
dashboard. The Claude Code implementation remains the canonical application;
the useful capabilities found in the other LLM implementations were integrated
into this codebase instead of replacing it or creating a second application.

The work covered:

- the dashboard information architecture and visual presentation;
- responsive desktop, tablet, and mobile layouts;
- family-wide and individual-member portfolio scopes;
- shared search, filtering, and sorting behavior;
- dedicated mutual-fund and fixed-deposit pages;
- US-equity imports and valuations;
- bank accounts, statements, transactions, and analytics;
- authentication, authorization, encryption, rate limiting, and upload safety;
- account-scoped immutable snapshots and financially safe calculations;
- database migrations and upgrade compatibility;
- broad backend and frontend regression suites;
- deployment, setup, and security documentation.

The implementation deliberately favors small services, explicit state, and
shared utilities over additional framework layers or speculative abstractions.

## 2. High-level outcome

The application is now a self-hosted family portfolio dashboard for:

- Indian equities;
- Coin mutual funds;
- US equities;
- fixed deposits;
- bank balances and statement-derived transactions.

The final system keeps ownership and currency boundaries explicit:

- every Zerodha account and bank account belongs to one dashboard user;
- every portfolio snapshot belongs to one Zerodha account;
- Family scope combines only the latest completed snapshot from each owned,
  active account;
- Member scope targets exactly one owned account;
- domestic assets and fixed deposits remain in INR;
- US holdings remain in USD;
- bank accounts retain their configured INR, USD, EUR, or GBP currency;
- amounts in different currencies are never silently added or converted.

## 3. Final architecture

The existing Flask/Vue structure was retained and clarified:

```text
zerodha-dashboard-opus1/
├── backend/
│   ├── alembic/versions/       # Ordered, tested schema upgrades
│   ├── app/
│   │   ├── models/             # Ownership-aware SQLAlchemy models
│   │   ├── routes/             # Authenticated HTTP boundary
│   │   ├── services/           # Portfolio, import, statement, and analytics logic
│   │   └── utils/              # Auth, encryption, validation, and rate limiting
│   └── tests/                  # Backend unit, route, migration, and security tests
├── frontend/
│   ├── src/
│   │   ├── components/         # Shared dashboard, chart, and bank components
│   │   ├── stores/             # Pinia state and request orchestration
│   │   ├── utils/              # Currency, holdings, session, and query helpers
│   │   └── views/              # Auth, account, and asset pages
│   └── tests/                  # Vitest contracts and store tests
├── docs/
├── GETTING_STARTED.md
└── README.md
```

`create_app()` constructs the Flask application without starting background
threads. `backend/run.py` is the only normal entry point that starts the
scheduler. This keeps imports, Alembic, and tests deterministic.

## 4. Frontend changes

### 4.1 Navigation and page structure

The dashboard was reorganized into explicit authenticated routes:

| Route | Page | Main responsibility |
| --- | --- | --- |
| `/dashboard/overview` | Overview | Cross-asset summaries, allocation, sectors, history, and holdings |
| `/dashboard/stocks` | Indian Stocks | Domestic equity analysis and holdings |
| `/dashboard/mutual-funds` | Mutual Funds | Folio-aware Coin mutual-fund analysis |
| `/dashboard/us-stocks` | US Stocks | USD positions, workbook import, provenance, and quote refresh |
| `/dashboard/fixed-deposits` | Fixed Deposits | INR deposits, maturity, estimates, import, and recalculation |
| `/dashboard/bank-balances` | Bank Balances | Accounts, statements, transactions, and cash analytics |
| `/accounts` | Accounts | Zerodha account creation, reconnection, and management |

The dashboard child pages are lazy-loaded. The root route redirects to the
Overview page. Guest and protected routes wait for authentication bootstrap
before resolving, preventing a valid stored session from briefly being treated
as logged out.

The application shell and sidebar were rebuilt to provide:

- a consistent page title and primary navigation;
- clear active-route styling;
- a collapsible mobile menu;
- touch-friendly controls and spacing;
- a stable content area for nested dashboard routes;
- safe logout and session cleanup.

Primary files:

- [`frontend/src/App.vue`](../frontend/src/App.vue)
- [`frontend/src/router/index.js`](../frontend/src/router/index.js)
- [`frontend/src/components/dashboard/Sidebar.vue`](../frontend/src/components/dashboard/Sidebar.vue)
- [`frontend/src/views/Dashboard.vue`](../frontend/src/views/Dashboard.vue)

### 4.2 Visual system and responsive presentation

The presentation layer was expanded with reusable visual primitives instead of
duplicating page-specific markup:

- summary and KPI cards;
- chart panels with titles, descriptions, loading, empty, and error states;
- responsive line, bar, and pie-chart wrappers;
- allocation, sector, scheme, bank concentration, cash-flow, and trend views;
- desktop tables that become readable cards on narrow screens;
- responsive summary grids and import forms;
- mobile sort controls and menu behavior;
- consistent positive, negative, neutral, muted, and warning states;
- accessible labels and explicit button states for unavailable actions.

Shared styling lives in
[`frontend/src/assets/styles/main.css`](../frontend/src/assets/styles/main.css).
The main reusable display components are:

- [`DataCard.vue`](../frontend/src/components/common/DataCard.vue)
- [`ChartPanel.vue`](../frontend/src/components/dashboard/ChartPanel.vue)
- [`PortfolioSummary.vue`](../frontend/src/components/dashboard/PortfolioSummary.vue)
- [`HoldingsTable.vue`](../frontend/src/components/dashboard/HoldingsTable.vue)
- [`FixedDepositTable.vue`](../frontend/src/components/dashboard/FixedDepositTable.vue)
- the chart wrappers under [`frontend/src/components/charts`](../frontend/src/components/charts)

### 4.3 Family and Member scope

`AccountSelector.vue` now exposes two explicit modes:

- **Family** combines the current completed state of all active accounts owned
  by the authenticated user.
- **Member** requires one selected account and is used for account-specific
  sync, quote refresh, FD recalculation, and detailed review.

Behavior added around the selector:

- the currently selected member is kept valid when the account list changes;
- disappearing or deactivated selections are rebound safely;
- a Family-mode import requires the user to choose the destination owner;
- operations that cannot be performed across owners are disabled or explained;
- changing scope reloads holdings and analytics through a single orchestration
  path;
- late responses from a previous scope cannot overwrite the new selection.

Primary files:

- [`AccountSelector.vue`](../frontend/src/components/dashboard/AccountSelector.vue)
- [`accounts.js`](../frontend/src/stores/accounts.js)
- [`holdings.js`](../frontend/src/stores/holdings.js)
- [`Dashboard.vue`](../frontend/src/views/Dashboard.vue)

### 4.4 Shared search, filtering, and sorting

The holdings experience gained one shared implementation for desktop and
mobile:

- search across symbol, type, sector, fund name, folio, account name, and
  account identifier;
- asset-type filtering;
- profitable-position and loss-making-position filters;
- clickable desktop column sorting;
- mobile sort-field selection;
- ascending and descending direction controls;
- deterministic tie-breaking so equal values do not jump between renders;
- explicit initial-empty and filtered-empty messages;
- numeric sorting that safely handles missing or malformed values.

Backend holdings endpoints also accept validated `search`, `instrument_type`,
`sort_by`, and `sort_order` parameters, so the server and client follow the
same contract.

The shared implementation is in:

- [`frontend/src/utils/holdings.js`](../frontend/src/utils/holdings.js)
- [`frontend/src/components/dashboard/HoldingsTable.vue`](../frontend/src/components/dashboard/HoldingsTable.vue)
- [`backend/app/routes/holdings.py`](../backend/app/routes/holdings.py)

Transaction lists received comparable server-backed search, category/type
filters, bounded pagination, and validated sorting. Query construction is
centralized in
[`frontend/src/utils/transactions.js`](../frontend/src/utils/transactions.js).

### 4.5 Overview page

The Overview page now provides:

- separate INR and USD portfolio summaries;
- asset-allocation and sector-allocation charts;
- value-growth and value-path metrics with honest labels;
- currency-aware portfolio history;
- top and bottom performers;
- a responsive current-holdings view;
- loading, no-account, no-holdings, filtered-empty, and error states.

Mixed-currency totals are intentionally not rendered as one number. A history
chart is shown only when its currency is explicit or unambiguous.

Primary file:
[`frontend/src/views/dashboard/OverviewTab.vue`](../frontend/src/views/dashboard/OverviewTab.vue).

### 4.6 Indian Stocks page

The Indian Stocks page now has:

- a domestic-equity-only summary;
- equity allocation and sector visuals;
- reusable search, performance filtering, and sorting;
- a responsive holdings table/card layout;
- account attribution in Family scope.

Primary file:
[`frontend/src/views/dashboard/StocksTab.vue`](../frontend/src/views/dashboard/StocksTab.vue).

### 4.7 Dedicated Mutual Funds page

A complete mutual-fund page was added rather than treating funds as generic
stock rows. It includes:

- a dedicated INR summary;
- fractional unit display;
- folio-aware position identity;
- scheme, folio, and account search;
- largest-fund and return insights;
- scheme allocation and scheme-return charts;
- responsive positions on desktop and mobile.

The backend fetches Kite equity holdings and Coin mutual-fund holdings through
their respective APIs. Separate folios are preserved instead of being merged
solely by scheme name.

Primary file:
[`frontend/src/views/dashboard/MutualFundsTab.vue`](../frontend/src/views/dashboard/MutualFundsTab.vue).

### 4.8 US Stocks page

The US-equity experience now supports:

- a dedicated USD summary and holdings view;
- `.xlsx` and `.xls` imports;
- explicit destination-account selection;
- replacement-semantics warnings;
- quote source and valuation date display;
- a visible import-cost fallback when no live quote was available;
- refresh status that distinguishes complete, partial, failed, skipped, and
  no-holdings outcomes;
- safe refresh behavior that publishes a new snapshot only when every symbol
  in the selected account receives a valid quote;
- responsive forms, cards, and tables.

The page never presents an import-cost fallback as a fresh market quote.

Primary files:

- [`USStocksTab.vue`](../frontend/src/views/dashboard/USStocksTab.vue)
- [`us_holdings_service.py`](../backend/app/services/us_holdings_service.py)
- [`finnhub_service.py`](../backend/app/services/finnhub_service.py)

### 4.9 Dedicated Fixed Deposits page

A dedicated fixed-deposit page and table were added with:

- principal, accrued interest, current-value estimate, and maturity state;
- interest-rate and investment/maturity date presentation;
- bank concentration and maturity insights;
- `.xlsx` and `.xls` replacement imports;
- optional stable `Deposit ID` support;
- Member-scope value recalculation;
- clear disclosure that displayed values are simple-interest estimates.

The estimate accrues through the earlier of the valuation date or maturity
date. It does **not** claim to model compounding, payout schedules, taxes, or
bank-specific product rules.

Primary files:

- [`FixedDepositsTab.vue`](../frontend/src/views/dashboard/FixedDepositsTab.vue)
- [`FixedDepositTable.vue`](../frontend/src/components/dashboard/FixedDepositTable.vue)
- [`fd_service.py`](../backend/app/services/fd_service.py)

### 4.10 Bank Balances experience

The bank area was integrated into the main dashboard and expanded to include:

- account cards with masked account numbers and account currency;
- account creation for INR, USD, EUR, and GBP;
- preserved opening balances;
- explicit permanent-delete confirmation;
- statement upload, parse, review, approve, retry, discard, and history flows;
- paginated transaction search and filtering;
- transaction editing, verification, categorization, and deletion;
- balance trend, category breakdown, cash flow, top merchants, anomalies, and
  spending prediction panels;
- analytics period selectors whose exact period is passed to every endpoint;
- balance and transaction refresh after relevant mutations;
- responsive modals, charts, lists, and account layouts.

New statement history is implemented in
[`StatementHistory.vue`](../frontend/src/components/bank/StatementHistory.vue).
The overall page is
[`BankBalancesTab.vue`](../frontend/src/views/dashboard/BankBalancesTab.vue).

### 4.11 Accounts and Kite reconnection

The account flow was changed so brokerage access tokens never pass through the
browser:

1. A new account submits its Kite API key, API secret, and one-time
   `request_token` to the backend.
2. The backend exchanges the one-time token and encrypts the resulting access
   token.
3. API responses return only nonsensitive account metadata.
4. The legacy `POST /api/auth/access-token` endpoint now returns `410 Gone`.

For an expired Kite session, **Reconnect** calls
`GET /api/accounts/:id/login-url`. The backend decrypts the stored API key,
constructs the Kite URL server-side, and returns it only after checking account
ownership. The frontend accepts navigation only to HTTPS on
`kite.zerodha.com`, then submits the new request token to the same account.

Primary files:

- [`frontend/src/views/Accounts.vue`](../frontend/src/views/Accounts.vue)
- [`backend/app/routes/accounts.py`](../backend/app/routes/accounts.py)

### 4.12 Frontend session and request safety

Authentication and asynchronous state handling were hardened:

- the dashboard JWT is stored in tab-scoped `sessionStorage`;
- older token locations are cleared during migration and logout;
- the single Axios client adds the bearer token;
- a `401` clears local session state;
- authentication bootstrap calls `/auth/me` before route decisions;
- API errors are normalized without leaking credentials;
- holdings, bank analytics, bank transactions, and statement requests use
  request generations and/or `AbortController`;
- a late response is ignored when account, scope, or page context has changed;
- selected bank accounts are rebound after account refreshes;
- loading flags are cleared only by the request that owns them.

Primary files:

- [`frontend/src/services/api.js`](../frontend/src/services/api.js)
- [`frontend/src/stores/auth.js`](../frontend/src/stores/auth.js)
- [`frontend/src/stores/holdings.js`](../frontend/src/stores/holdings.js)
- [`frontend/src/stores/bankAccounts.js`](../frontend/src/stores/bankAccounts.js)
- [`frontend/src/utils/authSession.js`](../frontend/src/utils/authSession.js)

### 4.13 Currency utilities

Currency display was centralized in
[`frontend/src/utils/currency.js`](../frontend/src/utils/currency.js):

- ISO-style currency codes are normalized;
- `Intl.NumberFormat` is used consistently;
- account currency flows through bank cards, analytics, transactions, and
  opening-balance fields;
- INR is a fallback, not an unconditional hard-coded prefix;
- mixed portfolio summaries expose per-currency groups rather than a false
  aggregate.

## 5. Backend changes

### 5.1 Application factory and configuration

The application bootstrap was refactored to make configuration deterministic
and production-safe:

- mapping overrides are applied before extension initialization;
- unknown or omitted environments do not silently select development settings;
- production requires distinct Flask and JWT secrets of at least 32 bytes;
- production requires a valid Fernet encryption key;
- wildcard or empty production CORS configuration is rejected;
- production requires database-backed rate limiting;
- the scheduler is attached by the factory but started only by `run.py`;
- request-size handling returns consistent validation responses;
- API responses receive security and no-cache headers;
- legacy bank-statement permissions are reconciled before requests are served.

Security headers include:

- `X-Content-Type-Options: nosniff`;
- `X-Frame-Options: DENY`;
- a restrictive API Content Security Policy;
- `Referrer-Policy: same-origin`;
- a restrictive `Permissions-Policy`;
- `Cache-Control: no-store` and `Pragma: no-cache` for API responses;
- HSTS for secure production requests.

Primary files:

- [`backend/app/__init__.py`](../backend/app/__init__.py)
- [`backend/app/config.py`](../backend/app/config.py)
- [`backend/run.py`](../backend/run.py)

### 5.2 Dashboard authentication

Authentication changes include:

- registration with normalized email and bounded input validation;
- passwords limited to 8–1024 characters;
- portable PBKDF2-SHA256 password hashing;
- active-user checks during JWT lookup;
- database-persisted JWT revocation on logout;
- revocation lookup on every protected request;
- bounded login and registration rate limits;
- a retired browser-facing brokerage-token exchange endpoint;
- no credentials, request tokens, access tokens, or JWTs in logs or account
  serialization.

New models:

- [`RevokedToken`](../backend/app/models/revoked_token.py)
- [`RateLimitBucket`](../backend/app/models/rate_limit_bucket.py)

### 5.3 Tenant isolation and ownership

Tenant boundaries were applied consistently across the API and service layer:

- Zerodha account names are unique per dashboard user, not globally;
- accounts have a non-null user owner and cascading ownership relationships;
- every account lookup for sync, import, analytics, and reconnect checks the JWT
  subject;
- bank accounts, statements, and transactions are queried through their owner;
- inactive or foreign accounts are returned as unavailable rather than
  disclosing their existence;
- analytics join through owned active accounts;
- family reads cannot select another user's account by changing an ID;
- JWT subject caching is request-aware and cannot leak a prior subject through
  a long-lived Flask application context.

The shared account helpers live in
[`backend/app/utils/auth.py`](../backend/app/utils/auth.py).

### 5.4 Credential and account-number encryption

Kite API keys, API secrets, and access tokens remain encrypted with Fernet.
The bank feature was brought to the same standard:

- full bank account numbers are encrypted at rest;
- only the last four characters are stored separately for display;
- API serialization returns a masked number only;
- encryption uses the configured stable `ENCRYPTION_KEY`;
- existing plaintext rows are encrypted by migration;
- sensitive model fields are omitted from public dictionaries.

Primary files:

- [`backend/app/utils/encryption.py`](../backend/app/utils/encryption.py)
- [`backend/app/models/account.py`](../backend/app/models/account.py)
- [`backend/app/models/bank_account.py`](../backend/app/models/bank_account.py)

### 5.5 Account-scoped immutable portfolio snapshots

Portfolio persistence was reworked from global timestamp snapshots to
account-scoped immutable snapshots:

- every snapshot has `account_id`, `batch_id`, `status`, `trigger`, currency,
  and optional error information;
- reads use only the latest completed snapshot for each selected account;
- a failed refresh does not replace the last good state;
- Family scope aggregates one current snapshot per owned account;
- source-specific updates copy other asset classes forward;
- US and FD refreshes create snapshots instead of mutating historical rows;
- currency-specific time-series rows prevent INR/USD mixing;
- zero-value currency tombstones prevent a removed currency from being carried
  forward indefinitely in family history;
- holdings have source-aware stable keys;
- mutual-fund folios and fixed-deposit identifiers participate in identity;
- numeric bounds are checked before a database flush, including aggregate
  totals that could overflow even when each individual holding fits.

Concurrent portfolio writers are serialized through `Account.portfolio_version`
and conditional updates. A losing writer fails cleanly instead of publishing a
partially interleaved snapshot.

Primary files:

- [`backend/app/models/snapshot.py`](../backend/app/models/snapshot.py)
- [`backend/app/models/holding.py`](../backend/app/models/holding.py)
- [`backend/app/services/portfolio_service.py`](../backend/app/services/portfolio_service.py)

### 5.6 Kite synchronization

Manual and scheduled synchronization now:

- process only active accounts owned by the selected dashboard user;
- fetch equity and mutual-fund holdings independently;
- preserve fractional mutual-fund units;
- keep positions in different folios separate;
- create one result snapshot per account;
- report complete, partial, and failed batch outcomes honestly;
- isolate one account failure from successful sibling accounts;
- record failed attempts without making them current;
- avoid starting scheduler threads from tests or migrations.

Primary files:

- [`backend/app/services/kite_service.py`](../backend/app/services/kite_service.py)
- [`backend/app/services/scheduler_service.py`](../backend/app/services/scheduler_service.py)

### 5.7 Spreadsheet upload safety

US and FD imports share a hardened upload boundary:

- Flask enforces `MAX_UPLOAD_BYTES`;
- only `.xlsx` and `.xls` are accepted;
- the file signature must match the extension;
- `.xlsx` archives are capped at 2,000 members and 50 MiB expanded size;
- randomized private temporary paths replace user-supplied filenames;
- rejected and completed temporary files are removed;
- input rows are fully validated before a replacement snapshot is created;
- invalid, duplicate, non-finite, or out-of-precision values reject the entire
  workbook;
- import destinations must be active accounts owned by the JWT user.

Both import types are full-list replacements for the selected account and
asset type, while other asset classes are preserved.

### 5.8 US-equity import and refresh integrity

US holdings changes include:

- a maximum of 100 positions per workbook;
- required Symbol, Quantity, and Average Price fields;
- strict ticker validation and duplicate-symbol rejection;
- positive finite quantities and prices;
- six-decimal position precision and database-money bounds;
- optional Purchase Date parsing;
- USD-only storage and summaries;
- live quote provenance and price dates;
- import-cost fallback when the quote provider is unavailable;
- all-or-nothing quote refresh per account so a partially refreshed account is
  never published as current.

### 5.9 Fixed-deposit calculation integrity

FD processing now uses `Decimal` with round-half-up money quantization. It
validates:

- positive principal;
- interest rates greater than zero for imports and no greater than 100%;
- investment and maturity dates;
- maturity not preceding investment;
- duplicate Deposit IDs;
- source and derived precision before persistence;
- current value and interest against database numeric limits.

Simple interest is calculated as:

```text
interest = principal × annual_rate × elapsed_days / (100 × 365)
```

Elapsed days stop at maturity. This is explicitly an estimate and not a bank
product settlement engine.

### 5.10 Portfolio analytics

Portfolio analytics were made owner- and currency-aware:

- history, sectors, performance, correlation, and heatmap routes require JWTs;
- an optional account filter must refer to an owned account;
- currency filters prevent mixed-currency series;
- start/end boundaries are retained even when no event occurs exactly on a
  boundary;
- family history carries the latest state per account while counting day
  change only for accounts updated in that period;
- daily, weekly, and monthly granularity is supported;
- performance output is labeled `value_growth` and `value_path_metrics`;
- metrics explicitly state that they are not cash-flow-adjusted investment
  returns.

Primary files:

- [`backend/app/routes/analytics.py`](../backend/app/routes/analytics.py)
- [`backend/app/services/analytics_service.py`](../backend/app/services/analytics_service.py)

### 5.11 Bank account behavior

Bank-account handling now provides:

- authenticated per-user CRUD;
- encrypted full account numbers and masked serialization;
- validated bank name, account number, account type, balance, and currency;
- supported currencies: INR, USD, EUR, and GBP;
- a separately preserved opening balance;
- a derived current balance;
- permanent deletion rather than ambiguous soft deletion.

Permanent deletion:

- first serializes against statement uploads;
- refuses deletion while an active statement operation owns a lease;
- deletes transactions and statements through database cascades;
- removes both database-linked PDFs and account-owned legacy/orphan PDFs;
- validates that every deletion target stays within the configured account
  directory;
- refuses symbolic links, nested/special entries, and outside paths;
- reactivates the account if file or database cleanup fails, allowing a safe
  retry.

### 5.12 Private bank-statement storage

Statement filesystem handling was hardened for both new and legacy uploads:

- directories are owner-only (`0700`);
- regular files are owner-only (`0600`);
- startup recursively reconciles modes left by older releases;
- traversal is file-descriptor-relative and uses `O_NOFOLLOW`;
- symbolic links and special files stop startup instead of being followed;
- new intermediate directories are secured before statement bytes are written;
- pytest automatically redirects statement storage to a temporary directory.

The configured storage root is
`backend/uploads/bank_statements`. Uploaded PDFs, private paths, and hashes are
never returned by the API.

### 5.13 Statement lifecycle and idempotency

The statement workflow was made explicit and retry-safe:

```text
uploading → uploaded → parsing → review → approving → approved
                     ↘ failed                  ↘ deleting
```

Changes include:

- a durable `uploading` database row is committed before sensitive bytes are
  written;
- failed upload cleanup retains a recoverable tombstone if file removal fails;
- SHA-256 content hashes prevent the same PDF from being approved twice for one
  bank account;
- parse claims use a compare-and-set lease;
- stale parsing and uploading leases can be recovered;
- active operations cannot be deleted concurrently;
- PDFs are capped at 200 pages;
- compatible transaction tables are combined across pages;
- repeated page headers are removed;
- parsed rows are normalized into one canonical review DTO;
- temporary parsed data is removed after approval;
- approval is a single claim-once database transaction;
- failed parses can be retried or discarded;
- statement periods use inclusive overlap detection, including shared boundary
  dates;
- approval order does not determine balance order;
- approving an older statement recalculates canonical account state instead of
  moving `last_statement_date` backward.

User-derived statement templates are no longer saved into a cross-tenant
global object. Legacy templates remain migration-compatible, but new private
statement layouts are not learned globally.

Primary files:

- [`backend/app/models/bank_statement.py`](../backend/app/models/bank_statement.py)
- [`backend/app/services/bank_statement_service.py`](../backend/app/services/bank_statement_service.py)
- [`backend/app/services/pdf_parser_service.py`](../backend/app/services/pdf_parser_service.py)
- [`backend/app/routes/bank_statements.py`](../backend/app/routes/bank_statements.py)

### 5.14 Transaction and balance integrity

Transaction behavior was consolidated around verified financial data:

- queries are owner-scoped and support bounded filters, pagination, and
  allowlisted sorting;
- unknown query parameters are rejected instead of silently ignored;
- transaction date, type, amount, running balance, category, verification, and
  notes are validated;
- update and delete failures roll back cleanly;
- approving a statement creates verified transactions atomically;
- changing verification or deleting a transaction recalculates account state;
- current balance is taken from the latest verified transaction with a running
  balance, falling back to the preserved opening balance when none remains;
- removing the final verified transaction restores the opening balance rather
  than zero;
- statement and transaction mutations invalidate/reload relevant frontend
  balances and analytics.

### 5.15 Categories and privacy

The transaction taxonomy is now system-controlled:

- `/api/categories` returns system categories only;
- categorization and correction accept system category IDs only;
- known default category rows are normalized to safe names, colors, icons, and
  public keyword rules during migration;
- old user-created category data is not exposed through transaction or anomaly
  responses;
- legacy/custom category references are presented as Uncategorized;
- category breakdown joins do not leak custom category names;
- user corrections may update similar unverified transactions in the same bank
  account but never append private merchant words to global rules;
- category serialization omits matching keywords.

### 5.16 Bank analytics

Bank analytics now enforce ownership and exact query contracts for:

- balance trend;
- category breakdown;
- cash flow;
- top merchants;
- anomalies;
- spending prediction.

Improvements include bounded period parameters, exact transaction counts,
system-category redaction, currency propagation, consistent merchant
extraction, and verified-data filtering where financial totals require it.

### 5.17 Rate limiting

The rate limiter supports:

- local in-memory counters for development;
- database-backed fixed-window counters for production;
- hashed bucket keys rather than raw principal/route identifiers;
- route-specific and user-specific limits;
- expired-bucket cleanup;
- production startup rejection when only process-local counters are selected.

Primary file:
[`backend/app/utils/rate_limiter.py`](../backend/app/utils/rate_limiter.py).

## 6. Database migration history

The migration chain was repaired and tested as one linear history. Existing
migrations were also made safer for clean databases, populated databases,
SQLite batch operations, named constraints, foreign keys, and indexes.

| Revision | Change |
| --- | --- |
| `4b86235fc91f` | Establishes users and the core portfolio schema with account ownership foundations. |
| `5fc1369292e0` | Adds owned bank accounts and bank-account indexes/constraints. |
| `a6640608403a` | Adds the transaction-category taxonomy. |
| `751d9fc01792` | Adds bank transactions, indexes, category links, and account relationships. |
| `7c612302520e` | Adds bank statements and statement lifecycle fields. |
| `b1f00545dd90` | Adds parsing-template compatibility. |
| `d71c4a9e2f30` | Makes account ownership non-null, scopes account names per user, creates account snapshots, adds status/batch/currency metadata, source-aware holding fields, and safely quarantines unowned legacy data. |
| `e82b91a7c4d6` | Encrypts existing bank account numbers, stores only last-four display data, and replaces learned private category keywords with safe defaults. |
| `f93c20b8d5e1` | Adds `accounts.portfolio_version` to serialize concurrent snapshot writers. |
| `a04f31c9e762` | Adds statement content hashes and parsing leases, JWT revocation, database rate-limit buckets, and canonical system categories. |
| `b15a7e4c2d90` | Adds preserved bank opening balances and initializes existing rows from their current balance. |

Important upgrade behavior:

- orphan legacy accounts and snapshots are assigned to disabled quarantine
  owners rather than exposed to a real user;
- existing bank account encryption requires the stable production
  `ENCRYPTION_KEY`;
- the chain has one head: `b15a7e4c2d90`;
- `db.create_all()` is not a replacement for Alembic upgrades.

Apply the migrations from `backend`:

```bash
python -m alembic upgrade head
```

Back up a persistent database before upgrading.

## 7. API surface after consolidation

### 7.1 Authentication

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`
- `POST /api/auth/login-url`
- `POST /api/auth/access-token` — intentionally retired with `410 Gone`

### 7.2 Zerodha accounts

- `GET /api/accounts`
- `POST /api/accounts`
- `GET /api/accounts/:id`
- `GET /api/accounts/:id/login-url`
- `PUT /api/accounts/:id`
- `DELETE /api/accounts/:id` — soft-deactivates the Zerodha account

### 7.3 Holdings and imports

- `GET /api/holdings`
- `GET /api/holdings/aggregated`
- `POST /api/holdings/sync`
- `POST /api/holdings/us/upload`
- `POST /api/holdings/us/refresh-prices`
- `POST /api/holdings/fd/upload`
- `POST /api/holdings/fd/refresh-values`

### 7.4 Portfolio analytics

- `GET /api/analytics/portfolio-value-history`
- `GET /api/analytics/sector-breakdown`
- `GET /api/analytics/performance-metrics`
- `GET /api/analytics/correlation-matrix`
- `GET /api/analytics/heatmap`

### 7.5 Bank accounts and statements

- `GET /api/bank-accounts`
- `POST /api/bank-accounts`
- `GET /api/bank-accounts/:id`
- `PUT /api/bank-accounts/:id`
- `DELETE /api/bank-accounts/:id` — permanent deletion
- `POST /api/bank-accounts/:id/statements/upload`
- `GET /api/bank-accounts/:id/statements`
- `POST /api/statements/:id/parse`
- `GET /api/statements/:id`
- `DELETE /api/statements/:id`
- `GET /api/statements/:id/preview`
- `POST /api/statements/:id/approve`

### 7.6 Transactions, categories, and bank analytics

- `GET /api/bank-accounts/:id/transactions`
- `GET /api/transactions/search`
- `PUT /api/transactions/:id`
- `DELETE /api/transactions/:id`
- `POST /api/transactions/bulk-recategorize`
- `GET /api/categories`
- `GET /api/bank-accounts/:id/analytics/balance-trend`
- `GET /api/bank-accounts/:id/analytics/category-breakdown`
- `GET /api/bank-accounts/:id/analytics/cashflow`
- `GET /api/bank-accounts/:id/analytics/top-merchants`
- `GET /api/bank-accounts/:id/analytics/anomalies`
- `GET /api/bank-accounts/:id/analytics/predictions`

Except for registration, login, and health, the application APIs require a
valid dashboard JWT. Resource endpoints perform their own ownership checks in
addition to authentication.

## 8. Test suite expansion

### 8.1 Backend

The backend suite now covers 329 passing tests. Coverage was expanded across:

- application-factory ordering and security headers;
- production configuration rejection;
- registration, login, inactive users, logout, and token revocation;
- account ownership and server-owned Kite reconnect URLs;
- Kite equity/mutual-fund synchronization and partial failures;
- account-scoped snapshots and concurrent writer serialization;
- family/member tenant isolation;
- snapshot numeric and aggregate overflow rejection;
- history boundaries, currencies, and removed-currency tombstones;
- atomic US/FD imports and refreshes;
- FD Decimal calculations and derived precision;
- bank account encryption and masked serialization;
- statement upload idempotency, leases, multi-page parsing, page caps, overlap,
  preview, approval, retry, discard, and cleanup;
- startup permission reconciliation and symlink refusal;
- permanent account deletion, orphan PDFs, failure recovery, and retry;
- transaction queries, mutations, balance recalculation, and categories;
- bank analytics ownership and exact output contracts;
- clean and populated migration upgrades.

Important new/expanded test modules include:

- [`test_app_factory.py`](../backend/tests/test_app_factory.py)
- [`test_fd_service.py`](../backend/tests/test_fd_service.py)
- [`test_hardening_regressions.py`](../backend/tests/test_hardening_regressions.py)
- [`test_kite_sync.py`](../backend/tests/test_kite_sync.py)
- [`test_migrations.py`](../backend/tests/test_migrations.py)
- [`test_portfolio_security.py`](../backend/tests/test_portfolio_security.py)
- [`test_portfolio_service.py`](../backend/tests/test_portfolio_service.py)
- [`test_statement_workflow.py`](../backend/tests/test_statement_workflow.py)

Statement storage is redirected to a temporary path by an autouse fixture, so
tests cannot create financial-document artifacts inside the repository.

### 8.2 Frontend

The frontend now has 83 passing tests across 9 Vitest files. They cover:

- authentication bootstrap, storage migration, logout, and `401` cleanup;
- API bearer-token behavior;
- account-store scope and reconnect behavior;
- holdings summaries, filtering, sorting, currencies, imports, and stale
  response handling;
- bank-account state, analytics parameters, selected-account rebinding, and
  request cancellation;
- transaction query construction and mutation refresh behavior;
- responsive navigation and route contracts;
- dedicated page, disclosure, and release UI contracts.

The suite is configured by
[`frontend/vitest.config.js`](../frontend/vitest.config.js) and uses the shared
isolated setup in
[`frontend/tests/setup.js`](../frontend/tests/setup.js).

### 8.3 Final validation record

The final release checks completed successfully:

| Check | Result |
| --- | --- |
| Backend pytest suite | 329 passed |
| Frontend Vitest suite | 83 passed in 9 test files |
| Vite production build | 465 modules transformed successfully |
| Python compilation | Passed for app, migrations, and tests |
| Python dependency consistency | `pip check` reported no broken requirements |
| Alembic graph | One head: `b15a7e4c2d90` |
| Repository whitespace check | `git diff --check` passed |
| Independent release/security audit | No release-blocking findings remained |

A registry-backed `npm audit` was not completed because external audit metadata
access was not authorized in the execution environment. This does not change
the recorded local test and production-build results.

## 9. Dependency and tooling changes

### 9.1 Backend dependencies

Security and compatibility-sensitive packages were updated and pinned,
including:

- Flask `3.1.3`;
- Flask-CORS `6.0.5`;
- Flask-JWT-Extended `4.7.4`;
- cryptography `48.0.1`;
- pyOpenSSL `26.2.0`;
- requests `2.34.2`;
- Werkzeug `3.1.8`;
- pdfplumber `0.11.10`;
- pdfminer.six `20260107`.

Spreadsheet and quote support is explicit through `openpyxl`, `xlrd`, and
`finnhub-python`. The complete pins are in
[`backend/requirements.txt`](../backend/requirements.txt).

Python 3.10 or newer is supported; Python 3.11 or newer is recommended.

### 9.2 Frontend dependencies and scripts

The frontend toolchain was updated to:

- Vue `3.5.40`;
- Vite `8.1.5`;
- `@vitejs/plugin-vue` `6.0.8`;
- Vitest `4.1.10`.

New scripts:

```bash
npm test
npm run test:watch
```

The lockfile was regenerated for the updated dependency graph.

## 10. Configuration and operational changes

[`backend/.env.example`](../backend/.env.example) now documents:

- separate `SECRET_KEY` and `JWT_SECRET_KEY` generation;
- a stable Fernet `ENCRYPTION_KEY`;
- development and PostgreSQL database URLs;
- exact CORS origins;
- upload limits;
- memory versus database rate-limit storage;
- scheduler control;
- optional Finnhub and parser-provider keys.

Production invariants:

- use HTTPS;
- configure explicit frontend origins;
- use distinct high-entropy application and JWT secrets;
- retain the encryption key securely;
- use database-backed rate-limit counters;
- run the service as an unprivileged OS user;
- run exactly one scheduler process in a multi-worker deployment;
- apply Alembic migrations before starting the new application version.

## 11. Important behavior contracts

These choices are intentional and should not be changed accidentally:

1. **Claude Code remains canonical.** Other dashboard directories are not
   runtime dependencies.
2. **No implicit FX conversion.** Different currencies stay separate until a
   future explicit exchange-rate feature is designed.
3. **Snapshots are account-scoped and immutable.** Refreshes create history;
   they do not edit old snapshots.
4. **Failed refreshes are not current state.** Reads use the last completed
   snapshot.
5. **US and FD imports replace one asset slice.** They are complete lists, not
   deltas, and preserve other asset classes.
6. **A US refresh is all-or-nothing per account.** Partial quotes do not publish
   a mixed-age current snapshot.
7. **FD values are disclosed estimates.** They are not promises of bank payout
   value.
8. **Mutual-fund folios remain distinct.** Fractional units are preserved.
9. **Kite access tokens never reach the browser.** Reconnection uses a
   server-owned login URL and one-time request token.
10. **Zerodha account deletion is soft; bank account deletion is permanent.**
11. **Statement periods cannot overlap.** Boundary dates are inclusive.
12. **Bank balance uses the latest verified running balance and falls back to
    the preserved opening balance.**
13. **Private statement storage fails closed.** Links and special entries are
    never followed.
14. **Categories are a safe system taxonomy.** Private merchant descriptions
    are not learned into global matching rules.
15. **Late frontend responses cannot overwrite newer scope or account state.**

## 12. Documentation changes

The project documentation was rewritten to match the consolidated behavior:

- [`README.md`](../README.md) now describes the full product, security model,
  imports, snapshots, setup, and verification commands.
- [`GETTING_STARTED.md`](../GETTING_STARTED.md) now walks through secrets,
  migrations, registration, Kite connection/reconnection, scope selection,
  asset pages, imports, and test execution.
- [`backend/README.md`](../backend/README.md) now documents configuration,
  production validation, API routes, snapshots, imports, bank workflows,
  scheduler behavior, and security requirements.
- [`frontend/README.md`](../frontend/README.md) now documents routes, session
  handling, pages, scope, currencies, sorting/filtering, responsive behavior,
  state conventions, and test scripts.
- `docs/wiki.md` is this complete change record.

## 13. Component change map

This map identifies where each group of consolidation changes lives.

| Area | Changed or added components |
| --- | --- |
| Project documentation | `README.md`, `GETTING_STARTED.md`, `backend/README.md`, `frontend/README.md`, and this wiki |
| Backend bootstrap | `app/__init__.py`, `app/config.py`, `app/database.py`, `run.py`, and `.env.example` |
| Portfolio models | `models/account.py`, `models/holding.py`, `models/snapshot.py`, and `models/user.py` |
| Bank models | `models/bank_account.py`, `models/bank_statement.py`, `models/transaction.py`, `models/transaction_category.py`, and `models/parsing_template.py` |
| New security models | `models/revoked_token.py` and `models/rate_limit_bucket.py` |
| Portfolio routes | `routes/accounts.py`, `routes/holdings.py`, `routes/analytics.py`, and `routes/auth.py` |
| Bank routes | `routes/bank_accounts.py`, `routes/bank_statements.py`, `routes/transactions.py`, `routes/categories.py`, and `routes/bank_analytics.py` |
| Portfolio services | `services/portfolio_service.py`, `services/kite_service.py`, `services/scheduler_service.py`, and `services/analytics_service.py` |
| Import services | `services/us_holdings_service.py`, `services/finnhub_service.py`, and `services/fd_service.py` |
| Bank services | `services/bank_statement_service.py`, `services/pdf_parser_service.py`, `services/transaction_service.py`, `services/transaction_categorization_service.py`, and `services/bank_analytics_service.py` |
| Backend utilities | New `utils/auth.py`, plus `utils/encryption.py`, `utils/rate_limiter.py`, and `utils/validators.py` |
| Database history | The existing base migrations were repaired and revisions `d71c4a9e2f30`, `e82b91a7c4d6`, `f93c20b8d5e1`, `a04f31c9e762`, and `b15a7e4c2d90` were added |
| Backend tests | Existing auth/bank/transaction/parser/model suites were expanded; app-factory, FD, hardening, Kite-sync, migration, portfolio-security, portfolio-service, and statement-workflow suites were added |
| Frontend shell | `App.vue`, `main.js`, `router/index.js`, `assets/styles/main.css`, and `index.html` |
| Frontend state/API | `services/api.js` and the accounts, auth, bankAccounts, categories, and holdings Pinia stores |
| New frontend utilities | `utils/authSession.js`, `utils/currency.js`, `utils/holdings.js`, and `utils/transactions.js` |
| Dashboard components | `AccountSelector.vue`, `HoldingsTable.vue`, `PortfolioSummary.vue`, and `Sidebar.vue`; new `ChartPanel.vue` and `FixedDepositTable.vue` |
| Bank components | Account/upload/review modals, analytics charts, bank cards, transaction lists, and new `StatementHistory.vue` |
| Shared visual components | `DataCard.vue` and the bar, line, and pie chart wrappers |
| Frontend views | Accounts, Dashboard, Login, Register, Overview, Stocks, Mutual Funds, US Stocks, Fixed Deposits, and Bank Balances |
| Frontend tests/tooling | New `frontend/tests` suite, `vitest.config.js`, test scripts, upgraded package manifest, and regenerated lockfile |

## 14. Contributor checklist

Before changing or releasing this dashboard:

- preserve JWT and resource-level ownership checks;
- never serialize encrypted credentials, full bank numbers, private paths,
  hashes, parser leases, or tokens;
- preserve account and currency dimensions in new queries;
- create snapshots for valuation changes instead of mutating history;
- validate source rows and derived totals before committing imports;
- keep uploads private, bounded, content-checked, and temporary where possible;
- keep request-generation guards when adding asynchronous frontend loads;
- provide loading, empty, error, desktop, and mobile behavior for new pages;
- add backend and frontend regressions for behavior changes;
- run migrations and both complete test suites before release.

Recommended release commands:

```bash
cd backend
python -m alembic upgrade head
python -m pytest -q

cd ../frontend
npm test
npm run build
```
