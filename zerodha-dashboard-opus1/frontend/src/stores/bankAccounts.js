/**
 * Pinia store for bank accounts
 */
import { defineStore } from 'pinia'
import { api } from '@/services/api'

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
      transactions: [],
      warnings: [],
      loading: false,
      error: null,
    },
  }),

  getters: {
    totalBalance: (state) => {
      return state.bankAccounts.reduce((sum, account) => sum + account.balance, 0)
    },

    activeBankAccounts: (state) => {
      return state.bankAccounts.filter(account => account.is_active)
    },
  },

  actions: {
    async fetchBankAccounts() {
      this.loading = true
      this.error = null
      try {
        const response = await api.getBankAccounts()
        this.bankAccounts = response.data
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to fetch bank accounts'
        console.error('Error fetching bank accounts:', error)
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
        this.bankAccounts = this.bankAccounts.filter(acc => acc.id !== accountId)
        if (this.selectedBank?.id === accountId) {
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

        // Start polling for status
        await this.pollStatementStatus(response.data.statement_id)
      } catch (error) {
        this.uploadModal.status = 'failed'
        this.uploadModal.error = error.response?.data?.error || 'Failed to upload statement'
        console.error('Error uploading statement:', error)
        throw error
      }
    },

    async pollStatementStatus(statementId) {
      const maxAttempts = 60 // Poll for up to 2 minutes
      let attempts = 0

      const poll = async () => {
        try {
          const response = await api.getStatement(statementId)
          const { status, error } = response.data

          if (status === 'review') {
            this.uploadModal.status = 'review'
            this.uploadModal.progress = 100
            // Open review modal
            await this.openReviewModal(statementId)
            this.closeUploadModal()
            return
          } else if (status === 'failed') {
            this.uploadModal.status = 'failed'
            this.uploadModal.error = error || 'Statement parsing failed'
            return
          } else if (status === 'parsing' || status === 'uploaded') {
            // Continue polling
            attempts++
            if (attempts < maxAttempts) {
              setTimeout(poll, 2000) // Poll every 2 seconds
            } else {
              this.uploadModal.status = 'failed'
              this.uploadModal.error = 'Statement parsing timed out'
            }
          }
        } catch (error) {
          console.error('Error polling statement status:', error)
          this.uploadModal.status = 'failed'
          this.uploadModal.error = 'Failed to check statement status'
        }
      }

      await poll()
    },

    // Review modal actions
    async openReviewModal(statementId) {
      this.reviewModal.isOpen = true
      this.reviewModal.statementId = statementId
      this.reviewModal.loading = true
      this.reviewModal.error = null

      try {
        const response = await api.getStatementPreview(statementId)
        this.reviewModal.transactions = response.data.transactions
        this.reviewModal.warnings = response.data.warnings || []
      } catch (error) {
        this.reviewModal.error = error.response?.data?.error || 'Failed to load statement preview'
        console.error('Error loading statement preview:', error)
      } finally {
        this.reviewModal.loading = false
      }
    },

    closeReviewModal() {
      this.reviewModal.isOpen = false
      this.reviewModal.statementId = null
      this.reviewModal.transactions = []
      this.reviewModal.warnings = []
      this.reviewModal.loading = false
      this.reviewModal.error = null
    },

    async approveStatement(statementId, transactions) {
      this.reviewModal.loading = true
      this.reviewModal.error = null

      try {
        await api.approveStatement(statementId, transactions)
        // Refresh bank accounts to update balances
        await this.fetchBankAccounts()
        this.closeReviewModal()
      } catch (error) {
        this.reviewModal.error = error.response?.data?.error || 'Failed to approve statement'
        console.error('Error approving statement:', error)
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
  },
})
