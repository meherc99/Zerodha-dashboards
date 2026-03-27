/**
 * API client for communicating with the backend
 */
import axios from 'axios'
import router from '@/router'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - add token to all requests
apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor - handle 401 errors
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('token')
      router.push('/login')
    }
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// Export axios instance directly for auth store
export default apiClient

// Also export legacy API methods for backward compatibility
export const api = {
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

  // US Holdings
  uploadUSHoldings(file, accountId) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('account_id', accountId)

    return apiClient.post('/holdings/us/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 60000  // Longer timeout for file upload + price fetching
    })
  },

  refreshUSPrices(accountId = null) {
    return apiClient.post('/holdings/us/refresh-prices', {
      account_id: accountId
    })
  },

  // Fixed Deposits
  uploadFDHoldings(file, accountId) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('account_id', accountId)

    return apiClient.post('/holdings/fd/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 30000
    })
  },

  refreshFDValues(accountId = null) {
    return apiClient.post('/holdings/fd/refresh-values', {
      account_id: accountId
    })
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

  // Bank Accounts
  getBankAccounts() {
    return apiClient.get('/bank-accounts')
  },

  getBankAccount(accountId) {
    return apiClient.get(`/bank-accounts/${accountId}`)
  },

  createBankAccount(data) {
    return apiClient.post('/bank-accounts', data)
  },

  updateBankAccount(accountId, data) {
    return apiClient.put(`/bank-accounts/${accountId}`, data)
  },

  deleteBankAccount(accountId) {
    return apiClient.delete(`/bank-accounts/${accountId}`)
  },

  // Bank Statements
  uploadStatement(accountId, file) {
    const formData = new FormData()
    formData.append('file', file)

    return apiClient.post(`/bank-accounts/${accountId}/statements/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 60000  // Longer timeout for file upload + parsing
    })
  },

  getStatement(statementId) {
    return apiClient.get(`/statements/${statementId}`)
  },

  getStatementPreview(statementId) {
    return apiClient.get(`/statements/${statementId}/preview`)
  },

  approveStatement(statementId, transactions) {
    return apiClient.post(`/statements/${statementId}/approve`, { transactions })
  },

  // Categories
  getCategories() {
    return apiClient.get('/categories')
  },

  // Bank Analytics
  getBalanceTrend(accountId, days = 30) {
    return apiClient.get(`/bank-accounts/${accountId}/analytics/balance-trend`, {
      params: { days }
    })
  },

  getCategoryBreakdown(accountId, periodDays = 30) {
    return apiClient.get(`/bank-accounts/${accountId}/analytics/category-breakdown`, {
      params: { period_days: periodDays }
    })
  },

  getCashflow(accountId, periodDays = 30) {
    return apiClient.get(`/bank-accounts/${accountId}/analytics/cashflow`, {
      params: { period_days: periodDays }
    })
  },

  getTopMerchants(accountId, limit = 10) {
    return apiClient.get(`/bank-accounts/${accountId}/analytics/top-merchants`, {
      params: { limit }
    })
  },
}
