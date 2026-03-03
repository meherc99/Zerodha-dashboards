# Getting Started with Zerodha Portfolio Dashboard

Welcome! This guide will help you set up and run your Zerodha Portfolio Dashboard.

## Prerequisites

Before you begin, ensure you have:

1. **Python 3.9+** installed
2. **Node.js 18+** installed
3. **Zerodha Kite Connect API** subscription
   - Sign up at https://kite.trade/
   - Cost: ₹2000/month
   - You'll get: `api_key`, `api_secret`, and need to generate `access_token`

## Step-by-Step Setup

### 1. Backend Setup (5 minutes)

```bash
# Navigate to backend directory
cd /Users/mchanglani/Documents/zerodha-dashboard/backend

# Activate virtual environment (already created)
source venv/bin/activate

# The environment is already configured with .env file
# Dependencies are already installed

# Start the backend server
python run.py
```

✅ Backend should now be running on **http://localhost:5000**

You should see:
```
* Running on http://0.0.0.0:5000
Scheduler started. Syncing every 12 hours.
```

### 2. Frontend Setup (2 minutes)

Open a **new terminal window**:

```bash
# Navigate to frontend directory
cd /Users/mchanglani/Documents/zerodha-dashboard/frontend

# Dependencies are already installed
# Start the development server
npm run dev
```

✅ Frontend should now be running on **http://localhost:5173**

You should see:
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

### 3. Add Your First Zerodha Account

1. Open your browser and go to **http://localhost:5173**
2. Click on **"Accounts"** in the navigation
3. Click **"+ Add Account"** button
4. Fill in the form:
   - **Account Name**: e.g., "My Portfolio"
   - **API Key**: Your Kite Connect API key
   - **API Secret**: Your Kite Connect API secret
   - **Access Token**: Your access token (see below for how to get this)

### 4. Getting Your Access Token

Zerodha access tokens expire daily. Here's how to get one:

**Option 1: Using Kite Connect Dashboard**
1. Log into https://kite.trade/
2. Go to "Apps" section
3. Find your app
4. Generate access token

**Option 2: Using the Login Flow (Recommended)**
1. Use the Kite Connect login flow with your API key
2. After login, you'll get a `request_token`
3. Exchange it for an `access_token` using the backend

**Note**: You'll need to refresh your access token daily. We recommend setting up a script to automate this.

### 5. Sync Your Holdings

After adding your account:
1. Go back to **"Dashboard"**
2. Select your account from the dropdown
3. Click **"🔄 Sync"** button
4. Wait for the sync to complete (10-30 seconds)

✅ You should now see your portfolio data!

## What You Should See

### Dashboard
- **Portfolio Summary Cards**: Total value, P&L, day change, holdings count
- **Pie Chart**: Portfolio allocation by stock
- **Bar Chart**: Sector-wise breakdown
- **Line Chart**: Portfolio value over time (will populate after multiple syncs)
- **Performance Heatmap**: Visual representation of winners/losers
- **Holdings Table**: Detailed list with sorting and filtering

### Auto-Sync
- The system will automatically sync all active accounts every 12 hours
- You can manually trigger sync anytime using the "Sync" button
- Each sync creates a snapshot for historical tracking

## Common Issues & Solutions

### Backend won't start

**Problem**: `ModuleNotFoundError: No module named 'flask'`
**Solution**:
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

**Problem**: `ValueError: Encryption key not provided`
**Solution**: Check that `.env` file exists in backend directory with `ENCRYPTION_KEY` set

### Frontend won't start

**Problem**: `Cannot find module 'vue'`
**Solution**:
```bash
cd frontend
npm install
```

### API Connection Error

**Problem**: Frontend shows "Failed to fetch..."
**Solution**:
- Ensure backend is running on port 5000
- Check `.env` file in frontend has correct `VITE_API_BASE_URL`
- Check browser console for CORS errors

### Zerodha API Errors

**Problem**: "Invalid access token"
**Solution**: Access tokens expire daily. Generate a new one and update your account.

**Problem**: "Rate limit exceeded"
**Solution**: Zerodha limits API calls. Wait a few minutes before retrying.

## Adding Family Member Accounts

To track multiple family accounts:

1. Go to **Accounts** page
2. Click **"+ Add Account"** for each family member
3. Each account needs its own Kite Connect API credentials
4. All accounts will be aggregated in the "All Accounts" view
5. You can switch between individual accounts using the dropdown

## Next Steps

### Daily Usage
1. Open http://localhost:5173 in your browser
2. View your dashboard
3. The system auto-syncs every 12 hours
4. You can manually sync anytime

### Weekly Review
- Check performance metrics
- Review top and worst performers
- Analyze sector allocation
- Track portfolio value trends

### Monthly Analysis
- Review historical performance
- Check correlation between stocks
- Rebalance if needed based on sector allocation

## Advanced Configuration

### Change Sync Interval

Edit `backend/.env`:
```env
SYNC_INTERVAL_HOURS=6  # Sync every 6 hours instead of 12
```

Restart backend for changes to take effect.

### Use PostgreSQL Instead of SQLite

For production or better performance:

1. Install PostgreSQL
2. Create a database:
   ```sql
   CREATE DATABASE zerodha_dashboard;
   ```
3. Update `backend/.env`:
   ```env
   DATABASE_URL=postgresql://username:password@localhost:5432/zerodha_dashboard
   ```
4. Restart backend

### Deploy to Production

See `docs/DEPLOYMENT.md` for instructions on deploying to cloud services.

## Getting Help

- Check `README.md` for general information
- See `backend/README.md` for backend-specific docs
- See `frontend/README.md` for frontend-specific docs
- Review API endpoints in backend code
- Check browser console for errors

## Tips for Best Experience

1. **Keep Access Tokens Updated**: Set a daily reminder to refresh tokens
2. **Regular Syncs**: Use manual sync after making trades
3. **Historical Data**: The longer you use the dashboard, the better the trends
4. **Multiple Accounts**: Add all family accounts for consolidated view
5. **Bookmark It**: Add http://localhost:5173 to your bookmarks

---

**🎉 Congratulations!** Your Zerodha Portfolio Dashboard is now running!

Enjoy tracking your investments with beautiful visualizations and comprehensive analytics.
