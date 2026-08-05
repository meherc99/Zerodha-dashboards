/**
 * API client for communicating with the backend
 */
import axios from 'axios'
import { clearAuthToken, getAuthToken } from '@/utils/authSession'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

let unauthorizedHandler = null
let requestGeneration = 0
const pendingControllers = new Set()

const combineAbortSignals = (signals) => {
  const activeSignals = signals.filter(Boolean)
  if (activeSignals.length === 1) {
    return { signal: activeSignals[0], cleanup: () => {} }
  }

  const controller = new AbortController()
  const abort = () => controller.abort()
  activeSignals.forEach(signal => {
    if (signal.aborted) {
      controller.abort()
    } else {
      signal.addEventListener('abort', abort, { once: true })
    }
  })

  return {
    signal: controller.signal,
    cleanup: () => {
      activeSignals.forEach(signal => signal.removeEventListener('abort', abort))
    }
  }
}

const releaseRequest = config => {
  if (!config) return
  pendingControllers.delete(config.sessionController)
  config.signalCleanup?.()
}

export const setUnauthorizedHandler = handler => {
  unauthorizedHandler = handler
}

export const resetApiSession = () => {
  requestGeneration += 1
  pendingControllers.forEach(controller => controller.abort())
  pendingControllers.clear()
}

// Request interceptor - add token to all requests
apiClient.interceptors.request.use(config => {
  const sessionController = new AbortController()
  const combinedSignal = combineAbortSignals([
    config.signal,
    sessionController.signal
  ])
  config.signal = combinedSignal.signal
  config.sessionGeneration = requestGeneration
  config.sessionController = sessionController
  config.signalCleanup = combinedSignal.cleanup
  pendingControllers.add(sessionController)

  const token = getAuthToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor - handle 401 errors
apiClient.interceptors.response.use(
  response => {
    releaseRequest(response.config)
    if (response.config.sessionGeneration !== requestGeneration) {
      return Promise.reject(new axios.CanceledError('Session changed'))
    }
    return response
  },
  error => {
    releaseRequest(error.config)
    if (
      error.config?.sessionGeneration !== undefined
      && error.config.sessionGeneration !== requestGeneration
    ) {
      return Promise.reject(new axios.CanceledError(
        'Session changed',
        error.config
      ))
    }
    if (error.response?.status === 401) {
      clearAuthToken()
      unauthorizedHandler?.()
    }
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

  // Zerodha auth workflow
  getLoginUrl(data) {
    return apiClient.post('/auth/login-url', data)
  },

  getAccountLoginUrl(accountId) {
    return apiClient.get(`/accounts/${accountId}/login-url`)
  },

  // Holdings
  getHoldings(params = {}, options = {}) {
    return apiClient.get('/holdings', { ...options, params })
  },

  getAggregatedHoldings(options = {}) {
    return apiClient.get('/holdings/aggregated', options)
  },

  syncHoldings(accountId = null, options = {}) {
    return apiClient.post('/holdings/sync', { account_id: accountId }, options)
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

  refreshUSPrices(accountId = null, options = {}) {
    return apiClient.post('/holdings/us/refresh-prices', {
      account_id: accountId
    }, options)
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

  refreshFDValues(accountId = null, options = {}) {
    return apiClient.post('/holdings/fd/refresh-values', {
      account_id: accountId
    }, options)
  },

  // Analytics
  getPortfolioHistory(params = {}, options = {}) {
    return apiClient.get('/analytics/portfolio-value-history', {
      ...options,
      params
    })
  },

  getSectorBreakdown(params = {}, options = {}) {
    return apiClient.get('/analytics/sector-breakdown', { ...options, params })
  },

  getPerformanceMetrics(params = {}, options = {}) {
    return apiClient.get('/analytics/performance-metrics', {
      ...options,
      params
    })
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

  getStatements(accountId) {
    return apiClient.get(`/bank-accounts/${accountId}/statements`)
  },

  parseStatement(statementId) {
    return apiClient.post(`/statements/${statementId}/parse`, null, {
      timeout: 60000
    })
  },

  getStatementPreview(statementId) {
    return apiClient.get(`/statements/${statementId}/preview`)
  },

  approveStatement(statementId, transactions) {
    return apiClient.post(`/statements/${statementId}/approve`, { transactions })
  },

  deleteStatement(statementId) {
    return apiClient.delete(`/statements/${statementId}`)
  },

  // Categories
  getCategories() {
    return apiClient.get('/categories')
  },

  // Bank Analytics
  getBalanceTrend(accountId, days = 30, options = {}) {
    return apiClient.get(`/bank-accounts/${accountId}/analytics/balance-trend`, {
      ...options,
      params: { days }
    })
  },

  getCategoryBreakdown(accountId, periodDays = 30, options = {}) {
    return apiClient.get(`/bank-accounts/${accountId}/analytics/category-breakdown`, {
      ...options,
      params: { period_days: periodDays }
    })
  },

  getCashflow(accountId, periodDays = 30, options = {}) {
    return apiClient.get(`/bank-accounts/${accountId}/analytics/cashflow`, {
      ...options,
      params: { period_days: periodDays }
    })
  },

  getMonthlyIncomeExpenses(accountId, numMonths = 12, options = {}) {
    return apiClient.get(`/bank-accounts/${accountId}/analytics/monthly-cashflow`, {
      ...options,
      params: { num_months: numMonths }
    })
  },

  getTopMerchants(accountId, limit = 10, periodDays = 30, options = {}) {
    return apiClient.get(`/bank-accounts/${accountId}/analytics/top-merchants`, {
      ...options,
      params: { limit, period_days: periodDays }
    })
  },

  // Transactions
  getTransactions(accountId, params = {}, options = {}) {
    return apiClient.get(`/bank-accounts/${accountId}/transactions`, {
      ...options,
      params
    })
  },

  updateTransaction(transactionId, data) {
    return apiClient.put(`/transactions/${transactionId}`, data)
  },

  deleteTransaction(transactionId) {
    return apiClient.delete(`/transactions/${transactionId}`)
  },
}
