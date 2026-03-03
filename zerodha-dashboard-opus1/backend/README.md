# Zerodha Dashboard - Backend

Flask-based backend API for the Zerodha Portfolio Dashboard.

## Features

- Multi-account Zerodha integration
- Automated 12-hour portfolio syncing
- Secure credential encryption
- RESTful API for holdings, analytics, and portfolio data
- Historical data tracking

## Setup

### 1. Create Virtual Environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Generate Encryption Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Save the output for the next step.

### 4. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and set your values:

```env
SECRET_KEY=your-random-secret-key
DATABASE_URL=sqlite:///zerodha_dashboard.db
ENCRYPTION_KEY=<paste-the-key-from-step-3>
```

### 5. Run the Application

```bash
python run.py
```

The API will be available at http://localhost:5000

## API Endpoints

### Health

- `GET /api/health` - Health check

### Accounts

- `GET /api/accounts` - List all accounts
- `POST /api/accounts` - Create new account
- `GET /api/accounts/:id` - Get specific account
- `PUT /api/accounts/:id` - Update account
- `DELETE /api/accounts/:id` - Deactivate account

### Holdings

- `GET /api/holdings` - Get holdings with optional filters
- `GET /api/holdings/aggregated` - Get aggregated holdings across all accounts
- `POST /api/holdings/sync` - Trigger manual sync

### Analytics

- `GET /api/analytics/portfolio-value-history` - Historical portfolio value
- `GET /api/analytics/sector-breakdown` - Sector allocation
- `GET /api/analytics/performance-metrics` - Performance metrics
- `GET /api/analytics/correlation-matrix` - Stock correlations
- `GET /api/analytics/heatmap` - Performance heatmap

## Adding a Zerodha Account

To add a new family member's Zerodha account:

```bash
curl -X POST http://localhost:5000/api/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "account_name": "Family Member 1",
    "api_key": "your_api_key",
    "api_secret": "your_api_secret",
    "access_token": "your_access_token"
  }'
```

## Automated Syncing

The scheduler automatically syncs all active accounts every 12 hours. You can also trigger a manual sync:

```bash
curl -X POST http://localhost:5000/api/holdings/sync \
  -H "Content-Type: application/json" \
  -d '{"account_id": 1}'
```

## Database

The application uses SQLite by default for easy setup. For production, switch to PostgreSQL by updating `DATABASE_URL` in `.env`:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/zerodha_dashboard
```

## Development

Run tests:

```bash
pytest tests/backend/
```

Format code:

```bash
black app/
flake8 app/
```
