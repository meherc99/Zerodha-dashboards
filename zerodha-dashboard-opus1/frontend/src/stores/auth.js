import { defineStore } from 'pinia'
import api from '@/services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem('token'),
    isAuthenticated: !!localStorage.getItem('token'),
    loading: false,
    error: null
  }),

  actions: {
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
      this.user = data.user
      this.token = data.access_token
      this.isAuthenticated = true
      localStorage.setItem('token', data.access_token)

      // Set default Authorization header
      api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
    },

    async logout() {
      try {
        await api.post('/auth/logout')
      } catch (error) {
        // Logout even if API call fails
      }

      this.user = null
      this.token = null
      this.isAuthenticated = false
      localStorage.removeItem('token')
      delete api.defaults.headers.common['Authorization']
    },

    async fetchCurrentUser() {
      if (!this.token) return

      try {
        const response = await api.get('/auth/me')
        this.user = response.data
      } catch (error) {
        // Token invalid, logout
        this.logout()
      }
    },

    initializeAuth() {
      // Called on app start to restore auth from localStorage
      if (this.token) {
        api.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
        this.fetchCurrentUser()
      }
    },

    clearError() {
      this.error = null
    }
  }
})
