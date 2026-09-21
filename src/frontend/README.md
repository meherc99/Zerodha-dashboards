# Frontend

Vue 3 client for the Zerodha Family Portfolio Dashboard. It provides
authenticated account management, family/member portfolio scope, dedicated asset
pages, responsive charts and holdings views, and secure request-token submission
to the backend.

> Page behavior, scope/currency rules, session hardening, and state conventions
> are detailed in [../../docs/wiki.md](../../docs/wiki.md). This README is the
> at-a-glance frontend guide. Node.js 20.19+ or 22.12+ is required.

## Stack

Vue 3 (Composition API), Vue Router, Pinia, Axios, Chart.js + vue-chartjs, Vite,
Vitest.

## Setup

Configuration comes from the single **repository-root** [.env](../../.env);
Vite's `envDir` (in [vite.config.js](vite.config.js)) points there. The client
reads `VITE_API_BASE_URL` (default `http://localhost:5000/api`) and
`VITE_DEMO_MODE`.

```bash
npm install
npm run dev            # http://localhost:5173
```

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the Vite dev server |
| `npm test` | Run the Vitest suite once |
| `npm run test:watch` | Vitest in watch mode |
| `npm run build` | Produce the optimized `dist` build |
| `npm run preview` | Serve the production build locally |

Before handing off changes, run `npm test` and `npm run build`.

## Routes

- Public: `/login`, `/register`
- Authenticated: `/dashboard/overview`, `/dashboard/stocks`,
  `/dashboard/mutual-funds`, `/dashboard/us-stocks`, `/dashboard/fixed-deposits`,
  `/dashboard/bank-balances`, `/accounts`

The router waits for the initial JWT check before resolving protected/guest
navigation, so a stored session is not briefly treated as logged out.

## Scope, currency, and security

- `AccountSelector.vue` exposes **Family** and **Member** modes; Family-mode
  uploads require an explicit destination owner.
- Domestic assets and FDs display in INR; US equities in USD, shown as separate
  sections rather than an implicit conversion.
- The JWT is kept in tab-scoped `sessionStorage`; the single Axios client injects
  it and a `401` clears the session. Brokerage access tokens are never requested
  or stored by the frontend; the retired `/auth/access-token` flow must not be
  reintroduced.

## Structure

```text
src/
├── assets/styles/main.css
├── components/   # bank/, charts/, common/, dashboard/
├── router/index.js
├── services/api.js          # single Axios client, injects JWT
├── stores/                  # auth, accounts, holdings, bankAccounts, categories, ui
├── utils/                   # currency, holdings, transactions, authSession helpers
├── views/                   # auth/, dashboard/, Accounts.vue, Dashboard.vue
├── App.vue
└── main.js
```

Tests are in `tests/` and use isolated in-memory browser-storage fakes from
`tests/setup.js`.

## Conventions

- Stores own API calls and state (`auth`, `accounts`, `holdings`, `bankAccounts`,
  `categories`); components read via `storeToRefs()`.
- Components must not add INR and USD amounts; consume currency-labeled backend
  data and render each currency independently.
- Uploads must show the destination account and replacement semantics before
  submission; single-owner refresh actions stay disabled in Family scope.

See [../../docs/wiki.md §4](../../docs/wiki.md#4-feature-reference) for per-page
detail.
