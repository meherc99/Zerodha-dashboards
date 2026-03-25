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
import { ref, onMounted, watch } from 'vue'
import { useHoldingsStore } from '@/stores/holdings'
import { useAccountsStore } from '@/stores/accounts'
import { useUiStore } from '@/stores/ui'
import { format } from 'date-fns'

import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import AccountSelector from '@/components/dashboard/AccountSelector.vue'
import Sidebar from '@/components/dashboard/Sidebar.vue'

const holdingsStore = useHoldingsStore()
const accountsStore = useAccountsStore()
const uiStore = useUiStore()

const selectedAccount = ref(null)

const formatDate = (date) => {
  return format(new Date(date), 'PPpp')
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
