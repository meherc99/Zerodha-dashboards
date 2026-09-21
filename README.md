# Zerodha Family Portfolio Dashboard

A self-hosted Flask + Vue application for reviewing a family's Indian equities,
mutual funds, fixed deposits, US equities, and bank activity without mixing
account ownership or currencies.

> **New here?** Start with [GETTING_STARTED.md](GETTING_STARTED.md).
> **Full history, features, API, schema, and fixes:** [docs/wiki.md](docs/wiki.md).
> Backend and frontend specifics: [src/backend/README.md](src/backend/README.md)
> and [src/frontend/README.md](src/frontend/README.md).

## At a glance

- JWT auth protects the app and API; logout revokes the token server-side.
- Every account, snapshot, holding, import, and analytic query is scoped to its
  owning user; **Family** shows the combined view, **Member** one account.
- Each account has immutable portfolio snapshots; a failed sync never replaces
  another account's good data.
- Dedicated Overview, Indian Stocks, Mutual Funds, US Stocks, Fixed Deposits, and
  Bank Balances pages with responsive charts, tables, search, filter, and sort.
- INR and USD are summarized separately and never silently added or converted.
- Kite credentials, access tokens, and bank account numbers are encrypted at
  rest and never returned to the frontend.

## Technology

- **Backend:** Flask, Flask-SQLAlchemy, Flask-JWT-Extended, APScheduler, Alembic,
  Kite Connect, pandas
- **Frontend:** Vue 3, Pinia, Vue Router, Chart.js, Axios, Vite
- **Database:** SQLite for local development; PostgreSQL via `DATABASE_URL`
- **Tests:** pytest (backend), Vitest (frontend)

## Layout

```text
.
├── .env                    # Single consolidated environment file (root)
├── docker-compose.yml
├── docs/wiki.md            # Full project wiki and changelog
└── src/
    ├── backend/            # Flask API (see src/backend/README.md)
    └── frontend/           # Vue client (see src/frontend/README.md)
```

## Quick start

Prerequisites: Python 3.10+ (3.11+ recommended), Node.js 20.19+ or 22.12+, an
optional Kite Connect app for live sync, and an optional Finnhub key for US
quotes.

Configure the single root `.env` (see the variable table in
[docs/wiki.md §8](docs/wiki.md#8-configuration-and-environment)) and generate
secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"   # SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"   # JWT_SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # ENCRYPTION_KEY
```

Backend:

```bash
cd src/backend
python3 -m venv venv && source venv/bin/activate
python -m pip install -r requirements.txt
python -m alembic upgrade head
python run.py                     # http://localhost:5000
```

Frontend (another terminal):

```bash
cd src/frontend
npm install
npm run dev                       # http://localhost:5173
```

Open `http://localhost:5173`, register a dashboard user, add an account, and
sync. The Kite login/reconnect flow and per-page usage are documented in
[docs/wiki.md §4](docs/wiki.md#4-feature-reference).

## Verification

```bash
cd src/backend && source venv/bin/activate && python -m pytest tests
cd ../frontend && npm test && npm run build
```

## Security essentials

- Never commit the root `.env`, credentials, tokens, JWTs, uploaded statements,
  or database files.
- Use independent high-entropy `SECRET_KEY` and `JWT_SECRET_KEY` in production;
  keep `ENCRYPTION_KEY` stable (losing it makes stored credentials unreadable).
- In production set `FLASK_ENV=production`, use HTTPS, restrict `CORS_ORIGINS`
  (no `*`), set `RATELIMIT_STORAGE=database`, run as an unprivileged user, and
  run exactly one scheduler process.

See [docs/wiki.md §8](docs/wiki.md#8-configuration-and-environment) and
[§9](docs/wiki.md#9-behavior-contracts) for the full configuration and behavior
contracts.

## Docker deployment

Docker Compose runs PostgreSQL, the Flask API, and the Vue/nginx frontend as
one local stack. The application is exposed on port `8080` by default.

```bash
cp .env.example .env
# Edit .env and replace all required secret values.
docker compose build
docker compose up -d
docker compose ps
```

The backend container applies pending Alembic migrations before Gunicorn starts.
If a migration fails, the API does not start; inspect it with
`docker compose logs backend`.

Open `http://localhost:8080` or `http://SERVER_LAN_IP:8080` from another
device on the same network. The database, backend instance data, and uploaded
bank statements are stored in named Docker volumes. Back up those volumes
before changing the host or removing the stack.

```bash
docker compose logs -f backend
docker compose down                    # stop without deleting data
docker compose down -v                 # destructive: deletes all volumes
```

For remote personal access, keep the port private and use Tailscale or place
the stack behind an HTTPS reverse proxy. Do not expose PostgreSQL directly.
