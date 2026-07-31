<template>
  <div class="page-stack stocks-page">
    <div class="page-intro">
      <div>
        <p class="eyebrow">Indian equities</p>
        <h2>Stocks at a glance</h2>
        <p>Track position size, sector concentration and unrealised performance in INR.</p>
      </div>
      <span class="status-chip">INR portfolio</span>
    </div>

    <section v-if="!equityHoldings.length" class="state-panel">
      <span class="state-icon" aria-hidden="true">IN</span>
      <h2>No Indian stock holdings</h2>
      <p>This page will populate when a connected Zerodha account returns equity holdings.</p>
      <div class="state-actions">
        <router-link to="/accounts" class="secondary-button">Check accounts</router-link>
      </div>
    </section>

    <template v-else>
      <PortfolioSummary :summary="holdingsStore.equitySummary" currency="INR" />

      <div class="charts-grid">
        <ChartPanel
          title="Stock allocation"
          subtitle="Top positions by current market value"
          :has-data="allocationData.labels.length > 0"
        >
          <PieChart :data="allocationData" />
        </ChartPanel>

        <ChartPanel
          title="Sector exposure"
          subtitle="Current equity value by sector"
          :has-data="sectorData.labels.length > 0"
          empty-title="No sector labels"
          empty-message="Sector exposure will appear when holdings include classification data."
        >
          <BarChart :data="sectorData" horizontal />
        </ChartPanel>
      </div>

      <HoldingsTable
        :holdings="equityHoldings"
        title="Indian stock holdings"
        subtitle="Values shown in INR"
        currency="INR"
        empty-title="No Indian stocks"
      />
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useHoldingsStore } from '@/stores/holdings'

import PortfolioSummary from '@/components/dashboard/PortfolioSummary.vue'
import HoldingsTable from '@/components/dashboard/HoldingsTable.vue'
import ChartPanel from '@/components/dashboard/ChartPanel.vue'
import PieChart from '@/components/charts/PieChart.vue'
import BarChart from '@/components/charts/BarChart.vue'

const holdingsStore = useHoldingsStore()
const equityHoldings = computed(() => holdingsStore.equityHoldings)

const allocationData = computed(() => {
  const holdings = equityHoldings.value
    .slice()
    .sort((left, right) => Number(right.current_value || 0) - Number(left.current_value || 0))
    .slice(0, 8)

  return {
    labels: holdings.map(holding => holding.tradingsymbol),
    values: holdings.map(holding => Number(holding.current_value || 0))
  }
})

const sectorData = computed(() => {
  const sectors = equityHoldings.value.reduce((totals, holding) => {
    const sector = holding.sector || 'Uncategorised'
    totals[sector] = (totals[sector] || 0) + Number(holding.current_value || 0)
    return totals
  }, {})
  const sorted = Object.entries(sectors).sort((left, right) => right[1] - left[1])

  return {
    labels: sorted.map(([sector]) => sector),
    values: sorted.map(([, value]) => value),
    label: 'Current value'
  }
})
</script>

<style scoped>
.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.state-icon {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  border-radius: 13px;
  background: var(--color-primary-soft);
  color: var(--color-primary-dark);
  font-size: 0.74rem;
  font-weight: 850;
}

@media (max-width: 900px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
