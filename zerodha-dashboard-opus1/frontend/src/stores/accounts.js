/**
 * Pinia store for account management
 */
import { defineStore } from 'pinia'
import api from '@/services/api'

export const useAccountsStore = defineStore('accounts', {
  state: () => ({
    accounts: [],
    currentAccount: null,
    loading: false,
    error: null,
  }),

  getters: {
    activeAccounts: (state) => state.accounts.filter(a => a.is_active),
    accountCount: (state) => state.accounts.length,
    hasAccounts: (state) => state.accounts.length > 0,
  },

  actions: {
    async fetchAccounts() {
      this.loading = true
      this.error = null
      try {
        const response = await api.getAccounts()
        this.accounts = response.data.accounts
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to fetch accounts'
        console.error('Error fetching accounts:', error)
      } finally {
        this.loading = false
      }
    },

    async createAccount(accountData) {
      this.loading = true
      this.error = null
      try {
        const response = await api.createAccount(accountData)
        this.accounts.push(response.data)
        return response.data
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to create account'
        throw error
      } finally {
        this.loading = false
      }
    },

    async updateAccount(accountId, accountData) {
      this.loading = true
      this.error = null
      try {
        const response = await api.updateAccount(accountId, accountData)
        const index = this.accounts.findIndex(a => a.id === accountId)
        if (index !== -1) {
          this.accounts[index] = response.data
        }
        return response.data
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to update account'
        throw error
      } finally {
        this.loading = false
      }
    },

    async deleteAccount(accountId) {
      this.loading = true
      this.error = null
      try {
        await api.deleteAccount(accountId)
        this.accounts = this.accounts.filter(a => a.id !== accountId)
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to delete account'
        throw error
      } finally {
        this.loading = false
      }
    },

    setCurrentAccount(accountId) {
      this.currentAccount = accountId
    },
  },
})
