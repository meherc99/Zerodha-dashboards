import { defineStore } from 'pinia'
import api, { resetApiSession } from '@/services/api'
import {
  clearAuthToken,
  getAuthToken,
  setAuthToken
} from '@/utils/authSession'
import { useAccountsStore } from '@/stores/accounts'
import { useBankAccountsStore } from '@/stores/bankAccounts'
import { useCategoriesStore } from '@/stores/categories'
import { useHoldingsStore } from '@/stores/holdings'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: getAuthToken(),
    isAuthenticated: false,
    authReady: false,
    loading: false,
    error: null
  }),

  actions: {
    clearUserData() {
      useAccountsStore().$reset()
      useBankAccountsStore().$reset()
      useCategoriesStore().$reset()
      useHoldingsStore().$reset()
    },

    async register(email, password, fullName) {
      this.loading = true
      this.error = null
      try {
        const response = await api.post('/auth/register', {
          email,
          password,
          full_name: fullName
        })
        this.setAuth(response.data)
      } catch (error) {
        this.error = error.response?.data?.error || 'Registration failed'
        throw error
      } finally {
        this.loading = false
      }
    },

    async login(email, password) {
      this.loading = true
      this.error = null
      try {
        const response = await api.post('/auth/login', { email, password })
        this.setAuth(response.data)
      } catch (error) {
        this.error = error.response?.data?.error || 'Login failed'
        throw error
      } finally {
        this.loading = false
      }
    },

    setAuth(data) {
      resetApiSession()
      this.clearUserData()
      this.user = data.user
      this.token = data.access_token
      this.isAuthenticated = true
      this.authReady = true
      setAuthToken(data.access_token)

      // Set default Authorization header
      api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
    },

    async logout() {
      try {
        await api.post('/auth/logout')
      } catch {
        // Local cleanup is authoritative even when the remote session is unavailable.
      } finally {
        this.clearSession()
      }
    },

    async fetchCurrentUser() {
      if (!this.token) return false

      try {
        const response = await api.get('/auth/me')
        this.user = response.data
        this.isAuthenticated = true
        return true
      } catch {
        this.clearSession()
        return false
      }
    },

    async initializeAuth() {
      this.authReady = false
      this.token = getAuthToken()

      if (!this.token) {
        this.clearSession()
        this.authReady = true
        return false
      }

      api.defaults.headers.common.Authorization = `Bearer ${this.token}`
      try {
        return await this.fetchCurrentUser()
      } finally {
        this.authReady = true
      }
    },

    clearSession() {
      resetApiSession()
      this.clearUserData()
      this.user = null
      this.token = null
      this.isAuthenticated = false
      clearAuthToken()
      delete api.defaults.headers.common.Authorization
    },

    clearError() {
      this.error = null
    }
  }
})
