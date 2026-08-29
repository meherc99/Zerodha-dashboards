/**
 * Pinia store for holdings and portfolio data
 */
import { defineStore } from 'pinia'
import { api } from '@/services/api'
import { summarizeHoldings } from '@/utils/holdings'

let portfolioRequestSequence = 0
const portfolioControllers = new WeakMap()

const portfolioScopeKey = accountId => {
  return accountId === null || accountId === undefined || accountId === ''
    ? 'family'
    : `account:${String(accountId)}`
}

const isCanceledRequest = error => {
  return (
    error?.code === 'ERR_CANCELED'
    || error?.name === 'CanceledError'
    || error?.name === 'AbortError'
  )
}

export const useHoldingsStore = defineStore('holdings', {
  state: () => ({
    holdings: [],
    summary: null,
    portfolioHistory: [],
    sectorBreakdown: [],
    performanceMetrics: null,
    exchangeRates: null,
    loading: false,
    error: null,
    analyticsError: null,
    lastUpdated: null,
    portfolioScope: null,
    portfolioRequestId: 0,
  }),

  getters: {
    equityHoldings: (state) =>
      state.holdings.filter(h => h.instrument_type === 'equity'),

    mfHoldings: (state) =>
      state.holdings.filter(h => h.instrument_type === 'mf'),

    usHoldings: (state) =>
      state.holdings.filter(h => h.instrument_type === 'us_equity'),

    euHoldings: (state) =>
      state.holdings.filter(h => h.instrument_type === 'eu_equity'),

    fdHoldings: (state) =>
      state.holdings.filter(h => h.instrument_type === 'fd'),

    equitySummary: (state) =>
      summarizeHoldings(state.holdings.filter(h => h.instrument_type === 'equity')),

    mfSummary: (state) =>
      summarizeHoldings(state.holdings.filter(h => h.instrument_type === 'mf')),

    usSummary: (state) =>
      summarizeHoldings(state.holdings.filter(h => h.instrument_type === 'us_equity')),

    euSummary: (state) =>
      summarizeHoldings(state.holdings.filter(h => h.instrument_type === 'eu_equity')),

    fdSummary: (state) => {
      const fds = state.holdings.filter(h => h.instrument_type === 'fd')
      const summary = summarizeHoldings(fds)
      return {
        current_value: summary.current_value,
        total_investment: summary.total_investment,
        total_pnl: summary.total_pnl,
        total_pnl_percentage: summary.total_pnl_percentage,
        total_holdings: summary.total_holdings,
        day_change: summary.day_change,
        total_interest: summary.total_pnl,
        total_interest_percentage: summary.total_pnl_percentage,
      }
    },

    topPerformers: (state) =>
      [...state.holdings]
        .sort((a, b) => b.pnl_percentage - a.pnl_percentage)
        .slice(0, 5),

    worstPerformers: (state) =>
      [...state.holdings]
        .sort((a, b) => a.pnl_percentage - b.pnl_percentage)
        .slice(0, 5),

    totalValue: (state) => state.summary?.current_value || 0,
    totalPnL: (state) => state.summary?.total_pnl || 0,
    totalPnLPercentage: (state) => state.summary?.total_pnl_percentage || 0,
  },

  actions: {
    beginPortfolioRequest(accountId = null, { clear = false } = {}) {
      portfolioControllers.get(this)?.abort()

      const controller = new AbortController()
      const request = {
        id: ++portfolioRequestSequence,
        scope: portfolioScopeKey(accountId),
        signal: controller.signal,
      }
      portfolioControllers.set(this, controller)
      this.portfolioScope = request.scope
      this.portfolioRequestId = request.id
      this.error = null
      this.analyticsError = null

      if (clear) {
        this.holdings = []
        this.summary = null
        this.portfolioHistory = []
        this.sectorBreakdown = []
        this.performanceMetrics = null
        this.lastUpdated = null
      }

      return request
    },

    isPortfolioRequestCurrent(request) {
      return Boolean(
        request
        && !request.signal.aborted
        && request.id === this.portfolioRequestId
        && request.scope === this.portfolioScope
      )
    },

    currentPortfolioRequest(accountId = null) {
      const controller = portfolioControllers.get(this)
      const scope = portfolioScopeKey(accountId)
      if (
        !controller
        || controller.signal.aborted
        || this.portfolioScope !== scope
        || !this.portfolioRequestId
      ) {
        return this.beginPortfolioRequest(accountId)
      }
      return {
        id: this.portfolioRequestId,
        scope,
        signal: controller.signal,
      }
    },

    clearPortfolioData() {
      portfolioControllers.get(this)?.abort()
      portfolioControllers.delete(this)
      this.portfolioRequestId = ++portfolioRequestSequence
      this.portfolioScope = null
      this.holdings = []
      this.summary = null
      this.portfolioHistory = []
      this.sectorBreakdown = []
      this.performanceMetrics = null
      this.loading = false
      this.error = null
      this.analyticsError = null
      this.lastUpdated = null
    },

    async fetchHoldings(accountId = null, filters = {}, scopeRequest = null) {
      const ownsRequest = !scopeRequest
      const request = (
        scopeRequest || this.beginPortfolioRequest(accountId)
      )
      if (ownsRequest) this.loading = true
      try {
        const params = { ...filters }
        if (accountId) {
          params.account_id = accountId
        }

        const response = await api.getHoldings(params, {
          signal: request.signal
        })
        if (!this.isPortfolioRequestCurrent(request)) return null
        this.holdings = response.data.holdings
        this.summary = response.data.summary
        this.lastUpdated = new Date()
        return response.data
      } catch (error) {
        if (
          !this.isPortfolioRequestCurrent(request)
          || isCanceledRequest(error)
        ) return null
        this.error = error.response?.data?.error || 'Failed to fetch holdings'
        throw error
      } finally {
        if (ownsRequest && this.isPortfolioRequestCurrent(request)) {
          this.loading = false
        }
      }
    },

    async fetchAggregatedHoldings(scopeRequest = null) {
      const ownsRequest = !scopeRequest
      const request = (
        scopeRequest || this.beginPortfolioRequest(null)
      )
      if (ownsRequest) this.loading = true
      try {
        const response = await api.getAggregatedHoldings({
          signal: request.signal
        })
        if (!this.isPortfolioRequestCurrent(request)) return null
        this.holdings = response.data.holdings
        this.summary = response.data
        this.lastUpdated = new Date()
        return response.data
      } catch (error) {
        if (
          !this.isPortfolioRequestCurrent(request)
          || isCanceledRequest(error)
        ) return null
        this.error = error.response?.data?.error || 'Failed to fetch aggregated holdings'
        throw error
      } finally {
        if (ownsRequest && this.isPortfolioRequestCurrent(request)) {
          this.loading = false
        }
      }
    },

    async fetchPortfolioHistory(accountId = null, days = 30, scopeRequest = null) {
      const request = (
        scopeRequest || this.currentPortfolioRequest(accountId)
      )
      try {
        const endDate = new Date()
        const startDate = new Date()
        startDate.setDate(startDate.getDate() - days)

        const response = await api.getPortfolioHistory({
          account_id: accountId,
          start_date: startDate.toISOString(),
          end_date: endDate.toISOString(),
        }, {
          signal: request.signal
        })

        if (!this.isPortfolioRequestCurrent(request)) return null
        this.portfolioHistory = response.data.timeseries
        return response.data.timeseries
      } catch (error) {
        if (
          !this.isPortfolioRequestCurrent(request)
          || isCanceledRequest(error)
        ) return null
        this.portfolioHistory = []
        throw error
      }
    },

    async fetchSectorBreakdown(accountId = null, scopeRequest = null) {
      const request = (
        scopeRequest || this.currentPortfolioRequest(accountId)
      )
      try {
        const response = await api.getSectorBreakdown(
          { account_id: accountId },
          { signal: request.signal }
        )
        if (!this.isPortfolioRequestCurrent(request)) return null
        this.sectorBreakdown = response.data.sectors
        return response.data.sectors
      } catch (error) {
        if (
          !this.isPortfolioRequestCurrent(request)
          || isCanceledRequest(error)
        ) return null
        this.sectorBreakdown = []
        throw error
      }
    },

    async fetchPerformanceMetrics(accountId = null, periodDays = 30, scopeRequest = null) {
      const request = (
        scopeRequest || this.currentPortfolioRequest(accountId)
      )
      try {
        const response = await api.getPerformanceMetrics({
          account_id: accountId,
          period_days: periodDays,
        }, {
          signal: request.signal
        })
        if (!this.isPortfolioRequestCurrent(request)) return null
        this.performanceMetrics = response.data
        return response.data
      } catch (error) {
        if (
          !this.isPortfolioRequestCurrent(request)
          || isCanceledRequest(error)
        ) return null
        this.performanceMetrics = null
        throw error
      }
    },

    async loadPortfolio(accountId = null, days = 30) {
      const request = this.beginPortfolioRequest(accountId, { clear: true })
      this.loading = true

      try {
        const portfolio = accountId
          ? await this.fetchHoldings(accountId, {}, request)
          : await this.fetchAggregatedHoldings(request)
        if (!this.isPortfolioRequestCurrent(request)) {
          return { stale: true }
        }
        if (!portfolio) return { stale: true }

        const analyticsResults = await Promise.allSettled([
          this.fetchSectorBreakdown(accountId, request),
          this.fetchPortfolioHistory(accountId, days, request)
        ])
        if (!this.isPortfolioRequestCurrent(request)) {
          return { stale: true }
        }

        const analyticsFailed = analyticsResults.some(
          result => result.status === 'rejected'
        )
        this.analyticsError = analyticsFailed
          ? 'Portfolio analytics are temporarily unavailable.'
          : null
        return { stale: false, analyticsFailed }
      } catch (error) {
        if (
          !this.isPortfolioRequestCurrent(request)
          || isCanceledRequest(error)
        ) {
          return { stale: true }
        }
        throw error
      } finally {
        if (this.isPortfolioRequestCurrent(request)) {
          this.loading = false
        }
      }
    },

    async syncHoldings(accountId = null) {
      const request = this.beginPortfolioRequest(accountId)
      this.loading = true
      try {
        const response = await api.syncHoldings(accountId, {
          signal: request.signal
        })
        if (!this.isPortfolioRequestCurrent(request)) return null
        const result = response.data

        if (accountId) {
          await this.fetchHoldings(accountId, {}, request)
        } else {
          await this.fetchAggregatedHoldings(request)
        }
        if (!this.isPortfolioRequestCurrent(request)) return null

        if (result.status !== 'completed') {
          const message = result.status === 'partial'
            ? (
                `${result.accounts_failed} of ${result.accounts_total} `
                + 'accounts failed to sync. Showing the latest available data.'
              )
            : 'Portfolio sync failed. Showing the latest available data.'
          const syncError = new Error(message)
          syncError.syncResult = result
          throw syncError
        }
        return result
      } catch (error) {
        if (
          !this.isPortfolioRequestCurrent(request)
          || isCanceledRequest(error)
        ) return null
        this.error = (
          error.syncResult
            ? error.message
            : error.response?.data?.error || 'Failed to sync holdings'
        )
        throw error
      } finally {
        if (this.isPortfolioRequestCurrent(request)) {
          this.loading = false
        }
      }
    },

    async uploadUSHoldings(file, accountId) {
      this.loading = true
      this.error = null
      try {
        const response = await api.uploadUSHoldings(file, accountId)
        return response.data
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to upload file'
        throw error
      } finally {
        this.loading = false
      }
    },

    async refreshUSPrices(accountId = null) {
      const request = this.beginPortfolioRequest(accountId)
      this.loading = true
      try {
        const response = await api.refreshUSPrices(accountId, {
          signal: request.signal
        })
        if (!this.isPortfolioRequestCurrent(request)) return null
        const result = response.data

        if (accountId) {
          await this.fetchHoldings(accountId, {}, request)
        } else {
          await this.fetchAggregatedHoldings(request)
        }
        if (!this.isPortfolioRequestCurrent(request)) return null

        if (
          result.status === 'failed'
          || result.status === 'no_holdings'
          || Number(result.updated_count || 0) === 0
        ) {
          const message = result.status === 'no_holdings'
            ? 'No US holdings were available to refresh.'
            : 'No US prices were updated.'
          const refreshError = new Error(message)
          refreshError.refreshResult = result
          throw refreshError
        }
        return result
      } catch (error) {
        if (
          !this.isPortfolioRequestCurrent(request)
          || isCanceledRequest(error)
        ) return null
        this.error = (
          error.refreshResult
            ? error.message
            : error.response?.data?.error || 'Failed to refresh prices'
        )
        throw error
      } finally {
        if (this.isPortfolioRequestCurrent(request)) {
          this.loading = false
        }
      }
    },

    async uploadEUHoldings(file, accountId) {
      this.loading = true
      this.error = null
      try {
        const response = await api.uploadEUHoldings(file, accountId)
        return response.data
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to upload file'
        throw error
      } finally {
        this.loading = false
      }
    },

    async refreshEUPrices(accountId = null) {
      const request = this.beginPortfolioRequest(accountId)
      this.loading = true
      try {
        const response = await api.refreshEUPrices(accountId, {
          signal: request.signal
        })
        if (!this.isPortfolioRequestCurrent(request)) return null
        const result = response.data

        if (accountId) {
          await this.fetchHoldings(accountId, {}, request)
        } else {
          await this.fetchAggregatedHoldings(request)
        }
        if (!this.isPortfolioRequestCurrent(request)) return null

        if (
          result.status === 'failed'
          || result.status === 'no_holdings'
          || Number(result.updated_count || 0) === 0
        ) {
          const message = result.status === 'no_holdings'
            ? 'No EU holdings were available to refresh.'
            : 'No EU prices were updated.'
          const refreshError = new Error(message)
          refreshError.refreshResult = result
          throw refreshError
        }
        return result
      } catch (error) {
        if (
          !this.isPortfolioRequestCurrent(request)
          || isCanceledRequest(error)
        ) return null
        this.error = (
          error.refreshResult
            ? error.message
            : error.response?.data?.error || 'Failed to refresh prices'
        )
        throw error
      } finally {
        if (this.isPortfolioRequestCurrent(request)) {
          this.loading = false
        }
      }
    },

    async uploadFDHoldings(file, accountId) {
      this.loading = true
      this.error = null
      try {
        const response = await api.uploadFDHoldings(file, accountId)
        return response.data
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to upload file'
        throw error
      } finally {
        this.loading = false
      }
    },

    async refreshFDValues(accountId = null) {
      const request = this.beginPortfolioRequest(accountId)
      this.loading = true
      try {
        const response = await api.refreshFDValues(accountId, {
          signal: request.signal
        })
        if (!this.isPortfolioRequestCurrent(request)) return null
        if (accountId) {
          await this.fetchHoldings(accountId, {}, request)
        } else {
          await this.fetchAggregatedHoldings(request)
        }
        if (!this.isPortfolioRequestCurrent(request)) return null
        return response.data
      } catch (error) {
        if (
          !this.isPortfolioRequestCurrent(request)
          || isCanceledRequest(error)
        ) return null
        this.error = error.response?.data?.error || 'Failed to refresh FD values'
        throw error
      } finally {
        if (this.isPortfolioRequestCurrent(request)) {
          this.loading = false
        }
      }
    },

    async fetchExchangeRates() {
      try {
        const response = await api.getExchangeRates()
        this.exchangeRates = response.data
        return response.data
      } catch (error) {
        // Non-fatal — UI falls back to placeholder rates
        this.exchangeRates = null
        return null
      }
    },

    sortHoldings(sortBy = 'pnl_percentage', order = 'desc') {
      this.holdings.sort((a, b) => {
        const aVal = a[sortBy] || 0
        const bVal = b[sortBy] || 0
        return order === 'desc' ? bVal - aVal : aVal - bVal
      })
    },
  },
})
