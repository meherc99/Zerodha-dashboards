# Backend

Flask API for the Zerodha Family Portfolio Dashboard. It owns authentication, account isolation, encrypted brokerage credentials, account-scoped snapshots, portfolio imports, bank-statement processing, analytics, and scheduled Kite synchronization.

## Design

- `create_app()` configures Flask and extensions without starting worker threads.
- `run.py` is the executable entry point and starts the scheduler when enabled.
- Flask-JWT-Extended authenticates application users. A global user lookup
  rejects deleted or inactive users, and logout persists the token identifier
  in a server-side revocation list.
- Account lookup helpers enforce ownership before reads, writes, refreshes, uploads, or analytics.
- Each completed snapshot belongs to one Zerodha account. Current family data is assembled from the latest completed snapshot for each owned account.
- A failed account sync is recorded separately and does not replace that account’s latest good state.
- Kite equity holdings and mutual-fund holdings are fetched separately. Numeric columns support fractional quantities, and mutual-fund folios participate in holding identity.
- INR and USD totals are grouped by currency; they are never silently combined.

## Setup

Python 3.10 or newer is required; Python 3.11+ is recommended.

From this directory:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Generate secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Use separate random values for `SECRET_KEY` and `JWT_SECRET_KEY`, and use the Fernet output for `ENCRYPTION_KEY`.

### Environment Variables

| Variable | Purpose | Local default |
| --- | --- | --- |
| `FLASK_ENV` | `development` or `production` configuration | `development` |
| `SECRET_KEY` | Flask signing secret; must be replaced in production | insecure development fallback |
| `JWT_SECRET_KEY` | JWT signing secret; should differ from `SECRET_KEY` | falls back to `SECRET_KEY` |
| `ENCRYPTION_KEY` | Fernet key for Kite credentials and tokens | required when accounts are saved |
| `DATABASE_URL` | Runtime and Alembic database URL | `sqlite:///zerodha_dashboard.db` |
| `PORT` | HTTP listen port used by `run.py` | `5000` |
| `CORS_ORIGINS` | Comma-separated trusted frontend origins | `http://localhost:5173` |
| `SCHEDULER_ENABLED` | Start the APScheduler worker from `run.py` | `true` |
| `SYNC_INTERVAL_HOURS` | Scheduled Kite sync interval | `12` |
| `MAX_UPLOAD_BYTES` | Flask request-size limit | `10485760` |
| `RATELIMIT_ENABLED` | Enforce route-specific request limits | `true` |
| `RATELIMIT_STORAGE` | `memory` for local work; shared `database` counters are required in production | `memory` |
| `FINNHUB_API_KEY` | Optional live US quote provider key | unset |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Optional AI-assisted bank-statement parser key | unset |
| `CELERY_BROKER_URL` | Celery message broker (e.g. `redis://localhost:6379/0`); when unset, PDF parsing runs synchronously | unset |
| `CELERY_RESULT_BACKEND` | Celery result store; should match `CELERY_BROKER_URL` | unset |

`FLASK_ENV=production` requires distinct Flask/JWT secrets of at least 32
bytes, a valid Fernet `ENCRYPTION_KEY`, explicit non-wildcard CORS origins, and
`RATELIMIT_STORAGE=database`. An unknown or omitted environment never falls
back to development settings.

## Migrations

Alembic migrations live in `alembic/versions` and use the same Flask-resolved database URL as the application.

Apply all migrations:

```bash
python -m alembic upgrade head
```

Inspect the current migration:

```bash
python -m alembic current
```

Create a migration after an intentional model change:

```bash
python -m alembic revision --autogenerate -m "describe the schema change"
```

Review generated migrations before applying them. Back up persistent data before production upgrades. Do not use `db.create_all()` as a substitute for the migration chain.

### Linking orphaned Zerodha accounts to a user

Revision `4b86235fc91f` added the `users` table and made `accounts.user_id`
a **nullable** foreign key.  Accounts created before that migration (or in a
pre-auth development database) will have `user_id = NULL` and will be
invisible to the authenticated API.

Run the one-time helper script to assign those accounts to a user:

```bash
# Preview what would change without writing:
python scripts/migrate_orphaned_accounts.py --dry-run

# Apply:
python scripts/migrate_orphaned_accounts.py
```

The script will:
1. Report the number of orphaned accounts it finds.
2. If the `users` table is empty, interactively create an admin user.
3. If exactly one user exists, assign all orphaned accounts to that user.
4. If multiple users exist, present a numbered list and ask you to choose.
5. Ask for confirmation, then commit.

The script is idempotent; running it again when no orphans remain is a no-op.

## Run

```bash
python run.py
```

The API listens on `http://localhost:5000` unless `PORT` is set. `GET /api/health` is the health endpoint.

The application factory is safe to use from pytest and Alembic because it only attaches the scheduler service. The background scheduler is started explicitly by `run.py`.

## Authentication

