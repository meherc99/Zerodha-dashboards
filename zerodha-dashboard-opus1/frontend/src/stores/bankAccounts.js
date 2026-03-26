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
  },
})
