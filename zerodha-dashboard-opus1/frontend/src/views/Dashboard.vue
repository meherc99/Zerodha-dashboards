<template>
  <div class="dashboard-layout">
    <div class="dashboard-header">
      <div>
        <h1>Portfolio Dashboard</h1>
        <p v-if="holdingsStore.lastUpdated" class="last-updated">
          Last updated: {{ formatDate(holdingsStore.lastUpdated) }}
        </p>
      </div>
      <div class="header-actions">
        <AccountSelector
          v-model="selectedAccount"
          :accounts="accountsStore.accounts"
        />
        <button @click="handleSync" :disabled="holdingsStore.loading" class="sync-btn">
          <span v-if="!holdingsStore.loading">🔄 Sync</span>
          <span v-else>Syncing...</span>
        </button>

        <!-- User Menu -->
        <div class="user-menu" @click="toggleUserMenu" ref="userMenuRef">
          <div class="user-avatar">
            {{ userInitials }}
          </div>
          <div v-if="showUserMenu" class="user-dropdown">
            <div class="user-info">
              <p class="user-name">{{ authStore.user?.full_name || 'User' }}</p>
              <p class="user-email">{{ authStore.user?.email }}</p>
            </div>
            <button @click.stop="handleLogout" class="logout-btn">
              🚪 Logout
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="dashboard-body">
      <Sidebar />
      <div class="dashboard-main">
        <LoadingSpinner v-if="holdingsStore.loading && !holdingsStore.summary" message="Loading portfolio data..." />
        <router-view v-else />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useHoldingsStore } from '@/stores/holdings'
import { useAccountsStore } from '@/stores/accounts'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { format } from 'date-fns'

import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import AccountSelector from '@/components/dashboard/AccountSelector.vue'
import Sidebar from '@/components/dashboard/Sidebar.vue'

const router = useRouter()
const holdingsStore = useHoldingsStore()
const accountsStore = useAccountsStore()
const uiStore = useUiStore()
const authStore = useAuthStore()

const selectedAccount = ref(null)
const showUserMenu = ref(false)
const userMenuRef = ref(null)

const userInitials = computed(() => {
  const name = authStore.user?.full_name || authStore.user?.email || 'U'
  return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
})

const formatDate = (date) => {
  return format(new Date(date), 'PPpp')
}

function toggleUserMenu() {
  showUserMenu.value = !showUserMenu.value
}

function handleClickOutside(event) {
  if (userMenuRef.value && !userMenuRef.value.contains(event.target)) {
    showUserMenu.value = false
  }
}

async function handleLogout() {
  showUserMenu.value = false
  await authStore.logout()
  router.push('/login')
}

const handleSync = async () => {
  try {
    await holdingsStore.syncHoldings(selectedAccount.value)
    uiStore.addNotification({
      type: 'success',
      message: 'Holdings synced successfully!'
    })
  } catch (error) {
    uiStore.addNotification({
      type: 'error',
      message: 'Failed to sync holdings'
    })
  }
}

const loadData = async () => {
  if (selectedAccount.value) {
    await holdingsStore.fetchHoldings(selectedAccount.value)
    await holdingsStore.fetchSectorBreakdown(selectedAccount.value)
    await holdingsStore.fetchPortfolioHistory(selectedAccount.value, 30)
  } else {
    await holdingsStore.fetchAggregatedHoldings()
    await holdingsStore.fetchSectorBreakdown()
    await holdingsStore.fetchPortfolioHistory(null, 30)
  }
}

// Watch for account changes
watch(selectedAccount, () => {
  loadData()
})

onMounted(async () => {
  await accountsStore.fetchAccounts()
  await loadData()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.dashboard-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  flex-wrap: wrap;
  gap: 20px;
}

.dashboard-header h1 {
  margin: 0;
  font-size: 32px;
  color: #111827;
}

.last-updated {
  margin-top: 8px;
  font-size: 14px;
  color: #6b7280;
}

.header-actions {
  display: flex;
  gap: 15px;
  align-items: center;
}

.sync-btn {
  padding: 10px 20px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.user-menu {
  position: relative;
  cursor: pointer;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  transition: transform 0.2s;
}

.user-avatar:hover {
  transform: scale(1.05);
}

.user-dropdown {
  position: absolute;
  top: 50px;
  right: 0;
  background: white;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
  min-width: 220px;
  z-index: 1000;
  overflow: hidden;
}

.user-info {
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.user-name {
  margin: 0 0 4px 0;
  font-weight: 600;
  font-size: 14px;
  color: #111827;
}

.user-email {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
  word-break: break-all;
}

.logout-btn {
  width: 100%;
  padding: 12px 16px;
  background: transparent;
  border: none;
  text-align: left;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  cursor: pointer;
  transition: background 0.2s;
}

.logout-btn:hover {
  background: #f9fafb;
  color: #dc2626;
}

.sync-btn:hover:not(:disabled) {
  background: #2563eb;
}

.sync-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.dashboard-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.dashboard-main {
  flex: 1;
  overflow-y: auto;
  background: #f3f4f6;
}

@media (max-width: 768px) {
  .dashboard-header {
    flex-direction: column;
    padding: 15px;
  }

  .header-actions {
    width: 100%;
    flex-direction: column;
  }

  .dashboard-body {
    flex-direction: column;
  }
}
</style>