Public endpoints:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/health`

Registration accepts `email`, `password`, and optional `full_name`. Passwords must contain 8–1024 characters and are stored as PBKDF2 hashes. Registration and login are rate-limited.

Protected requests require:

```http
Authorization: Bearer <dashboard-jwt>
```

Useful authentication endpoints:

- `GET /api/auth/me` validates the JWT and returns its active user.
- `POST /api/auth/logout` revokes the presented access token in the database.
- `POST /api/auth/login-url` accepts a Kite `api_key` and returns the Zerodha login URL.
- `POST /api/auth/access-token` is retired and always returns `410 Gone`.

The supported Kite flow sends the one-time `request_token` to an account create or update endpoint. The server exchanges it using the account’s API secret, encrypts the generated access token, and never includes it in an API response.

## Core Portfolio API

Every endpoint below requires a dashboard JWT.

### Zerodha accounts

- `GET /api/accounts`
- `POST /api/accounts`
- `GET /api/accounts/:id`
- `GET /api/accounts/:id/login-url` — builds a reconnect URL from the encrypted server-side API key
- `PUT /api/accounts/:id`
- `DELETE /api/accounts/:id` — soft-deactivates the account

Create an account with:

```json
{
  "account_name": "Family Member",
  "api_key": "kite-api-key",
  "api_secret": "kite-api-secret",
  "request_token": "one-time-request-token"
}
```

Account names are unique per dashboard user. API keys, secrets, and tokens are encrypted and omitted from account responses.

### Holdings and sync

- `GET /api/holdings`
- `GET /api/holdings/aggregated`
- `POST /api/holdings/sync`
- `POST /api/holdings/us/upload`
- `POST /api/holdings/us/refresh-prices`
- `POST /api/holdings/fd/upload`
- `POST /api/holdings/fd/refresh-values`

`GET /api/holdings` supports:

- `account_id` for one owned account, otherwise family scope;
- `instrument_type`: `equity`, `mf`, `us_equity`, or `fd`;
- `search` across symbol and account name;
- `sort_by`: symbol, account name, quantity, price, value, P&L, or day-change fields;
- `sort_order`: `asc` or `desc`.

Manual sync accepts an optional JSON `account_id`. With no account ID, it syncs all active accounts owned by the authenticated user. The response reports completed, failed, or partial status for the batch.

US and FD uploads are multipart requests with `file` and `account_id`. Only `.xlsx` and `.xls` signatures are accepted. The server uses randomized temporary files and removes them after processing.

Imports are replacement operations for the selected account and asset type:

- a US workbook replaces that account’s current `us_equity` positions and preserves its other holdings;
- an FD workbook replaces that account’s current `fd` positions and preserves its other holdings.

Clients should therefore upload a complete current list, not a delta. Parsing
and validation are all-or-nothing: an invalid or duplicate row returns `400`
before any replacement snapshot is created.

### Analytics

- `GET /api/analytics/portfolio-value-history`
- `GET /api/analytics/sector-breakdown`
- `GET /api/analytics/performance-metrics`
- `GET /api/analytics/correlation-matrix`
- `GET /api/analytics/heatmap`

Account-aware analytics accept an optional owned `account_id`. History and performance endpoints also accept currency filters so callers can keep INR and USD series separate. Performance fields are deliberately labeled `value_growth` and `value_path_metrics`; they describe portfolio-value movement and are not presented as cash-flow-adjusted investment return.

### Bank data

The backend also exposes authenticated, user-owned routes for:

- `/api/bank-accounts`
- `/api/bank-accounts/:id/statements`
- `POST /api/statements/:id/parse`
- `/api/statements/:id`
- `/api/bank-accounts/:id/transactions`
- `/api/transactions/:id`
- `/api/categories`
- `/api/bank-accounts/:id/analytics/*`

Bank-account and statement routes verify active ownership before disclosing or
mutating data. Statement uploads are private, content-hashed, multi-page aware,
retry-safe, and claim-once at both parse and approval boundaries. Full account
numbers, private file paths, statement hashes, and parser leases are never
serialized. Statement periods for one bank account cannot overlap, failed
parses can be retried or discarded, and approval or transaction changes
recalculate the account from its preserved opening balance and all verified
transactions. Deleting a bank account is permanent and removes its statements,
transactions, and every private uploaded PDF in its account directory,
including legacy orphan files. Application startup reconciles the full
statement tree to owner-only permissions and fails closed on symbolic links or
special files.

## Snapshot and Valuation Behavior

- Successful Kite syncs replace only the selected account’s current equity and mutual-fund slice in a new snapshot.
- US and FD refreshes create new snapshots rather than mutating historical rows.
- Other asset classes are copied forward when one asset source is refreshed.
- Reads ignore failed snapshots and use the latest completed snapshot per account.
- Mutual-fund quantities preserve fractional units and separate folios.
- Fixed deposits use decimal, round-half-up simple-interest estimates and stop
  accruing after maturity. Compounding, payout schedules, taxes, and
  bank-specific terms are not modeled.
- US equities remain USD-denominated. If a live quote cannot be fetched during import, the holding remains at cost with a source marker and no false quote date.

## Scheduled Synchronization

With `SCHEDULER_ENABLED=true`, `run.py` starts one APScheduler job at the configured interval. It processes each user’s active accounts and isolates each account in a nested transaction.

Do not start the scheduler in every worker of a multi-process web deployment. Disable it on ordinary workers and run one designated scheduler process.

## Tests and Quality Checks

Run the complete backend suite:

```bash
python -m pytest tests
```

Run a focused file:

```bash
python -m pytest tests/test_portfolio_service.py
```

Optional formatting and lint checks:

```bash
python -m black --check app tests
python -m flake8 app tests
```

## Security Notes

- Never commit `.env`, database files, uploaded statements, credentials, tokens, or JWTs.
- Use HTTPS in production and restrict `CORS_ORIGINS`; wildcard origins are not appropriate for authenticated data.
- Protect the Fernet key separately from the encrypted database. Key loss makes saved brokerage credentials unusable.
- Keep database and upload paths private to the service user.
- Preserve the upload size limit and validate content before parsing.
- Do not add logs that contain account credentials, request tokens, access tokens, JWTs, uploaded document contents, or sensitive absolute paths.
- Rotate an exposed dashboard secret or brokerage credential immediately.
