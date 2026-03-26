/**
 * Pinia store for transaction categories
 */
import { defineStore } from 'pinia'
import { api } from '@/services/api'

export const useCategoriesStore = defineStore('categories', {
  state: () => ({
    categories: [],
    loading: false,
    error: null,
    lastFetched: null,
  }),

  getters: {
    categoriesMap: (state) => {
      const map = {}
      state.categories.forEach(cat => {
        map[cat.id] = cat
      })
      return map
    },

    categoriesByType: (state) => {
      return state.categories.reduce((acc, cat) => {
        if (!acc[cat.type]) {
          acc[cat.type] = []
        }
        acc[cat.type].push(cat)
        return acc
      }, {})
    },
  },

  actions: {
    async fetchCategories(force = false) {
      // Cache for 5 minutes
      if (!force && this.lastFetched && Date.now() - this.lastFetched < 300000) {
        return
      }

      this.loading = true
      this.error = null
      try {
        const response = await api.getCategories()
        this.categories = response.data
        this.lastFetched = Date.now()
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to fetch categories'
        console.error('Error fetching categories:', error)
      } finally {
        this.loading = false
      }
    },

    getCategoryById(categoryId) {
      return this.categories.find(cat => cat.id === categoryId)
    },

    getCategoryColor(categoryId) {
      const category = this.getCategoryById(categoryId)
      return category?.color || '#6b7280'
    },
  },
})
