<template>
  <div class="mutual-funds-tab">
    <!-- MF Summary Cards -->
    <PortfolioSummary :summary="holdingsStore.mfSummary" />

    <!-- Charts Row -->
    <div class="charts-row">
      <div class="chart-card">
        <h3>Mutual Fund Allocation</h3>
        <PieChart v-if="allocationData.labels.length" :data="allocationData" />
        <div v-else class="empty-chart">No mutual fund holdings</div>
      </div>

      <div class="chart-card">
        <h3>Category Breakdown</h3>
        <BarChart v-if="categoryData.labels.length" :data="categoryData" />
        <div v-else class="empty-chart">No category data</div>
      </div>
    </div>

    <!-- MF Holdings Table -->
    <HoldingsTable :holdings="holdingsStore.mfHoldings" />
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
  const holdings = holdingsStore.mfHoldings.slice(0, 10) // Top 10
  return {
    labels: holdings.map(h => h.tradingsymbol),
    values: holdings.map(h => h.current_value)
  }
})

const categoryData = computed(() => {
  // Filter sector/category breakdown to only MF
  const mfCategories = holdingsStore.sectorBreakdown.filter(s => {
    return holdingsStore.mfHoldings.some(h => h.sector === s.sector)
  })
  return {
    labels: mfCategories.map(s => s.sector),
    values: mfCategories.map(s => s.total_value),
    label: 'Category Value'
  }
})
</script>

<style scoped>
.mutual-funds-tab {
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
  .mutual-funds-tab {
    padding: 15px;
  }

  .charts-row {
    grid-template-columns: 1fr;
  }
}
</style>
