/**
 * Pinia store for bank accounts
 */
import { defineStore } from 'pinia'
import { api } from '@/services/api'

let bankDataRequestSequence = 0
const analyticsControllers = new WeakMap()
const transactionControllers = new WeakMap()

const isCanceledRequest = error => {
  return (
    error?.code === 'ERR_CANCELED'
    || error?.name === 'CanceledError'
    || error?.name === 'AbortError'
  )
}

export const useBankAccountsStore = defineStore('bankAccounts', {
  state: () => ({
    bankAccounts: [],
    selectedBank: null,
    loading: false,
    error: null,
    // Upload/review modal state
    uploadModal: {
      isOpen: false,
      bankAccountId: null,
      statementId: null,
      status: null, // 'uploading', 'parsing', 'review', 'failed'
      progress: 0,
      error: null,
    },
    reviewModal: {
      isOpen: false,
      statementId: null,
      bankAccountId: null,
      transactions: [],
      warnings: [],
      currency: 'INR',
      loading: false,
      error: null,
    },
    statements: {
      accountId: null,
      items: [],
      loading: false,
      error: null,
    },
    // Analytics state
    analytics: {
      balanceTrend: [],
      categoryBreakdown: [],
      cashflow: [],
      topMerchants: [],
      debitTransactionCount: 0,
      accountId: null,
      requestId: 0,
      loading: false,
      error: null,
    },
    // Transactions state
    transactions: {
      items: [],
      accountId: null,
      requestId: 0,
      loading: false,
      error: null,
    },
  }),

  getters: {
    balancesByCurrency: (state) => state.bankAccounts.reduce(
      (totals, account) => {
        if (!account.is_active) return totals
        const currency = String(account.currency || 'INR').toUpperCase()
        totals[currency] = (
          totals[currency] || 0
        ) + Number(account.current_balance || 0)
        return totals
      },
      {}
    ),

    activeBankAccounts: (state) => {
      return state.bankAccounts.filter(account => account.is_active)
    },
  },

  actions: {
    async fetchBankAccounts() {
      this.loading = true
      this.error = null
      try {
        const selectedId = this.selectedBank?.id
        const response = await api.getBankAccounts()
        this.bankAccounts = response.data
        this.selectedBank = selectedId === undefined || selectedId === null
          ? null
          : this.bankAccounts.find(
              account => Number(account.id) === Number(selectedId)
            ) || null
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to fetch bank accounts'
      } finally {
        this.loading = false
      }
    },

    async createBankAccount(data) {
      this.loading = true
      this.error = null
      try {
        const response = await api.createBankAccount(data)
        this.bankAccounts.push(response.data)
        return response.data
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to create bank account'
        throw error
      } finally {
        this.loading = false
      }
    },

    async updateBankAccount(accountId, data) {
      this.loading = true
      this.error = null
      try {
        const response = await api.updateBankAccount(accountId, data)
        const index = this.bankAccounts.findIndex(acc => acc.id === accountId)
        if (index !== -1) {
          this.bankAccounts[index] = response.data
        }
        return response.data
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to update bank account'
        throw error
      } finally {
        this.loading = false
      }
    },

    async deleteBankAccount(accountId) {
      this.loading = true
      this.error = null
      try {
        await api.deleteBankAccount(accountId)
        this.bankAccounts = this.bankAccounts.filter(
          account => Number(account.id) !== Number(accountId)
        )
        if (Number(this.selectedBank?.id) === Number(accountId)) {
          this.selectedBank = null
        }
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to delete bank account'
        throw error
      } finally {
        this.loading = false
      }
    },

    selectBank(bank) {
      this.selectedBank = bank
    },

    // Upload modal actions
    openUploadModal(bankAccountId) {
      this.uploadModal.isOpen = true
      this.uploadModal.bankAccountId = bankAccountId
      this.uploadModal.statementId = null
      this.uploadModal.status = null
      this.uploadModal.progress = 0
      this.uploadModal.error = null
    },

    resetUploadAttempt() {
      this.uploadModal.statementId = null
      this.uploadModal.status = null
      this.uploadModal.progress = 0
      this.uploadModal.error = null
    },

    closeUploadModal() {
      this.uploadModal.isOpen = false
      this.uploadModal.bankAccountId = null
      this.uploadModal.statementId = null
      this.uploadModal.status = null
      this.uploadModal.progress = 0
      this.uploadModal.error = null
    },

    async uploadStatement(bankAccountId, file) {
      this.uploadModal.status = 'uploading'
      this.uploadModal.progress = 30
      this.uploadModal.error = null

      try {
        const response = await api.uploadStatement(bankAccountId, file)
        this.uploadModal.statementId = response.data.statement_id
        this.uploadModal.status = 'parsing'
        this.uploadModal.progress = 60

        await api.parseStatement(response.data.statement_id)
        this.uploadModal.status = 'review'
        this.uploadModal.progress = 100
        const bankAccount = this.bankAccounts.find(
          account => Number(account.id) === Number(bankAccountId)
        )
        await this.openReviewModal(
          response.data.statement_id,
          bankAccount?.currency || 'INR',
          bankAccountId
        )
        await this.fetchStatements(bankAccountId)
        this.closeUploadModal()
      } catch (error) {
        this.uploadModal.status = 'failed'
        this.uploadModal.error = error.response?.data?.error || 'Failed to upload statement'
        throw error
      }
    },

    async retryStatementParse(
      statementId = this.uploadModal.statementId,
      bankAccountId = this.uploadModal.bankAccountId
    ) {
      if (!statementId || !bankAccountId) {
        throw new Error('No uploaded statement is available to retry.')
      }

      this.uploadModal.isOpen = true
      this.uploadModal.bankAccountId = bankAccountId
      this.uploadModal.statementId = statementId
      this.uploadModal.status = 'parsing'
      this.uploadModal.progress = 60
      this.uploadModal.error = null

      try {
        await api.parseStatement(statementId)
        this.uploadModal.status = 'review'
        this.uploadModal.progress = 100
        const bankAccount = this.bankAccounts.find(
          account => Number(account.id) === Number(bankAccountId)
        )
        await this.openReviewModal(
          statementId,
          bankAccount?.currency || 'INR',
          bankAccountId
        )
        await this.fetchStatements(bankAccountId)
        this.closeUploadModal()
      } catch (error) {
        this.uploadModal.status = 'failed'
        this.uploadModal.error = (
          error.response?.data?.error || 'Failed to parse statement'
        )
        throw error
      }
    },

    async discardStatement(
      statementId = this.uploadModal.statementId,
      bankAccountId = this.uploadModal.bankAccountId
    ) {
      if (!statementId) return
      await api.deleteStatement(statementId)
      this.statements.items = this.statements.items.filter(
        statement => Number(statement.id) !== Number(statementId)
      )
      if (this.uploadModal.statementId === statementId) {
        this.closeUploadModal()
      }
      if (bankAccountId) {
        await this.fetchStatements(bankAccountId)
      }
    },

    async fetchStatements(bankAccountId) {
      if (Number(this.statements.accountId) !== Number(bankAccountId)) {
        this.statements.items = []
      }
      this.statements.accountId = bankAccountId
      this.statements.loading = true
      this.statements.error = null
      try {
        const response = await api.getStatements(bankAccountId)
        if (Number(this.statements.accountId) === Number(bankAccountId)) {
          this.statements.items = response.data
        }
        return response.data
      } catch (error) {
        if (Number(this.statements.accountId) === Number(bankAccountId)) {
          this.statements.error = (
            error.response?.data?.error || 'Failed to load statements'
          )
        }
        throw error
      } finally {
        if (Number(this.statements.accountId) === Number(bankAccountId)) {
          this.statements.loading = false
        }
      }
    },

    // Review modal actions
    async openReviewModal(statementId, currency = null, bankAccountId = null) {
      this.reviewModal.isOpen = true
      this.reviewModal.statementId = statementId
      this.reviewModal.bankAccountId = (
        bankAccountId
        || this.selectedBank?.id
        || this.uploadModal.bankAccountId
        || null
      )
      this.reviewModal.currency = (
        currency
        || this.selectedBank?.currency
        || 'INR'
      )
      this.reviewModal.loading = true
      this.reviewModal.error = null

      try {
        const response = await api.getStatementPreview(statementId)
        this.reviewModal.transactions = response.data.transactions
        this.reviewModal.warnings = response.data.validation_warnings || []
      } catch (error) {
        this.reviewModal.error = error.response?.data?.error || 'Failed to load statement preview'
      } finally {
        this.reviewModal.loading = false
      }
    },

    closeReviewModal() {
      this.reviewModal.isOpen = false
      this.reviewModal.statementId = null
      this.reviewModal.bankAccountId = null
      this.reviewModal.transactions = []
      this.reviewModal.warnings = []
      this.reviewModal.currency = 'INR'
      this.reviewModal.loading = false
      this.reviewModal.error = null
    },

    async approveStatement(statementId, transactions) {
      this.reviewModal.loading = true
      this.reviewModal.error = null
      const bankAccountId = this.reviewModal.bankAccountId

      try {
        await api.approveStatement(statementId, transactions)
        // Refresh bank accounts to update balances
        await this.fetchBankAccounts()
        if (bankAccountId) {
          await this.fetchStatements(bankAccountId)
        }
        this.closeReviewModal()
      } catch (error) {
        this.reviewModal.error = error.response?.data?.error || 'Failed to approve statement'
        throw error
      } finally {
        this.reviewModal.loading = false
      }
    },

    updateReviewTransaction(index, field, value) {
      if (this.reviewModal.transactions[index]) {
        this.reviewModal.transactions[index][field] = value
      }
    },

    // Analytics actions
    async fetchAllAnalytics(accountId, days = 30) {
      analyticsControllers.get(this)?.abort()
      const controller = new AbortController()
      const requestId = ++bankDataRequestSequence
      analyticsControllers.set(this, controller)
      this.analytics.accountId = accountId
      this.analytics.requestId = requestId
      this.analytics.loading = true
      this.analytics.error = null
      const isCurrent = () => (
        !controller.signal.aborted
        && this.analytics.requestId === requestId
        && Number(this.analytics.accountId) === Number(accountId)
      )

      try {
        const options = { signal: controller.signal }
        const [balance, categories, cashflow, merchants] = await Promise.all([
          api.getBalanceTrend(accountId, days, options),
          api.getCategoryBreakdown(accountId, days, options),
          api.getCashflow(accountId, days, options),
          api.getTopMerchants(accountId, 10, days, options),
        ])
        if (!isCurrent()) return null

        this.analytics.balanceTrend = (balance.data.dates || []).map(
          (date, index) => ({
            date,
            balance: Number(balance.data.balances?.[index] || 0)
          })
        )
        this.analytics.categoryBreakdown = (
          categories.data.categories || []
        ).map(category => ({
          ...category,
          category: category.name,
          count: category.transaction_count
        }))
        this.analytics.debitTransactionCount = Number(
          categories.data.transaction_count || 0
        )
        this.analytics.cashflow = (cashflow.data.periods || []).map(
          (period, index) => ({
            period,
            total_credit: Number(cashflow.data.credits?.[index] || 0),
            total_debit: Number(cashflow.data.debits?.[index] || 0),
            net: Number(cashflow.data.net?.[index] || 0)
          })
        )
        this.analytics.topMerchants = (
          merchants.data.merchants || []
        ).map(merchant => ({
          ...merchant,
          total_spent: merchant.total,
          transaction_count: merchant.count
        }))
        return this.analytics
      } catch (error) {
        if (!isCurrent() || isCanceledRequest(error)) return null
        this.analytics.balanceTrend = []
        this.analytics.categoryBreakdown = []
        this.analytics.cashflow = []
        this.analytics.topMerchants = []
        this.analytics.debitTransactionCount = 0
        this.analytics.error = (
          error.response?.data?.error || 'Failed to fetch bank analytics'
        )
        throw error
      } finally {
        if (isCurrent()) {
          this.analytics.loading = false
        }
      }
    },

    // Transaction actions
    async fetchTransactions(accountId, params = {}) {
      transactionControllers.get(this)?.abort()
      const controller = new AbortController()
      const requestId = ++bankDataRequestSequence
      transactionControllers.set(this, controller)
      this.transactions.accountId = accountId
      this.transactions.requestId = requestId
      this.transactions.loading = true
      this.transactions.error = null
      const isCurrent = () => (
        !controller.signal.aborted
        && this.transactions.requestId === requestId
        && Number(this.transactions.accountId) === Number(accountId)
      )

      try {
        const response = await api.getTransactions(accountId, params, {
          signal: controller.signal
        })
        if (!isCurrent()) return null
        this.transactions.items = response.data.transactions || []
        return response.data
      } catch (error) {
        if (!isCurrent() || isCanceledRequest(error)) return null
        this.transactions.error = error.response?.data?.error || 'Failed to fetch transactions'
        throw error
      } finally {
        if (isCurrent()) {
          this.transactions.loading = false
        }
      }
    },

    async updateTransaction(transactionId, data) {
      try {
        const response = await api.updateTransaction(transactionId, data)
        return response.data
      } catch (error) {
        throw error
      }
    },

    async deleteTransaction(transactionId) {
      try {
        await api.deleteTransaction(transactionId)
        await this.fetchBankAccounts()
      } catch (error) {
        throw error
      }
    },
  },
})
