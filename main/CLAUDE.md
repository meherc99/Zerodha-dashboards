# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A full-stack web application for tracking and analyzing stock and mutual fund holdings across multiple Zerodha accounts. The system provides real-time portfolio analytics, visualizations, and automated data synchronization.

**Stack:** Flask (Python) backend + Vue 3 frontend + SQLite/PostgreSQL database

## Development Commands

### Backend (Flask API)

```bash
cd backend

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Start development server (runs on http://localhost:5000)
python run.py

# Run tests
pytest tests/backend/

# Code formatting
black app/
flake8 app/
```

### Frontend (Vue 3)

```bash
cd frontend

# Install dependencies (if needed)
npm install

# Start development server (runs on http://localhost:5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Setup

**Backend:** Requires `.env` file in `backend/` directory with:
- `DATABASE_URL` - SQLite or PostgreSQL connection string
- `ENCRYPTION_KEY` - Fernet key for encrypting API credentials
- `SECRET_KEY` - Flask secret key
- `SYNC_INTERVAL_HOURS` - Auto-sync interval (default: 12)
- `CORS_ORIGINS` - Allowed frontend origins

**Frontend:** Requires `.env` file in `frontend/` directory with:
- `VITE_API_BASE_URL` - Backend API URL (default: http://localhost:5000/api)

## Architecture

### Backend Structure

```
backend/app/
├── models/           # SQLAlchemy ORM models
│   ├── account.py    # Account with encrypted credentials
│   ├── holding.py    # Stock/MF holdings
│   ├── snapshot.py   # Portfolio snapshots (for historical tracking)
│   └── historical_price.py  # Price data for analytics
├── services/         # Business logic layer
│   ├── kite_service.py      # Zerodha Kite Connect API integration
│   ├── portfolio_service.py # Portfolio calculations and analytics
│   ├── scheduler_service.py # APScheduler for automated syncs
│   └── analytics_service.py # Advanced analytics (correlations, risk metrics)
├── routes/           # Flask blueprints (API endpoints)
│   ├── accounts.py   # CRUD for Zerodha accounts
│   ├── holdings.py   # Holdings retrieval and sync
│   ├── analytics.py  # Analytics endpoints
│   └── health.py     # Health check
└── utils/
    ├── encryption.py # Fernet encryption for API credentials
    └── validators.py # Input validation
```

**Key patterns:**
- **Service layer:** All business logic lives in `services/`. Routes should only handle HTTP concerns.
- **Encrypted credentials:** Zerodha API keys/secrets are encrypted using Fernet before storage. See `utils/encryption.py`.
- **Snapshots:** Every sync creates a `Snapshot` to track portfolio state over time. This enables historical trend analysis.
- **Scheduler:** APScheduler runs background jobs for automated syncing. Configured in `scheduler_service.py`.

### Frontend Structure

```
frontend/src/
├── views/            # Top-level pages
│   ├── Dashboard.vue # Main portfolio dashboard
│   └── Accounts.vue  # Account management
├── components/
│   ├── dashboard/    # Dashboard-specific components
│   │   ├── PortfolioSummary.vue  # Summary cards (value, P&L, etc.)
│   │   ├── HoldingsTable.vue     # Sortable holdings table
│   │   └── AccountSelector.vue   # Account dropdown
│   ├── charts/       # Chart.js visualizations
│   │   ├── PieChart.vue    # Portfolio allocation
│   │   ├── BarChart.vue    # Sector breakdown
│   │   ├── LineChart.vue   # Value over time
│   │   └── HeatMap.vue     # Performance heatmap
│   └── common/       # Reusable components
│       ├── DataCard.vue
│       └── LoadingSpinner.vue
├── stores/           # Pinia state management
│   ├── accounts.js   # Account data and actions
│   ├── holdings.js   # Holdings, summary, and sync
│   └── ui.js         # UI state (notifications, etc.)
├── services/
│   └── api.js        # Axios-based API client
└── router/
    └── index.js      # Vue Router configuration
