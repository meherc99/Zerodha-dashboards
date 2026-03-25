<template>
  <div class="stocks-tab">
    <!-- Equity Summary Cards -->
    <PortfolioSummary :summary="holdingsStore.equitySummary" />

    <!-- Charts Row -->
    <div class="charts-row">
      <div class="chart-card">
        <h3>Equity Allocation</h3>
        <PieChart v-if="allocationData.labels.length" :data="allocationData" />
        <div v-else class="empty-chart">No equity holdings</div>
      </div>

      <div class="chart-card">
        <h3>Sector Breakdown</h3>
        <BarChart v-if="sectorData.labels.length" :data="sectorData" />
        <div v-else class="empty-chart">No sector data</div>
      </div>
    </div>

    <!-- Equity Holdings Table -->
    <HoldingsTable :holdings="holdingsStore.equityHoldings" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useHoldingsStore } from '@/stores/holdings'

import PortfolioSummary from '@/components/dashboard/PortfolioSummary.vue'
import HoldingsTable from '@/components/dashboard/HoldingsTable.vue'
import PieChart from '@/components/charts/PieChart.vue'
import BarChart from '@/components/charts/BarChart.vue'

const holdingsStore = useHoldingsStore()

const allocationData = computed(() => {
  const holdings = holdingsStore.equityHoldings.slice(0, 10) // Top 10
  return {
    labels: holdings.map(h => h.tradingsymbol),
    values: holdings.map(h => h.current_value)
  }
})

const sectorData = computed(() => {
  // Filter sector breakdown to only equity sectors
  const equitySectors = holdingsStore.sectorBreakdown.filter(s => {
    return holdingsStore.equityHoldings.some(h => h.sector === s.sector)
  })
  return {
    labels: equitySectors.map(s => s.sector),
    values: equitySectors.map(s => s.total_value),
    label: 'Sector Value'
  }
})
</script>

<style scoped>
.stocks-tab {
  padding: 20px;
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
  .stocks-tab {
    padding: 15px;
  }

  .charts-row {
    grid-template-columns: 1fr;
  }
}
</style>
