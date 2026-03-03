<template>
  <div class="dashboard">
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

    <LoadingSpinner v-if="holdingsStore.loading && !holdingsStore.summary" message="Loading portfolio data..." />

    <div v-else class="dashboard-content">
      <!-- Portfolio Summary Cards -->
      <PortfolioSummary :summary="holdingsStore.summary" />

      <!-- Charts Row 1 -->
      <div class="charts-row">
        <div class="chart-card">
          <h3>Portfolio Allocation</h3>
          <PieChart v-if="allocationData.labels.length" :data="allocationData" />
          <div v-else class="empty-chart">No data available</div>
        </div>

        <div class="chart-card">
          <h3>Sector Breakdown</h3>
          <BarChart v-if="sectorData.labels.length" :data="sectorData" />
          <div v-else class="empty-chart">No data available</div>
        </div>
      </div>

      <!-- Charts Row 2 -->
      <div class="charts-row">
        <div class="chart-card full-width">
          <h3>Portfolio Value Over Time</h3>
          <LineChart v-if="holdingsStore.portfolioHistory.length" :data="holdingsStore.portfolioHistory" />
          <div v-else class="empty-chart">No historical data available</div>
        </div>
      </div>

      <!-- Performance Heatmap -->
      <div v-if="heatmapData.length" class="chart-card">
        <h3>Performance Heatmap</h3>
        <HeatMap :data="heatmapData" />
      </div>

      <!-- Holdings Table -->
      <HoldingsTable :holdings="holdingsStore.holdings" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useHoldingsStore } from '@/stores/holdings'
import { useAccountsStore } from '@/stores/accounts'
import { useUiStore } from '@/stores/ui'
import { format } from 'date-fns'

import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import AccountSelector from '@/components/dashboard/AccountSelector.vue'
import PortfolioSummary from '@/components/dashboard/PortfolioSummary.vue'
import HoldingsTable from '@/components/dashboard/HoldingsTable.vue'
import PieChart from '@/components/charts/PieChart.vue'
import BarChart from '@/components/charts/BarChart.vue'
import LineChart from '@/components/charts/LineChart.vue'
import HeatMap from '@/components/charts/HeatMap.vue'

const holdingsStore = useHoldingsStore()
const accountsStore = useAccountsStore()
const uiStore = useUiStore()

const selectedAccount = ref(null)

// Computed data for charts
const allocationData = computed(() => {
  const holdings = holdingsStore.holdings.slice(0, 10) // Top 10
  return {
    labels: holdings.map(h => h.tradingsymbol),
    values: holdings.map(h => h.current_value)
  }
})

const sectorData = computed(() => {
  return {
    labels: holdingsStore.sectorBreakdown.map(s => s.sector),
    values: holdingsStore.sectorBreakdown.map(s => s.total_value),
    label: 'Sector Value'
  }
})

const heatmapData = computed(() => {
  return holdingsStore.holdings.map(h => ({
    symbol: h.tradingsymbol,
    value: h.pnl_percentage,
    sector: h.sector
  }))
})

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
.dashboard {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 30px;
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

.dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

.chart-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chart-card.full-width {
  grid-column: 1 / -1;
}

.chart-card h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #111827;
}

.empty-chart {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #9ca3af;
  font-size: 14px;
}

@media (max-width: 768px) {
  .dashboard {
    padding: 15px;
  }

  .dashboard-header {
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
    flex-direction: column;
  }

  .charts-row {
    grid-template-columns: 1fr;
  }
}
</style>
