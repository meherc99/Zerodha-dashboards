/**
 * Pinia store for holdings and portfolio data
 */
import { defineStore } from 'pinia'
import api from '@/services/api'

export const useHoldingsStore = defineStore('holdings', {
  state: () => ({
    holdings: [],
    summary: null,
    portfolioHistory: [],
    sectorBreakdown: [],
    performanceMetrics: null,
    loading: false,
    error: null,
    lastUpdated: null,
  }),

  getters: {
    equityHoldings: (state) =>
      state.holdings.filter(h => h.instrument_type === 'equity'),

    mfHoldings: (state) =>
      state.holdings.filter(h => h.instrument_type === 'mf'),

    usHoldings: (state) =>
      state.holdings.filter(h => h.instrument_type === 'us_equity'),

    fdHoldings: (state) =>
      state.holdings.filter(h => h.instrument_type === 'fd'),

    equitySummary: (state) => {
      const equity = state.holdings.filter(h => h.instrument_type === 'equity')
      if (equity.length === 0) {
        return {
          current_value: 0,
          total_pnl: 0,
          total_pnl_percentage: 0,
          day_change: 0,
          total_holdings: 0,
          total_investment: 0
        }
      }

      const totalInvestment = equity.reduce((sum, h) =>
        sum + (h.average_price * h.quantity), 0)
      const currentValue = equity.reduce((sum, h) =>
        sum + h.current_value, 0)
      const totalPnl = equity.reduce((sum, h) =>
        sum + h.pnl, 0)
      const dayChange = equity.reduce((sum, h) =>
        sum + (h.day_change || 0), 0)

      return {
        current_value: currentValue,
        total_pnl: totalPnl,
        total_pnl_percentage: totalInvestment > 0
          ? (totalPnl / totalInvestment) * 100
          : 0,
        day_change: dayChange,
        total_holdings: equity.length,
        total_investment: totalInvestment
      }
    },

    mfSummary: (state) => {
      const mf = state.holdings.filter(h => h.instrument_type === 'mf')
      if (mf.length === 0) {
        return {
          current_value: 0,
          total_pnl: 0,
          total_pnl_percentage: 0,
          day_change: 0,
          total_holdings: 0,
          total_investment: 0
        }
      }

      const totalInvestment = mf.reduce((sum, h) =>
        sum + (h.average_price * h.quantity), 0)
      const currentValue = mf.reduce((sum, h) =>
        sum + h.current_value, 0)
      const totalPnl = mf.reduce((sum, h) =>
        sum + h.pnl, 0)
      const dayChange = mf.reduce((sum, h) =>
        sum + (h.day_change || 0), 0)

      return {
        current_value: currentValue,
        total_pnl: totalPnl,
        total_pnl_percentage: totalInvestment > 0
          ? (totalPnl / totalInvestment) * 100
          : 0,
        day_change: dayChange,
        total_holdings: mf.length,
        total_investment: totalInvestment
      }
    },

    usSummary: (state) => {
      const us = state.holdings.filter(h => h.instrument_type === 'us_equity')
      if (us.length === 0) {
        return {
          current_value: 0,
          total_pnl: 0,
          total_pnl_percentage: 0,
          day_change: 0,
          total_holdings: 0,
          total_investment: 0
        }
      }

      const totalInvestment = us.reduce((sum, h) =>
        sum + (h.average_price * h.quantity), 0)
      const currentValue = us.reduce((sum, h) =>
        sum + h.current_value, 0)
      const totalPnl = us.reduce((sum, h) =>
        sum + h.pnl, 0)
      const dayChange = us.reduce((sum, h) =>
        sum + (h.day_change || 0), 0)

      return {
        current_value: currentValue,
        total_pnl: totalPnl,
        total_pnl_percentage: totalInvestment > 0
          ? (totalPnl / totalInvestment) * 100
          : 0,
        day_change: dayChange,
        total_holdings: us.length,
        total_investment: totalInvestment
      }
    },

    fdSummary: (state) => {
      const fds = state.holdings.filter(h => h.instrument_type === 'fd')
      if (fds.length === 0) {
        return {
          current_value: 0,
          total_interest: 0,
          total_interest_percentage: 0,
          total_holdings: 0,
          total_investment: 0
        }
      }

      const totalInvestment = fds.reduce((sum, h) =>
        sum + h.average_price, 0)
      const currentValue = fds.reduce((sum, h) =>
        sum + h.current_value, 0)
      const totalInterest = fds.reduce((sum, h) =>
        sum + h.pnl, 0)

      return {
        current_value: currentValue,
        total_interest: totalInterest,
        total_interest_percentage: totalInvestment > 0
          ? (totalInterest / totalInvestment) * 100
          : 0,
        total_holdings: fds.length,
        total_investment: totalInvestment
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
    async fetchHoldings(accountId = null, filters = {}) {
      this.loading = true
      this.error = null
      try {
        const params = { ...filters }
        if (accountId) {
          params.account_id = accountId
        }

        const response = await api.getHoldings(params)
        this.holdings = response.data.holdings
        this.summary = response.data.summary
        this.lastUpdated = new Date()
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to fetch holdings'
        console.error('Error fetching holdings:', error)
      } finally {
        this.loading = false
      }
    },

    async fetchAggregatedHoldings() {
      this.loading = true
      this.error = null
      try {
        const response = await api.getAggregatedHoldings()
        this.holdings = response.data.holdings
        this.summary = response.data
        this.lastUpdated = new Date()
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to fetch aggregated holdings'
        console.error('Error fetching aggregated holdings:', error)
      } finally {
        this.loading = false
      }
    },

    async fetchPortfolioHistory(accountId = null, days = 30) {
      try {
        const endDate = new Date()
        const startDate = new Date()
        startDate.setDate(startDate.getDate() - days)

        const response = await api.getPortfolioHistory({
          account_id: accountId,
          start_date: startDate.toISOString(),
          end_date: endDate.toISOString(),
        })

        this.portfolioHistory = response.data.timeseries
      } catch (error) {
        console.error('Error fetching portfolio history:', error)
      }
    },

    async fetchSectorBreakdown(accountId = null) {
      try {
        const response = await api.getSectorBreakdown({ account_id: accountId })
        this.sectorBreakdown = response.data.sectors
      } catch (error) {
        console.error('Error fetching sector breakdown:', error)
      }
    },

    async fetchPerformanceMetrics(accountId = null, periodDays = 30) {
      try {
        const response = await api.getPerformanceMetrics({
          account_id: accountId,
          period_days: periodDays,
        })
        this.performanceMetrics = response.data
      } catch (error) {
        console.error('Error fetching performance metrics:', error)
      }
    },

    async syncHoldings(accountId = null) {
      this.loading = true
      this.error = null
      try {
        await api.syncHoldings(accountId)
        // Refresh holdings after sync
        if (accountId) {
          await this.fetchHoldings(accountId)
        } else {
          await this.fetchAggregatedHoldings()
        }
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to sync holdings'
        throw error
      } finally {
        this.loading = false
      }
    },

    async uploadUSHoldings(file, accountId) {
      this.loading = true
      this.error = null
      try {
        const response = await api.uploadUSHoldings(file, accountId)
        // Refresh holdings after upload
        await this.fetchHoldings(accountId)
        return response.data
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to upload file'
        throw error
      } finally {
        this.loading = false
      }
    },

    async refreshUSPrices(accountId = null) {
      this.loading = true
      this.error = null
      try {
        await api.refreshUSPrices(accountId)
        // Refresh holdings after price update
        if (accountId) {
          await this.fetchHoldings(accountId)
        } else {
          await this.fetchAggregatedHoldings()
        }
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to refresh prices'
        throw error
      } finally {
        this.loading = false
      }
    },

    async uploadFDHoldings(file, accountId) {
      this.loading = true
      this.error = null
      try {
        const response = await api.uploadFDHoldings(file, accountId)
        // Refresh holdings after upload
        await this.fetchHoldings(accountId)
        return response.data
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to upload file'
        throw error
      } finally {
        this.loading = false
      }
    },

    async refreshFDValues(accountId = null) {
      this.loading = true
      this.error = null
      try {
        await api.refreshFDValues(accountId)
        // Refresh holdings after value update
        if (accountId) {
          await this.fetchHoldings(accountId)
        } else {
          await this.fetchAggregatedHoldings()
        }
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to refresh FD values'
        throw error
      } finally {
        this.loading = false
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
