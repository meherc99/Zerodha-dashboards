# Zerodha Portfolio Dashboard

A comprehensive web-based dashboard for analyzing and managing stock and mutual fund holdings across multiple Zerodha accounts.

## Features

✨ **Multi-Account Support** - Track multiple family member accounts in one place
📊 **Beautiful Visualizations** - Pie charts, bar charts, time-series graphs, and heatmaps
🔄 **Automated Sync** - Background updates every 12 hours
📈 **Advanced Analytics** - P&L tracking, sector allocation, correlation analysis, risk metrics
🔒 **Secure** - Encrypted credential storage using Fernet encryption
📱 **Responsive** - Works on desktop and mobile devices

## Architecture

**Backend:** Flask + SQLAlchemy + APScheduler
**Frontend:** Vue 3 + Pinia + Chart.js
**Database:** PostgreSQL/SQLite
**API:** Zerodha Kite Connect

## Project Structure

```
zerodha-dashboard/
├── backend/              # Flask API server
│   ├── app/
│   │   ├── models/      # Database models
│   │   ├── services/    # Business logic
│   │   ├── routes/      # API endpoints
│   │   └── utils/       # Utilities
│   ├── requirements.txt
│   └── run.py
├── frontend/            # Vue.js application
│   ├── src/
│   │   ├── components/  # Vue components
│   │   ├── views/       # Page views
│   │   ├── stores/      # Pinia stores
│   │   └── services/    # API client
│   └── package.json
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Zerodha Kite Connect API subscription ([Get it here](https://kite.trade/))

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configuration is already done in .env file
# Start the server
python run.py
```

The API will run on http://localhost:5000

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will run on http://localhost:5173

### 3. Add Your Zerodha Account

Option 1: Using API:
```bash
curl -X POST http://localhost:5000/api/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "account_name": "My Account",
    "api_key": "your_kite_api_key",
    "api_secret": "your_kite_api_secret",
    "access_token": "your_access_token"
  }'
```

Option 2: Use the frontend UI (recommended)

## Configuration

### Backend (.env)

```env
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///zerodha_dashboard.db
ENCRYPTION_KEY=your-fernet-key
SYNC_INTERVAL_HOURS=12
CORS_ORIGINS=http://localhost:5173
```

### Frontend (.env)

```env
VITE_API_BASE_URL=http://localhost:5000/api
```

## Features in Detail

### 1. Portfolio Overview
- Total portfolio value and P&L
- Day change tracking
- Holdings count
- Investment vs current value

### 2. Visualizations
- **Pie Chart**: Portfolio allocation by stock
- **Bar Chart**: Sector-wise breakdown
- **Line Chart**: Portfolio value over time
- **Heatmap**: Performance tracking
- **Correlation Matrix**: Stock correlations

### 3. Holdings Management
- Sortable and filterable holdings table
- Equity and mutual fund separation
- Purchase date tracking
- Real-time P&L calculations

### 4. Analytics
- Return metrics (total, annualized, daily)
- Risk metrics (volatility, Sharpe ratio, max drawdown)
- Top and worst performers
- Sector analysis

### 5. Multi-Account
- Aggregated family portfolio view
- Individual account views
- Per-account performance tracking

## API Endpoints

### Accounts
- `GET /api/accounts` - List accounts
- `POST /api/accounts` - Create account
- `PUT /api/accounts/:id` - Update account
- `DELETE /api/accounts/:id` - Delete account

### Holdings
- `GET /api/holdings` - Get holdings
- `GET /api/holdings/aggregated` - Aggregated view
- `POST /api/holdings/sync` - Manual sync

### Analytics
- `GET /api/analytics/portfolio-value-history`
- `GET /api/analytics/sector-breakdown`
- `GET /api/analytics/performance-metrics`
- `GET /api/analytics/correlation-matrix`
- `GET /api/analytics/heatmap`

## Security

- **Credential Encryption**: All API keys encrypted using Fernet
- **Environment Variables**: Sensitive data in .env files
- **CORS**: Restricted to specific origins
- **Input Validation**: All user inputs validated

## Development

### Backend Testing
```bash
cd backend
pytest tests/backend/
```

### Code Formatting
```bash
black app/
flake8 app/
```

### Frontend Testing
```bash
cd frontend
npm run test
```

## Deployment

### Option 1: Local Deployment
- Already configured for local use
- SQLite database (no setup needed)
- Access via localhost

### Option 2: Cloud Deployment
- **Backend**: Deploy to Heroku/DigitalOcean/AWS
- **Frontend**: Deploy to Vercel/Netlify
- **Database**: PostgreSQL (managed service recommended)

See `docs/DEPLOYMENT.md` for detailed instructions.

## Troubleshooting

### Backend won't start
- Check if port 5000 is available
- Verify ENCRYPTION_KEY is set in .env
- Check database file permissions

### Frontend can't connect to API
- Verify backend is running on port 5000
- Check CORS_ORIGINS in backend .env
- Check VITE_API_BASE_URL in frontend .env

### Zerodha API errors
- Verify API credentials are correct
- Check if access token is valid (expires daily)
- Ensure Kite Connect subscription is active

## Roadmap

- [ ] Real-time price updates via WebSocket
- [ ] Tax reporting and capital gains
- [ ] Portfolio rebalancing suggestions
- [ ] Mobile app (React Native)
- [ ] Email/SMS notifications
- [ ] Comparison with market indices
- [ ] Goal tracking
- [ ] Order placement

## License

MIT License - feel free to use for personal projects

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review API documentation in `docs/API.md`
3. Check Zerodha Kite Connect documentation

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Built with ❤️ for Indian stock market investors**
