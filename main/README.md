# Zerodha Family Portfolio Dashboard

A self-hosted Flask and Vue application for reviewing a family’s Indian equities, mutual funds, fixed deposits, US equities, and bank activity without mixing account ownership or currencies.

## Highlights

- JWT registration and login protect the application and API; logout revokes
  the presented token server-side.
- Every Zerodha account, bank account, snapshot, holding, import, and analytic query is scoped to its owning user.
- The Family/Member switch shows either the authenticated user’s combined family view or one selected account.
- Broker sync reads Kite equity holdings and Coin mutual-fund holdings independently. Mutual-fund units remain fractional and separate folios remain separate positions.
- Each account has its own immutable portfolio snapshots. Family views combine the latest completed snapshot from each selected account, so one failed sync does not replace another account’s good data.
- Dedicated Overview, Indian Stocks, Mutual Funds, US Stocks, Fixed Deposits, and Bank Balances pages provide responsive cards, charts, tables, mobile layouts, search, filtering, and sorting.
- INR domestic assets and USD holdings are summarized separately. The application does not silently add or convert them.
- Kite credentials, brokerage access tokens, and bank account numbers are
  encrypted at rest. Brokerage access tokens and full bank account numbers are
  never returned to the frontend.

## Technology

- Backend: Flask, Flask-SQLAlchemy, Flask-JWT-Extended, APScheduler, Alembic, Kite Connect, pandas
- Frontend: Vue 3, Pinia, Vue Router, Chart.js, Axios, Vite
- Database: SQLite for local development; PostgreSQL is supported through `DATABASE_URL`
- Tests: pytest for the backend; Vitest for frontend logic and state

## Repository Layout

```text
.
├── backend/
│   ├── alembic/             # Versioned database migrations
│   ├── app/
│   │   ├── models/          # SQLAlchemy models
│   │   ├── routes/          # Authenticated API routes
│   │   ├── services/        # Sync, valuation, analytics, and imports
│   │   └── utils/           # Auth, encryption, validation, and rate limiting
│   ├── tests/
│   ├── .env.example
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── src/
│   ├── tests/
│   └── package.json
├── GETTING_STARTED.md
└── README.md
```

## Quick Start

Prerequisites:

- Python 3.10 or newer (3.11+ recommended)
- Node.js 20.19+ or 22.12+ (Node.js 24 LTS is also supported)
- A Kite Connect application for live Zerodha sync
- A Finnhub API key only if US quote refreshes are required

Start the backend:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Generate independent application and JWT secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Put those values in `backend/.env`, then migrate and run:

```bash
python -m alembic upgrade head
python run.py
```

The API listens on `http://localhost:5000` by default. The scheduler starts only from `run.py`; importing the application factory for tests or migrations does not start background threads.

Start the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, register a dashboard user, and add an account. See [GETTING_STARTED.md](GETTING_STARTED.md) for the complete setup and Kite login flow.

## Authentication and Kite Session Flow

The dashboard has two distinct authentication layers:

1. `POST /api/auth/register` or `POST /api/auth/login` returns the dashboard JWT used as `Authorization: Bearer <token>`.
2. On the Accounts page, enter the account name, Kite API key, and Kite API secret.
3. Open the trusted Kite login URL, complete the Zerodha login, and copy the one-time `request_token` from the redirect URL.
4. Submit that request token with the account form. The backend exchanges it
   once, discards it, and encrypts the API credentials and resulting access
   token before persistence.

The response never contains the Kite access token. `POST /api/auth/access-token` is intentionally retired and returns `410 Gone`; clients must submit `request_token` to `POST /api/accounts` or `PUT /api/accounts/:id`.

Kite sessions expire according to Zerodha’s rules. When a session expires, use
**Reconnect** on the existing account. The backend builds its login URL from
the encrypted server-side API key, then exchanges the new one-time request
token without creating a duplicate account.

## Portfolio and Import Semantics

### Zerodha sync

A manual or scheduled sync creates a completed snapshot per account and fetches equities and mutual funds through their respective Kite APIs. The latest completed snapshot is used for reads; failed attempts do not become the current portfolio.

### US holdings

The US page accepts `.xlsx` or `.xls` with these columns:

- `Symbol`
- `Quantity`
- `Average Price`
- `Purchase Date` (optional)

An upload is a complete replacement of the selected account’s current US positions, not an append. The complete workbook is validated before a snapshot is created; one malformed or duplicate row rejects the entire upload and leaves the prior positions intact. Other asset classes are carried into the new account snapshot. Values remain in USD. If a live quote is unavailable during import, the position is visibly retained at import cost rather than presented as a current quote. A later price refresh is published only when every symbol for that account receives a valid quote.

### Fixed deposits

The Fixed Deposits page accepts `.xlsx` or `.xls` with:

- `Bank Name`
- `Investment Amount`
- `Investment Date`
- `Interest Rate`
- `Maturity Date` (optional)
- `Deposit ID` (optional, recommended for stable identity)

An upload replaces the selected account’s complete FD list while preserving its other asset classes. Workbook validation is all-or-nothing, including duplicate `Deposit ID` checks and derived-value precision bounds. Fixed-deposit values are explicitly presented as simple-interest estimates through the earlier of the valuation date or maturity date; compounding, payout schedules, taxes, and bank-specific terms are not modeled. Values remain denominated in INR.

Spreadsheet uploads are limited by `MAX_UPLOAD_BYTES`, checked against their file signature and expanded archive size, processed from private randomized temporary files, and removed after processing.

### Bank statements

PDF statements are content-hashed per bank account, so an identical upload
cannot be approved twice. Parsing is explicitly claimed with a recoverable
lease, combines compatible transaction tables across pages, and produces one
canonical review format. Approval is a single claim-once transaction; approved
rows feed analytics as verified data while temporary parsed JSON is removed.
Statement periods for one account cannot overlap, including shared boundary
dates. Failed parses can be retried or discarded, account balances are
recalculated from the preserved opening balance and all verified transactions,
and deleting a bank account permanently removes its statements, transactions,
and all private PDF files in that account’s storage. Startup reconciles legacy
statement directories and files to owner-only permissions and refuses symbolic
links or special files.

## Database Migrations

Schema changes are versioned in `backend/alembic/versions`. From `backend`, run:

```bash
python -m alembic upgrade head
```

Run migrations before starting a new application version. `DATABASE_URL` selects the migration and runtime database. Back up an existing database before applying migrations in production.

## Verification

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

For interactive frontend test development, use `npm run test:watch`.

## Security Requirements

- Never commit `backend/.env`, API credentials, request tokens, access tokens, JWTs, uploaded statements, or database files.
- Use independent, high-entropy `SECRET_KEY` and `JWT_SECRET_KEY` values in production.
- Generate `ENCRYPTION_KEY` with Fernet and retain it securely. Changing or losing it makes stored Kite credentials unreadable.
- Set `FLASK_ENV=production`, use HTTPS, and restrict `CORS_ORIGINS` to the deployed frontend origins. Do not use `*`.
- Set `RATELIMIT_STORAGE=database` in production. The application refuses to
  start with process-local counters in production.
- Keep upload limits conservative, run the service as an unprivileged user, and protect database and upload directories with operating-system permissions.
- Treat the frontend’s JWT storage as sensitive: avoid untrusted scripts and deploy a strict Content Security Policy at the reverse proxy.
- The built-in scheduler belongs in only one process. In a multi-worker deployment, disable it with `SCHEDULER_ENABLED=false` and run one designated scheduler process.

Additional backend and frontend details are in [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md). The complete consolidation change record is in [docs/wiki.md](docs/wiki.md).
