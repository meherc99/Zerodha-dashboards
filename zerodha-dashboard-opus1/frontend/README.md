# Zerodha Dashboard - Frontend

Vue 3 frontend for the Zerodha Portfolio Dashboard.

## Features

- 📊 Interactive charts (Pie, Bar, Line, Heatmap)
- 💼 Multi-account portfolio tracking
- 📈 Real-time P&L calculations
- 🎨 Beautiful, responsive UI
- 🔄 Auto-sync with backend
- 📱 Mobile-friendly design

## Tech Stack

- Vue 3 (Composition API)
- Pinia (State Management)
- Vue Router
- Chart.js + vue-chartjs
- Axios
- Vite

## Setup

### Install Dependencies

```bash
npm install
```

### Development Server

```bash
npm run dev
```

The app will run on http://localhost:5173

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
src/
├── components/
│   ├── charts/          # Chart components
│   │   ├── PieChart.vue
│   │   ├── BarChart.vue
│   │   ├── LineChart.vue
│   │   └── HeatMap.vue
│   ├── common/          # Reusable components
│   │   ├── LoadingSpinner.vue
│   │   └── DataCard.vue
│   └── dashboard/       # Dashboard-specific components
│       ├── AccountSelector.vue
│       ├── PortfolioSummary.vue
│       └── HoldingsTable.vue
├── views/               # Page views
│   ├── Dashboard.vue
│   └── Accounts.vue
├── stores/              # Pinia stores
│   ├── accounts.js
│   ├── holdings.js
│   └── ui.js
├── services/            # API client
│   └── api.js
├── router/              # Vue Router config
│   └── index.js
├── assets/              # Static assets
│   └── styles/
└── App.vue              # Root component
```

## Configuration

Create a `.env` file:

```env
VITE_API_BASE_URL=http://localhost:5000/api
```

## Usage

### Dashboard View

- View portfolio summary (total value, P&L, day change)
- See portfolio allocation pie chart
- Analyze sector breakdown
- Track portfolio value over time
- View performance heatmap
- Browse holdings table with sorting and filtering

### Accounts View

- Add new Zerodha accounts
- Manage existing accounts
- Trigger manual sync
- Activate/deactivate accounts

## Components

### Charts

All charts are built with Chart.js and are fully responsive:

- **PieChart**: Portfolio allocation
- **BarChart**: Sector breakdown
- **LineChart**: Historical value tracking
- **HeatMap**: Performance visualization

### State Management

Pinia stores handle all state:

- **accounts**: Account management
- **holdings**: Portfolio data and analytics
- **ui**: UI state (sidebar, notifications, theme)

### API Integration

The `api.js` service provides methods for all backend endpoints:

- `getAccounts()`, `createAccount()`, etc.
- `getHoldings()`, `syncHoldings()`, etc.
- `getPortfolioHistory()`, `getSectorBreakdown()`, etc.

## Customization

### Adding New Charts

1. Create component in `src/components/charts/`
2. Import in Dashboard view
3. Connect to appropriate store data

### Styling

- Global styles in `src/App.vue`
- Utility classes in `src/assets/styles/main.css`
- Component-specific styles in `<style scoped>` sections

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Tips

- Use the account selector to switch between accounts
- Click "Sync" to manually update holdings
- Holdings table supports sorting and filtering
- Charts are interactive - hover for details
