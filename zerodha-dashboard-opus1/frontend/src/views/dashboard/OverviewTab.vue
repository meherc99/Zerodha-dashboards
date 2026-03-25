<template>
  <div class="overview-tab">
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
</template>

<script setup>
import { computed } from 'vue'
import { useHoldingsStore } from '@/stores/holdings'

import PortfolioSummary from '@/components/dashboard/PortfolioSummary.vue'
import HoldingsTable from '@/components/dashboard/HoldingsTable.vue'
import PieChart from '@/components/charts/PieChart.vue'
import BarChart from '@/components/charts/BarChart.vue'
import LineChart from '@/components/charts/LineChart.vue'
import HeatMap from '@/components/charts/HeatMap.vue'

const holdingsStore = useHoldingsStore()

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
</script>

<style scoped>
.overview-tab {
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
  .overview-tab {
    padding: 15px;
  }

  .charts-row {
    grid-template-columns: 1fr;
  }
}
</style>
