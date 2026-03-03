/**
 * API client for communicating with the backend
 */
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor for error handling
apiClient.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default {
  // Health check
  healthCheck() {
    return apiClient.get('/health')
  },

  // Accounts
  getAccounts() {
    return apiClient.get('/accounts')
  },

  getAccount(accountId) {
    return apiClient.get(`/accounts/${accountId}`)
  },

  createAccount(data) {
    return apiClient.post('/accounts', data)
  },

  updateAccount(accountId, data) {
    return apiClient.put(`/accounts/${accountId}`, data)
  },

  deleteAccount(accountId) {
    return apiClient.delete(`/accounts/${accountId}`)
  },

  // Holdings
  getHoldings(params = {}) {
    return apiClient.get('/holdings', { params })
  },

  getAggregatedHoldings() {
    return apiClient.get('/holdings/aggregated')
  },

  syncHoldings(accountId = null) {
    return apiClient.post('/holdings/sync', { account_id: accountId })
  },

  // Analytics
  getPortfolioHistory(params = {}) {
    return apiClient.get('/analytics/portfolio-value-history', { params })
  },

  getSectorBreakdown(params = {}) {
    return apiClient.get('/analytics/sector-breakdown', { params })
  },

  getPerformanceMetrics(params = {}) {
    return apiClient.get('/analytics/performance-metrics', { params })
  },

  getCorrelationMatrix(symbols, period = 90) {
    return apiClient.get('/analytics/correlation-matrix', {
      params: { symbols: symbols.join(','), period }
    })
  },

  getHeatmap(metric = 'pnl_percentage', period = 'week') {
    return apiClient.get('/analytics/heatmap', {
      params: { metric, period }
    })
  },
}
