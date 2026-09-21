# Getting Started

This guide takes you from an empty local checkout to an authenticated family
portfolio. For the full feature, API, schema, and configuration reference, see
[docs/wiki.md](docs/wiki.md).

## Prerequisites

- **Python** 3.10 or newer (3.11+ recommended)
- **Node.js** 20.19+ or 22.12+ (Node.js 24 LTS is also supported)
- A **Kite Connect** application — optional, only for live Zerodha sync
- A **Finnhub** API key — optional, only for live US quote refreshes

The application runs and its tests pass without brokerage credentials; live
Zerodha sync requires a valid Kite application.

## 1. Configure the environment

All configuration lives in a single [.env](.env) at the repository root, loaded
by the backend (`run.py` and Alembic) and by the frontend (Vite `envDir`).

Generate three secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"   # SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"   # JWT_SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # ENCRYPTION_KEY
```

Assign them in the root `.env`:

- first random value → `SECRET_KEY`
- second random value → `JWT_SECRET_KEY`
- Fernet value → `ENCRYPTION_KEY`

For optional live US pricing, set `FINNHUB_API_KEY`. The remaining defaults are
usable locally without changes. The complete variable table is in
[docs/wiki.md §8](docs/wiki.md#8-configuration-and-environment).

> Do not commit `.env`. Keep the Fernet key stable — it is required to decrypt
> saved Kite credentials, and you cannot switch keys once the database contains
> encrypted data.

## 2. Set up and start the backend

```bash
cd src/backend
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

Apply migrations (Alembic uses the same resolved `DATABASE_URL` as the app; the
default SQLite database is created under `src/backend/instance`):

```bash
python -m alembic upgrade head
```

Start the API:

```bash
python run.py
```

- API: `http://localhost:5000`
- Health check: `curl http://localhost:5000/api/health`

The periodic scheduler starts only when `SCHEDULER_ENABLED=true`; the application
factory used by tests and Alembic does not start background threads.

## 3. Start the frontend

In another terminal:

```bash
cd src/frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The client defaults to `http://localhost:5000/api`
(`VITE_API_BASE_URL` in the root `.env`).

## 4. Register a dashboard user

Choose **Register** and provide:

- a valid email address
- a password between 8 and 1024 characters
- an optional full name

Registration returns the application JWT and signs the browser in; a later login
is restored via `GET /api/auth/me`. Portfolio data belonging to another user
cannot be accessed by changing an account ID.

## 5. Connect a Zerodha account

On the **Accounts** page:

1. Enter a family-facing account name, Kite API key, and Kite API secret.
2. Select **Open Zerodha Login** (the frontend only navigates to HTTPS on
   `kite.zerodha.com`) and complete the Zerodha login.
3. Copy the one-time `request_token` from the redirect URL.
4. Paste it into the account form and save.

The backend exchanges the request token once, discards it, and encrypts the API
key, secret, and resulting access token — the browser never receives the access
token. `POST /api/auth/access-token` is intentionally retired and returns
`410 Gone`.

For an expired session, use **Reconnect**: the backend builds the login URL from
the account's encrypted API key, and you submit a fresh request token to the same
account. Accounts may also be created with a name only (no Kite credentials) and
populated with manual US/FD imports.

## 6. Sync and choose scope

On the dashboard:

- **Family** combines the latest completed snapshot from each active account you
  own; **Member** targets one account for sync, refresh, or recalculation.
- **Sync portfolio** fetches Kite equities and Coin mutual funds. Each account
  sync creates its own snapshot, and a partial failure never replaces a
  successful sibling account. Fractional mutual-fund units and separate folios
  are preserved.

## 7. Use the asset pages

Overview, Indian Stocks, Mutual Funds, US Stocks, Fixed Deposits, and Bank
Balances each provide responsive cards, charts, tables, search, filtering, and
sorting. INR and USD summaries are shown separately. Per-page behavior is
detailed in [docs/wiki.md §4](docs/wiki.md#4-feature-reference).

### Import US holdings

`.xlsx`/`.xls` with columns `Symbol`, `Quantity`, `Average Price`, and optional
`Purchase Date`. Each upload **replaces** the selected account's US positions
(include every current position), values stay in USD, and validation is
all-or-nothing (≤100 positions; malformed or duplicate rows reject the whole
workbook). In Family scope, choose the destination account explicitly.

### Import fixed deposits

`.xlsx`/`.xls` with `Bank Name`, `Investment Amount`, `Investment Date`,
`Interest Rate`, and optional `Maturity Date` and `Deposit ID`. Each upload
replaces the account's FD list; values are INR simple-interest estimates that
stop accruing at maturity. Column details and the formula are in
[docs/wiki.md §5](docs/wiki.md#5-import-data-formats).

## 8. Run the tests

```bash
cd src/backend && source venv/bin/activate && python -m pytest tests
cd ../frontend && npm test && npm run build      # npm run test:watch for dev
```

## Troubleshooting

- **`ModuleNotFoundError` on backend start** — activate `src/backend/venv` and
  reinstall with `python -m pip install -r requirements.txt`.
- **Encryption-key errors** — `ENCRYPTION_KEY` must be a valid Fernet key, and
  the same key that encrypted any existing data.
- **Frontend connection/CORS errors** — confirm the backend on port 5000,
  `VITE_API_BASE_URL` ends in `/api`, and `CORS_ORIGINS` includes the exact
  frontend origin (with port); restart both processes after editing `.env`.
- **Auth rate-limited** — wait for the window to expire; do not retry
  continuously.
- **Expired Zerodha session** — reconnect the account and submit a fresh one-time
  request token.
- **US quote missing** — check `FINNHUB_API_KEY` and provider limits; positions
  remain visible at import cost.
- **Empty page after import** — confirm Family/Member scope and the destination
  account; US/FD workbooks replace only that asset class for the chosen account.

## Production checklist

- Set `FLASK_ENV=production` with distinct high-entropy `SECRET_KEY` and
  `JWT_SECRET_KEY`, and a protected, stable Fernet `ENCRYPTION_KEY`.
- Run `python -m alembic upgrade head` against the production database before
  deploying a new version.
- Serve the frontend and API over HTTPS and restrict `CORS_ORIGINS` (no `*`).
- Set `RATELIMIT_STORAGE=database` (production rejects process-local counters)
  and keep `RATELIMIT_ENABLED=true`.
- Enforce upload/request-size limits at both the reverse proxy and Flask.
- Run as an unprivileged user with private database/upload permissions, and run
  exactly one scheduler process (`SCHEDULER_ENABLED=false` on other workers).
- Keep JWTs and Kite tokens out of logs, URLs, and diagnostics.

See [docs/wiki.md](docs/wiki.md) for the complete reference.
