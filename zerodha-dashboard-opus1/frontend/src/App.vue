<template>
  <div id="app">
    <nav v-if="!isAuthPage" class="navbar">
      <div class="nav-brand">
        <h1>📊 Zerodha Dashboard</h1>
      </div>
      <div class="nav-links">
        <router-link to="/" class="nav-link">Dashboard</router-link>
        <router-link to="/accounts" class="nav-link">Accounts</router-link>
        <button v-if="authStore.isAuthenticated" @click="handleLogout" class="logout-btn">
          Logout
        </button>
      </div>
    </nav>

    <main :class="{ 'main-content': !isAuthPage, 'auth-content': isAuthPage }">
      <router-view />
    </main>

    <!-- Notifications -->
    <div class="notifications">
      <div
        v-for="notification in uiStore.notifications"
        :key="notification.id"
        class="notification"
        :class="notification.type"
      >
        {{ notification.message }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'

const uiStore = useUiStore()
const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const isAuthPage = computed(() => {
  return route.path === '/login' || route.path === '/register'
})

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f3f4f6;
  color: #111827;
}

#app {
  min-height: 100vh;
}

.navbar {
  background: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 0 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 64px;
}

.nav-brand h1 {
  font-size: 20px;
  color: #111827;
}

.nav-links {
  display: flex;
  gap: 20px;
}

.nav-link {
  text-decoration: none;
  color: #6b7280;
  font-weight: 600;
  font-size: 14px;
  padding: 8px 16px;
  border-radius: 6px;
  transition: all 0.2s;
}

.nav-link:hover {
  color: #3b82f6;
  background: #eff6ff;
}

.nav-link.router-link-active {
  color: #3b82f6;
  background: #eff6ff;
}

.logout-btn {
  background: none;
  border: none;
  color: #6b7280;
  font-weight: 600;
  font-size: 14px;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.logout-btn:hover {
  color: #ef4444;
  background: #fef2f2;
}

.main-content {
  min-height: calc(100vh - 64px);
}

.auth-content {
  min-height: 100vh;
}

/* Notifications */
.notifications {
  position: fixed;
  top: 80px;
  right: 20px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.notification {
  padding: 12px 20px;
  border-radius: 6px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  font-size: 14px;
  font-weight: 500;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.notification.success {
  background: #d1fae5;
  color: #065f46;
  border-left: 4px solid #10b981;
}

.notification.error {
  background: #fee2e2;
  color: #991b1b;
  border-left: 4px solid #ef4444;
}

.notification.info {
  background: #dbeafe;
  color: #1e40af;
  border-left: 4px solid #3b82f6;
}

@media (max-width: 768px) {
  .navbar {
    flex-direction: column;
    height: auto;
    padding: 15px 20px;
    gap: 15px;
  }

  .nav-links {
    width: 100%;
    justify-content: center;
  }

  .notifications {
    right: 10px;
    left: 10px;
  }
}
</style>
