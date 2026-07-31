# Getting Started

This guide takes a new checkout from an empty local database to an authenticated family portfolio.

## Prerequisites

- Python 3.10 or newer (3.11+ recommended)
- Node.js 20.19+ or 22.12+ (Node.js 24 LTS is also supported)
- A Kite Connect application if you want to sync Zerodha and Coin holdings
- A Finnhub API key if you want live US quote refreshes

You can run and test the application without brokerage credentials, but live Zerodha sync requires a valid Kite application.

## 1. Configure the Backend

Run these commands from the project root:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

On Windows PowerShell, activate the environment with:

```powershell
venv\Scripts\Activate.ps1
```

Generate three different secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Edit `backend/.env` and assign the first random value to `SECRET_KEY`, the second to `JWT_SECRET_KEY`, and the Fernet value to `ENCRYPTION_KEY`. The development defaults for the remaining settings are usable locally.

If you plan to refresh US prices, also set:

```env
FINNHUB_API_KEY=your-finnhub-api-key
```

Do not commit `.env`. Keep the Fernet key stable: it is required to decrypt saved Kite credentials.

## 2. Apply Database Migrations

From `backend`, with the virtual environment active:

```bash
python -m alembic upgrade head
```

Alembic uses the same resolved `DATABASE_URL` as the Flask application. The default SQLite URL creates the database under Flask’s `backend/instance` directory. For PostgreSQL, set `DATABASE_URL` before running the migration.

Use migrations for schema setup and upgrades; do not replace them with an ad hoc `db.create_all()` workflow. Back up an existing database before upgrading it.

## 3. Start the Backend

```bash
python run.py
```

The API is available at `http://localhost:5000`. Check it with:

```bash
curl http://localhost:5000/api/health
```

`run.py` starts the periodic scheduler when `SCHEDULER_ENABLED=true`. The application factory used by tests and Alembic does not start it.

## 4. Configure and Start the Frontend

Open another terminal at the project root:

```bash
cd frontend
npm install
```

The frontend defaults to `http://localhost:5000/api`. To override it, create `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://localhost:5000/api
```

Start the development server:

```bash
npm run dev
```

Open `http://localhost:5173`.

## 5. Register a Dashboard User

Select **Register**, then provide:

- a valid email address;
- a password between 8 and 1024 characters;
- an optional full name.

Registration returns an application JWT and signs the browser in. Login restores the user with `GET /api/auth/me`; invalid, logged-out, or inactive-user tokens are rejected. Portfolio data belonging to another user cannot be selected by changing an account ID.

## 6. Connect a Zerodha Account

Open **Accounts** and start a new account:

1. Enter a family-facing account name, the Kite API key, and the Kite API secret.
2. Select **Open Zerodha Login**. The frontend accepts only an HTTPS login URL on `kite.zerodha.com`.
3. Complete the login on Zerodha.
4. Copy the one-time `request_token` query parameter from the redirect URL.
5. Paste the request token into the account form and save.

The browser sends the request token to the account endpoint. The backend uses
it once to obtain a Kite access token, discards the one-time request token,
encrypts the API key, API secret, and access token, and returns only
nonsensitive account metadata.

Do not call `POST /api/auth/access-token`: that legacy endpoint intentionally returns `410 Gone` so brokerage access tokens are never sent back to the browser.

To renew an expired Kite session, select **Reconnect** on the existing account.
The backend creates the login URL from that account’s encrypted API key, so the
browser does not need the stored key or secret. Complete the login and submit
the new one-time request token to update the same account.

## 7. Sync and Choose Portfolio Scope

On the Dashboard:

- choose **Family** to combine the latest completed snapshot from each active account owned by the signed-in user;
- choose **Member**, then select one family account, to inspect or refresh only that account;
- select **Sync portfolio** to fetch Kite equities and Coin mutual funds.

Each account sync creates its own snapshot. Family history and current holdings are assembled from account-scoped data, so a partial failure does not replace a successful sibling account snapshot.

Mutual-fund data is fetched from Kite’s mutual-fund holdings API. Fractional units are preserved, and positions with different folios are not collapsed into one holding.

## 8. Use the Asset Pages

The authenticated dashboard contains:

- **Overview**: domestic INR and US USD summaries shown separately, allocation charts, performance views, and recent holdings;
- **Indian Stocks**: searchable, filterable, and sortable domestic equity holdings;
- **Mutual Funds**: dedicated INR fund summary, folio-aware holdings, allocation, and return views;
- **US Stocks**: USD-only holdings, workbook import, quote provenance, and price refresh;
- **Fixed Deposits**: INR principal, simple-interest accrual, maturity details, workbook import, and recalculation;
- **Bank Balances**: owned bank accounts, statements, transactions, and analytics.

