# Backend

Flask API for the Zerodha Family Portfolio Dashboard. It owns authentication,
account isolation, encrypted brokerage credentials, account-scoped snapshots,
portfolio imports, bank-statement processing, analytics, and scheduled Kite
synchronization.

> Detailed behavior, API reference, snapshot rules, migration history, and fixes
> live in [../../docs/wiki.md](../../docs/wiki.md). This README is the
> at-a-glance backend guide.

## Design in brief

- `create_app()` configures Flask and extensions **without** starting worker
  threads; [run.py](run.py) is the executable entry point and starts the
  scheduler when enabled.
- Flask-JWT-Extended authenticates users; a global lookup rejects deleted or
  inactive users, and logout persists the token id in a revocation list.
- Account-lookup helpers enforce ownership before every read, write, refresh,
  upload, or analytic.
- Each completed snapshot belongs to one Zerodha account; Family data uses the
  latest completed snapshot per owned account, so a failed sync never replaces
  good state.
- INR and USD totals are grouped by currency and never silently combined.

## Setup

Python 3.10+ (3.11+ recommended). Configuration comes from the single
**repository-root** [.env](../../.env) (loaded by `run.py` and Alembic).

```bash
python3 -m venv venv && source venv/bin/activate
python -m pip install -r requirements.txt
```

The environment variable table and secret-generation commands are in
[../../docs/wiki.md §8](../../docs/wiki.md#8-configuration-and-environment).
`FLASK_ENV=production` requires distinct ≥32-byte Flask/JWT secrets, a valid
Fernet `ENCRYPTION_KEY`, explicit non-wildcard CORS, and
`RATELIMIT_STORAGE=database`.

## Run

```bash
python run.py            # http://localhost:5000 (GET /api/health)
```

The factory is safe for pytest and Alembic; only `run.py` starts the scheduler.

## Migrations

```bash
python -m alembic upgrade head        # apply
python -m alembic current             # inspect
python -m alembic revision --autogenerate -m "describe change"
```

Review generated migrations, back up persistent data before production upgrades,
and do not use `db.create_all()` as a substitute. Current head: `855036219916`.
To link pre-auth accounts with `user_id = NULL`, run
`python scripts/migrate_orphaned_accounts.py --dry-run` then without the flag
(details in [../../docs/wiki.md §8](../../docs/wiki.md#8-configuration-and-environment)).

## API groups

All non-public endpoints require `Authorization: Bearer <dashboard-jwt>` and
perform their own ownership checks. Public: `POST /api/auth/register`,
`POST /api/auth/login`, `GET /api/health`.

- **Accounts** — `/api/accounts` CRUD plus `/api/accounts/:id/login-url` for
  server-owned Kite reconnect.
- **Holdings/imports** — `/api/holdings`, `/api/holdings/sync`, and the
  US/FD upload and refresh endpoints (`.xlsx`/`.xls`, all-or-nothing validation,
  replacement semantics).
- **Analytics** — history, sector, performance (`value_growth` /
  `value_path_metrics`), correlation, heatmap.
- **Bank** — accounts, statements (private, hashed, retry-safe, claim-once),
  transactions, categories, and analytics.

The full endpoint list, request formats, and snapshot/valuation rules are in
[../../docs/wiki.md §6](../../docs/wiki.md#6-api-reference).

## Tests

```bash
python -m pytest tests
python -m pytest tests/test_portfolio_service.py     # focused
python -m black --check app tests && python -m flake8 app tests   # optional
```

## Security notes

- Never commit `.env`, database files, uploaded statements, credentials, tokens,
  or JWTs; never log them or sensitive absolute paths.
- Protect the Fernet key separately from the database; key loss makes saved
  brokerage credentials unusable.
- Use HTTPS and restrict `CORS_ORIGINS` in production; rotate any exposed secret
  or brokerage credential immediately.
