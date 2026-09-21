/**
 * Pinia store for UI state
 */
import { defineStore } from 'pinia'

export const useUiStore = defineStore('ui', {
  state: () => ({
    sidebarOpen: true,
    theme: 'light',
    notifications: [],
  }),

  actions: {
    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen
    },

    setTheme(theme) {
      this.theme = theme
      document.documentElement.setAttribute('data-theme', theme)
    },

    addNotification(notification) {
      const id = Date.now()
      this.notifications.push({ id, ...notification })

      // Auto-remove after 5 seconds
      setTimeout(() => {
        this.removeNotification(id)
      }, 5000)
    },

    removeNotification(id) {
      this.notifications = this.notifications.filter(n => n.id !== id)
    },
  },
})