Tables adapt to mobile cards on narrow screens. Search, asset type, profit/loss filtering, sortable columns, and ascending/descending controls are available where applicable.

## 9. Import US Holdings

Create a complete `.xlsx` or `.xls` workbook for one account:

| Column | Required | Example |
| --- | --- | --- |
| `Symbol` | Yes | `AAPL` |
| `Quantity` | Yes | `2.5` |
| `Average Price` | Yes | `182.50` |
| `Purchase Date` | No | `2025-01-15` |

Select the destination account explicitly when the dashboard is in Family scope.

Important: every upload replaces the selected account’s current US holdings list. Include every current US position in the workbook. Validation is atomic: malformed rows, duplicate symbols, or more than 100 positions reject the whole workbook without replacing the previous snapshot. The snapshot carries the account’s other asset classes forward. Values are stored and displayed in USD; they are not added to INR totals. When a quote cannot be retrieved, the UI identifies the position as valued at import cost.

## 10. Import Fixed Deposits

Create a complete `.xlsx` or `.xls` workbook:

| Column | Required | Example |
| --- | --- | --- |
| `Bank Name` | Yes | `HDFC Bank` |
| `Investment Amount` | Yes | `250000` |
| `Investment Date` | Yes | `2025-01-15` |
| `Interest Rate` | Yes | `7.25` |
| `Maturity Date` | No | `2027-01-15` |
| `Deposit ID` | No | `FD-2025-001` |

The amount must be positive, the rate must be greater than zero and no more than 100, and maturity cannot precede investment.

An FD upload is also a complete replacement for that account’s FD list. Every
non-empty row must be valid and `Deposit ID` values must be unique; otherwise
the existing FD snapshot is left untouched. The service uses simple interest
and stops accrual at maturity. The displayed current value is an estimate: it
does not model compounding, payout schedules, taxes, or bank-specific terms.
All values remain in INR.

Both import types require an authenticated, owned destination account. Files are size-limited, extension-, signature-, member-count-, and expanded-size-checked, processed through randomized temporary paths, and deleted after processing.

## 11. Run the Test Suites

Backend:

```bash
cd backend
source venv/bin/activate
python -m pytest tests
```

Frontend:

```bash
cd frontend
npm test
npm run build
```

Use `npm run test:watch` while developing frontend tests.

## Troubleshooting

### `ModuleNotFoundError` when starting the backend

Activate `backend/venv` and reinstall:

```bash
python -m pip install -r requirements.txt
```

### Encryption-key errors

`ENCRYPTION_KEY` must be a valid Fernet key. Generate it with the command in step 1. If the database already contains encrypted credentials, use the same key that created them.

### The frontend receives connection or CORS errors

- Confirm that the backend is listening on port 5000.
- Confirm `VITE_API_BASE_URL` ends in `/api`.
- Confirm `CORS_ORIGINS` includes the exact frontend origin, including its port.
- Restart both processes after changing environment files.

### Registration or login is rate-limited

Registration and login endpoints have IP-based limits. Wait for the window to expire rather than retrying continuously.

### Zerodha sync reports an expired or invalid session

Open the account editor, complete the Kite login again, and submit a fresh request token. Request tokens are one-time values.

### A US quote is missing

Check `FINNHUB_API_KEY` and the provider’s response or rate limits. Imported positions remain visible at cost with their source status instead of being silently dropped.

### A portfolio page looks empty after an import

Confirm the Family/Member scope and the destination account selected during upload. US and FD workbooks replace only that asset class for the chosen account.

## Production Checklist

- Set `FLASK_ENV=production`.
- Use strong independent `SECRET_KEY` and `JWT_SECRET_KEY` values and a protected Fernet key.
- Run `python -m alembic upgrade head` against the production database before deploying the new process.
- Serve the frontend and API over HTTPS.
- Restrict `CORS_ORIGINS` to trusted frontend origins.
- Set `RATELIMIT_STORAGE=database`; production startup rejects process-local
  counters.
- Use an unprivileged service account and private database/upload permissions.
- Put upload and request-size limits at both the reverse proxy and Flask layers.
- Keep `RATELIMIT_ENABLED=true`; SQL-backed counters are shared across web
  workers and restarts. An additional edge limit remains recommended.
- Run only one scheduler instance, or set `SCHEDULER_ENABLED=false` in ordinary web workers.
- Keep JWTs and all Kite tokens out of logs, diagnostics, URLs, and support captures.
