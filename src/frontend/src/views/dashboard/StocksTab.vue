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
          title="Holdings distribution (Top 15)"
          subtitle="Largest positions by current market value"
          :has-data="allocationData.labels.length > 0"
        >
          <BarChart :data="allocationData" horizontal />
        </ChartPanel>

        <ChartPanel
          title="Sector allocation"
          subtitle="Current equity value by sector"
          :has-data="sectorData.labels.length > 0"
          empty-title="No sector labels"
          empty-message="Sector exposure will appear when holdings include classification data."
        >
          <PieChart :data="sectorData" />
        </ChartPanel>
      </div>

      <HoldingsTable
        :holdings="equityHoldings"
        title="Indian stock holdings"
        subtitle="Values shown in INR"
        currency="INR"
        empty-title="No Indian stocks"
        :show-day-change="true"
        :show-member="true"
      />

      <ChartPanel
        title="Return map"
        subtitle="Position-level unrealised return; colour and size both communicate direction"
        :has-data="heatmapData.length > 0"
        empty-title="No return data"
      >
        <HeatMap :data="heatmapData" />
      </ChartPanel>
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
import HeatMap from '@/components/charts/HeatMap.vue'

const holdingsStore = useHoldingsStore()
const equityHoldings = computed(() => holdingsStore.equityHoldings)

const allocationData = computed(() => {
  const OPUS_COLORS = [
    '#6366f1', '#8b5cf6', '#ec4899', '#ef4444', '#f97316',
    '#f59e0b', '#10b981', '#06b6d4', '#3b82f6', '#14b8a6',
    '#a855f7', '#e879f9', '#fb7185', '#fbbf24', '#34d399',
  ]
  const holdings = equityHoldings.value
    .slice()
    .sort((left, right) => Number(right.current_value || 0) - Number(left.current_value || 0))
    .slice(0, 15)

  return {
    labels: holdings.map(holding => holding.tradingsymbol),
    values: holdings.map(holding => Number(holding.current_value || 0)),
    colors: holdings.map((_, i) => OPUS_COLORS[i % OPUS_COLORS.length]),
  }
})

const heatmapData = computed(() =>
  equityHoldings.value.map(h => ({
    symbol: h.tradingsymbol,
    value: Number(h.pnl_percentage || 0),
    sector: h.sector,
  }))
)

const SECTOR_COLORS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#ef4444', '#f97316',
  '#f59e0b', '#10b981', '#06b6d4', '#3b82f6', '#14b8a6',
  '#a855f7', '#e879f9', '#fb7185', '#fbbf24', '#34d399',
  '#22d3ee', '#60a5fa', '#c084fc',
]

// Normalize sector names from Zerodha/NSE to display-friendly categories
const normalizeSector = sector => {
  if (!sector) return 'Other'
  const s = sector.trim()
  const map = {
    'Financial Services': 'Financial Services',
    'Banks': 'Financial Services',
    'Insurance': 'Financial Services',
    'Capital Markets': 'Financial Services',
    'Diversified Financials': 'Financial Services',
    'Information Technology': 'Technology',
    'IT': 'Technology',
    'Software': 'Technology',
    'Internet': 'Technology',
    'Consumer Discretionary': 'Consumer',
    'Consumer Goods': 'Consumer',
    'Consumer Staples': 'Consumer',
    'FMCG': 'Consumer',
    'Retailing': 'Consumer',
    'Automobile': 'Automobiles',
    'Automobiles': 'Automobiles',
    'Auto Components': 'Automobiles',
    'Healthcare': 'Healthcare',
    'Pharma': 'Healthcare',
    'Pharmaceuticals': 'Healthcare',
    'Biotechnology': 'Healthcare',
    'Energy': 'Energy',
    'Oil & Gas': 'Energy',
    'Petroleum': 'Energy',
    'Power': 'Energy',
    'Metals': 'Metals & Mining',
    'Metals & Mining': 'Metals & Mining',
    'Steel': 'Metals & Mining',
    'Mining': 'Metals & Mining',
    'Infrastructure': 'Infrastructure',
    'Construction': 'Infrastructure',
    'Real Estate': 'Real Estate',
    'Realty': 'Real Estate',
    'Telecom': 'Telecom',
    'Communication': 'Telecom',
    'Media': 'Media & Entertainment',
    'Entertainment': 'Media & Entertainment',
    'Chemicals': 'Chemicals',
    'Materials': 'Chemicals',
    'Fertilisers': 'Chemicals',
    'Agriculture': 'Agriculture',
    'Agro Chemicals': 'Chemicals',
    'Textiles': 'Textiles',
    'Utilities': 'Utilities',
    'Transport': 'Transport',
    'Logistics': 'Transport',
  }
  return map[s] || s
}

const sectorData = computed(() => {
  const sectors = equityHoldings.value.reduce((totals, holding) => {
    const sector = normalizeSector(holding.sector)
    totals[sector] = (totals[sector] || 0) + Number(holding.current_value || 0)
    return totals
  }, {})
  const sorted = Object.entries(sectors).sort((left, right) => right[1] - left[1])

  return {
    labels: sorted.map(([sector]) => sector),
    values: sorted.map(([, value]) => value),
    colors: sorted.map((_, i) => SECTOR_COLORS[i % SECTOR_COLORS.length]),
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