```

**Key patterns:**
- **Pinia stores:** All API calls and state management happen in stores, not components.
- **Store actions:** Components call store actions (e.g., `holdingsStore.fetchHoldings()`), which internally use `api.js`.
- **Reactive data:** Components subscribe to store state using `storeToRefs()` for reactivity.

### Database Models

**Key relationships:**
- `Account` (1) → (many) `Holding` - Each account has multiple holdings
- `Snapshot` (1) → (many) `Holding` - Each snapshot captures holdings at a point in time
- Holdings reference `snapshot_id` to track historical state

**Important fields:**
- `Account.access_token_encrypted` - Encrypted Zerodha access token
- `Holding.snapshot_id` - Links holding to specific sync
- `Snapshot.snapshot_date` - Timestamp for historical tracking

## API Integration

### Zerodha Kite Connect

The app uses the official `kiteconnect` Python package. Main operations:
- **Authentication:** Requires `api_key`, `api_secret`, and `access_token` (expires daily)
- **Fetching holdings:** `kite.holdings()` returns list of stocks and mutual funds
- **Data structure:** Returns dict with keys like `tradingsymbol`, `quantity`, `average_price`, `last_price`, `pnl`

**Access token expiry:** Zerodha tokens expire daily. Users must refresh tokens manually via the UI. This is a known limitation.

### API Endpoints

**Accounts:**
- `GET /api/accounts` - List all accounts
- `POST /api/accounts` - Create account (encrypts credentials)
- `PUT /api/accounts/:id` - Update account
- `DELETE /api/accounts/:id` - Deactivate account

**Holdings:**
- `GET /api/holdings` - Get holdings with optional filters (`account_id`, `instrument_type`, `sort_by`)
- `GET /api/holdings/aggregated` - Aggregated view across accounts
- `POST /api/holdings/sync` - Trigger manual sync for account(s)

**Analytics:**
- `GET /api/analytics/portfolio-value-history` - Time series data
- `GET /api/analytics/sector-breakdown` - Sector allocation
- `GET /api/analytics/performance-metrics` - Returns, volatility, Sharpe ratio, etc.
- `GET /api/analytics/correlation-matrix` - Stock correlations
- `GET /api/analytics/heatmap` - Performance heatmap data

## Common Development Tasks

### Adding a new chart/visualization

1. Create Vue component in `frontend/src/components/charts/`
2. Use Chart.js via `vue-chartjs` (see existing charts for patterns)
3. Fetch data from appropriate API endpoint in component's `onMounted()`
4. Add to `Dashboard.vue` in appropriate layout section

### Adding a new API endpoint

1. Add route handler in appropriate blueprint (`backend/app/routes/`)
2. Implement business logic in service layer (`backend/app/services/`)
3. If new data model needed, create in `backend/app/models/`
4. Add corresponding API call in `frontend/src/services/api.js`
5. Update relevant Pinia store to call the new API

### Modifying sync behavior

- **Sync interval:** Change `SYNC_INTERVAL_HOURS` in `.env`
- **Sync logic:** See `SchedulerService` in `backend/app/services/scheduler_service.py`
- **Data fetching:** See `KiteService` in `backend/app/services/kite_service.py`

### Database schema changes

1. Modify model in `backend/app/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Apply migration: `alembic upgrade head`

**Note:** Current setup uses SQLite by default. For production, switch to PostgreSQL by updating `DATABASE_URL`.

## Testing

### Backend Tests

Located in `tests/backend/`. Run with:
```bash
cd backend
pytest tests/backend/
```

Test patterns:
- Use Flask test client for route testing
- Mock Zerodha API calls to avoid external dependencies
- Use in-memory SQLite for test database

### Frontend Tests

(Not currently implemented - would use Vitest + Vue Test Utils)

## Security Considerations

- **Credential encryption:** All Zerodha API credentials are encrypted using Fernet before database storage
- **Environment variables:** Never commit `.env` files - use `.env.example` templates
- **CORS:** Backend restricts origins to configured frontend URL
- **Input validation:** All user inputs validated in routes before processing

## Known Limitations

1. **Access token expiry:** Zerodha tokens expire daily and must be manually refreshed
2. **Rate limits:** Zerodha API has rate limits - sync too frequently may cause errors
3. **SQLite concurrency:** Default SQLite setup may have issues with concurrent writes (use PostgreSQL for production)
4. **Historical data:** Portfolio trends only available after multiple syncs have occurred

## Troubleshooting

**Backend won't start:**
- Check if port 5000 is available
- Verify `ENCRYPTION_KEY` is set in `.env`
- Ensure virtual environment is activated

**Frontend can't connect:**
- Verify backend is running on port 5000
- Check `VITE_API_BASE_URL` in frontend `.env`
- Look for CORS errors in browser console

**Zerodha API errors:**
- "Invalid access token" → Token expired, refresh in UI
- "Rate limit exceeded" → Wait before retrying
- "Instrument not found" → Symbol may be delisted/invalid

**No historical data:**
- Historical charts require multiple snapshots over time
- Trigger a few manual syncs or wait for automated syncs
