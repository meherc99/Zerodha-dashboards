import { defineStore } from 'pinia'
import api from '@/services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem('token'),
    isAuthenticated: !!localStorage.getItem('token')
  }),

  actions: {
    async register(email, password, fullName) {
      const response = await api.post('/auth/register', {
        email,
        password,
        full_name: fullName
      })
      this.setAuth(response.data)
    },

    async login(email, password) {
      const response = await api.post('/auth/login', { email, password })
      this.setAuth(response.data)
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
    }
  }
})
