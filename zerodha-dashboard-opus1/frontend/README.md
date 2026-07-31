# Frontend

Vue 3 client for the Zerodha Family Portfolio Dashboard. It provides authenticated account management, family/member portfolio scope, dedicated asset pages, responsive charts and holdings views, and secure request-token submission to the backend.

Node.js 20.19+ or 22.12+ is required by the current Vite toolchain.

## Stack

- Vue 3 Composition API
- Vue Router
- Pinia
- Axios
- Chart.js and vue-chartjs
- Vite
- Vitest

## Setup

From this directory:

```bash
npm install
```

The API defaults to `http://localhost:5000/api`. For another backend, create `.env.local`:

```env
VITE_API_BASE_URL=http://localhost:5000/api
```

Start development:

```bash
npm run dev
```

The development server normally listens on `http://localhost:5173`.

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the Vite development server |
| `npm test` | Run the Vitest suite once |
| `npm run test:watch` | Run Vitest in watch mode |
| `npm run build` | Produce the optimized `dist` build |
| `npm run preview` | Serve the production build locally |

Before handing off frontend changes, run:

```bash
npm test
npm run build
```

## Application Routes

Public:

- `/login`
- `/register`

Authenticated:

- `/dashboard/overview`
- `/dashboard/stocks`
- `/dashboard/mutual-funds`
- `/dashboard/us-stocks`
- `/dashboard/fixed-deposits`
- `/dashboard/bank-balances`
- `/accounts`

The router waits for the initial JWT check before resolving protected or guest-only navigation, which prevents a stored session from being treated as logged out during bootstrap.

## Authentication and Account Security

Registration and login keep the dashboard JWT in tab-scoped `sessionStorage`.
The API interceptor adds it as a Bearer token, and a `401` response clears the
session plus any token left by older builds. The backend remains authoritative:
every account and portfolio request is ownership-checked.

The Accounts screen follows a server-side Kite exchange:

1. The user enters a Kite API key and API secret.
2. The frontend requests a Kite login URL from the authenticated backend.
3. It verifies that the URL uses HTTPS and `kite.zerodha.com` before navigating.
4. The user pastes the one-time `request_token` into the account form.
5. The backend exchanges and encrypts the generated brokerage access token.

The frontend neither requests nor stores the resulting Kite access token. The retired `/auth/access-token` response flow must not be reintroduced.

For an expired session, **Reconnect** requests
`/accounts/:id/login-url`. The backend derives the trusted Kite URL from the
selected account’s encrypted API key; the user then submits a new one-time
request token to that same account.

Because the dashboard JWT is stored in the browser, avoid adding untrusted scripts, unsafe HTML rendering, or logs containing tokens and personal portfolio data. Production hosting should serve HTTPS and a strict Content Security Policy.

## Portfolio Scope and Currency

`AccountSelector.vue` exposes explicit **Family** and **Member** modes:

- Family loads the authenticated user’s latest available holdings across active accounts.
- Member requires a specific account and is used for account-specific syncs, FD recalculation, and US quote refresh.
- In Family mode, uploads require an explicit destination owner.

Domestic equities, mutual funds, and fixed deposits are displayed in INR. US equities are displayed in USD and excluded from the INR total. The Overview page renders the two currencies as separate sections rather than performing an implicit conversion.

## Asset Pages

### Overview

Displays domestic and US summaries separately, allocation and sector charts, performance views, history when its currency is unambiguous, and current holdings.

### Indian Stocks

Provides a dedicated domestic-equity summary, allocation charts, and a responsive holdings table.

### Mutual Funds

Shows Coin mutual funds on a dedicated INR page with:

- fractional units;
- folio-aware positions;
- largest-fund and return insights;
- scheme allocation and scheme-return charts;
- scheme, folio, and account search.

### US Stocks

Keeps all values in USD, displays quote source and price date, and visibly marks positions held at import cost when a live quote is unavailable.

The workbook must be a complete current list for one account:

- `Symbol`
- `Quantity`
- `Average Price`
- optional `Purchase Date`

Uploading replaces that account’s current US positions. It does not append rows.

### Fixed Deposits

Shows principal, accrued simple-interest estimates, maturity state, and bank
concentration in INR. Estimates stop at maturity and do not include compounding,
payout schedules, taxes, or bank-specific terms.

The workbook accepts:

- `Bank Name`
- `Investment Amount`
- `Investment Date`
- `Interest Rate`
- optional `Maturity Date`
- optional `Deposit ID`

Uploading replaces that account’s current FD list. Recalculation is available only after selecting Member scope.

### Bank Balances

Manages user-owned bank accounts, statement upload and review, transactions,
and cash-flow/category analytics. Failed statement parses can be retried or
discarded; overlapping statement periods are rejected. Bank-account deletion
is explicitly permanent and removes its related statement data.

## Sorting, Filtering, and Responsive Behavior

The shared holdings table supports:

- search by symbol and descriptive metadata;
- asset-type filtering when multiple types are present;
- profitable/loss-making position filters;
- clickable desktop column sorting;
- a mobile sort selector and ascending/descending toggle;
- responsive card output on narrow screens;
- explicit loading, empty, filtered-empty, and error states.

Charts and summary grids adapt to available width. The navigation collapses for mobile use, and import forms move from multi-column layouts to touch-friendly stacked layouts.

## Project Structure

```text
src/
├── assets/styles/main.css
├── components/
│   ├── bank/              # Bank cards, statements, transactions, analytics
│   ├── charts/            # Chart.js wrappers
│   ├── common/            # Shared data and loading components
│   └── dashboard/         # Scope selector, sidebar, summaries, tables
├── router/index.js
├── services/api.js
├── stores/                # Auth, accounts, holdings, bank, UI, categories
├── utils/holdings.js      # Shared filtering, sorting, and labels
├── views/
│   ├── auth/
│   ├── dashboard/
│   ├── Accounts.vue
│   └── Dashboard.vue
├── App.vue
└── main.js
```

Tests are in `tests/` and use isolated in-memory browser-storage fakes from
`tests/setup.js`.

## State and API Conventions

- `auth.js` owns session bootstrap and cleanup.
- `accounts.js` owns the current Family/Member scope and account CRUD.
- `holdings.js` owns portfolio data, currency-specific summaries, analytics, sync, and imports.
- `bankAccounts.js` and `categories.js` own the bank-data workflows.
- `api.js` is the single Axios client and injects the JWT for all protected requests.

Components should not add INR and USD amounts themselves. New portfolio features should consume currency-labeled backend data and render each currency independently unless an explicit exchange-rate feature is introduced.

Uploads should always display the destination account and replacement semantics before submission. Refresh actions that require a single owner should remain disabled in Family scope.
