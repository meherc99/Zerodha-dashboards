<template>
  <div class="page-stack overview-page">
    <div class="page-intro">
      <div>
        <p class="eyebrow">Portfolio overview</p>
        <h2>One clear view of your wealth</h2>
        <p>Domestic and foreign assets are kept in their source currencies so totals stay financially meaningful.</p>
      </div>
      <div class="currency-legend" aria-label="Currency treatment">
        <span><i class="inr-dot"></i> Domestic assets · INR</span>
        <span v-if="usHoldings.length"><i class="usd-dot"></i> US equities · USD</span>
      </div>
    </div>

    <section v-if="!allHoldings.length" class="state-panel">
      <span class="empty-portfolio-icon" aria-hidden="true">＋</span>
      <h2>Your portfolio is ready for its first sync</h2>
      <p>Connect a family account, then sync it to see holdings, allocation, performance and history.</p>
      <div class="state-actions">
        <router-link to="/accounts" class="primary-button">Manage accounts</router-link>
      </div>
    </section>

    <template v-else>
      <section v-if="domesticHoldings.length" aria-labelledby="domestic-summary-title">
        <div class="section-heading summary-heading">
          <div>
            <h2 id="domestic-summary-title">Domestic portfolio</h2>
            <p>Indian equities, mutual funds and deposits · INR</p>
          </div>
        </div>
        <PortfolioSummary :summary="domesticSummary" currency="INR" />
      </section>

      <section v-if="domesticHoldings.length" class="insight-strip" aria-label="Portfolio highlights">
        <article>
          <span>Largest position</span>
          <strong>{{ largestHolding?.tradingsymbol || '—' }}</strong>
          <small>{{ largestAllocation.toFixed(1) }}% of domestic value</small>
        </article>
        <article>
          <span>Best performer</span>
          <strong>{{ bestPerformer?.tradingsymbol || '—' }}</strong>
          <small :class="pnlClass(bestPerformer?.pnl_percentage)">
            {{ formatPercentage(bestPerformer?.pnl_percentage) }}
          </small>
        </article>
        <article>
          <span>Asset mix</span>
          <strong>{{ domesticAssetTypes }}</strong>
          <small>{{ domesticHoldings.length }} total positions</small>
        </article>
      </section>

      <div v-if="domesticHoldings.length" class="charts-grid">
        <ChartPanel
          title="Largest positions"
          subtitle="Top domestic holdings by current value"
          :has-data="allocationData.labels.length > 0"
          empty-message="Holdings allocation will appear after a successful sync."
        >
          <PieChart :data="allocationData" />
        </ChartPanel>

        <ChartPanel
          title="Domestic allocation"
          subtitle="Equities by sector; other holdings by asset class"
          :has-data="sectorData.labels.length > 0"
          empty-title="No allocation data"
          empty-message="Allocation labels are not available for these holdings."
        >
          <BarChart :data="sectorData" horizontal />
        </ChartPanel>

        <ChartPanel
          v-for="series in historySeries"
          :key="series.currency"
          class="wide-chart"
          :title="`Portfolio value · ${series.currency}`"
          subtitle="30-day history; currencies remain independent"
          :has-data="series.points.length > 0"
          empty-title="No history yet"
          empty-message="Historical values will appear after portfolio snapshots have been collected."
        >
          <LineChart :data="series.points" :currency="series.currency" />
        </ChartPanel>

        <ChartPanel
          v-if="historySeries.length === 0"
          class="wide-chart"
          title="Portfolio value"
          subtitle="30-day history"
          :has-data="false"
          empty-title="No history yet"
          empty-message="Historical values will appear after portfolio snapshots have been collected."
        />
      </div>

      <ChartPanel
        v-if="domesticHoldings.length"
        title="Return map"
        subtitle="Position-level unrealised return; colour and labels both communicate direction"
        :has-data="heatmapData.length > 0"
        empty-title="No return data"
      >
        <HeatMap :data="heatmapData" />
      </ChartPanel>

      <HoldingsTable
        v-if="domesticHoldings.length"
        :holdings="domesticHoldings"
        title="Domestic holdings"
        subtitle="Values shown in INR"
        currency="INR"
        :show-member="true"
      />

      <section v-if="usHoldings.length" class="foreign-section" aria-labelledby="foreign-summary-title">
        <div class="section-heading">
          <div>
            <h2 id="foreign-summary-title">US equities</h2>
            <p>Kept separate from domestic totals · USD</p>
          </div>
          <router-link to="/dashboard/us-stocks" class="secondary-button">Open US portfolio</router-link>
        </div>
        <PortfolioSummary :summary="usSummary" currency="USD" />
        <HoldingsTable
          :holdings="usHoldings"
          title="US holdings"
          subtitle="Values shown in USD"
          currency="USD"
          empty-title="No US holdings"
        />
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useHoldingsStore } from '@/stores/holdings'
import { summarizeHoldings } from '@/utils/holdings'

import PortfolioSummary from '@/components/dashboard/PortfolioSummary.vue'
import HoldingsTable from '@/components/dashboard/HoldingsTable.vue'
import ChartPanel from '@/components/dashboard/ChartPanel.vue'
import PieChart from '@/components/charts/PieChart.vue'
import BarChart from '@/components/charts/BarChart.vue'
import LineChart from '@/components/charts/LineChart.vue'
import HeatMap from '@/components/charts/HeatMap.vue'

const holdingsStore = useHoldingsStore()

const allHoldings = computed(() => holdingsStore.holdings)
const domesticHoldings = computed(() => allHoldings.value.filter(holding => holding.instrument_type !== 'us_equity'))
const usHoldings = computed(() => allHoldings.value.filter(holding => holding.instrument_type === 'us_equity'))
const domesticSummary = computed(() => summarizeHoldings(domesticHoldings.value))
const usSummary = computed(() => summarizeHoldings(usHoldings.value))
const historySeries = computed(() => {
  const grouped = holdingsStore.portfolioHistory.reduce((series, point) => {
    const currency = String(point.currency || 'INR').toUpperCase()
    if (!series[currency]) series[currency] = []
    series[currency].push(point)
    return series
  }, {})

  return Object.entries(grouped)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([currency, points]) => ({ currency, points }))
})

const sortedDomestic = computed(() => {
  return domesticHoldings.value
    .slice()
    .sort((left, right) => Number(right.current_value || 0) - Number(left.current_value || 0))
})

const largestHolding = computed(() => sortedDomestic.value[0])
const bestPerformer = computed(() => {
  return domesticHoldings.value
    .slice()
    .sort((left, right) => Number(right.pnl_percentage || 0) - Number(left.pnl_percentage || 0))[0]
})

const largestAllocation = computed(() => {
  const total = domesticSummary.value.current_value
  return total > 0 ? (Number(largestHolding.value?.current_value || 0) / total) * 100 : 0
})

const domesticAssetTypes = computed(() => {
  return new Set(domesticHoldings.value.map(holding => holding.instrument_type)).size
})

const allocationData = computed(() => {
  const holdings = sortedDomestic.value.slice(0, 8)
  return {
    labels: holdings.map(holding => holding.tradingsymbol),
    values: holdings.map(holding => Number(holding.current_value || 0))
  }
})

const sectorData = computed(() => {
  const categories = domesticHoldings.value.reduce((totals, holding) => {
    const category = holding.instrument_type === 'mf'
      ? 'Mutual funds'
      : holding.instrument_type === 'fd'
        ? 'Fixed deposits'
        : holding.sector || 'Other equities'
    totals[category] = (totals[category] || 0) + Number(holding.current_value || 0)
    return totals
  }, {})
  const sorted = Object.entries(categories).sort((left, right) => right[1] - left[1])

  return {
    labels: sorted.map(([label]) => label),
    values: sorted.map(([, value]) => value),
    label: 'Current value'
  }
})

const heatmapData = computed(() => {
  return domesticHoldings.value.map(holding => ({
    symbol: holding.tradingsymbol,
    value: Number(holding.pnl_percentage || 0),
    sector: holding.sector
  }))
})

const pnlClass = value => {
  const number = Number(value || 0)
  return number > 0 ? 'positive' : number < 0 ? 'negative' : 'neutral'
}
const formatPercentage = value => {
  const number = Number(value || 0)
  return `${number > 0 ? '+' : number < 0 ? '−' : ''}${Math.abs(number).toFixed(2)}% return`
}
</script>

<style scoped>
.summary-heading {
  margin-bottom: 12px;
}

.currency-legend {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px 14px;
  padding: 10px 13px;
  border: 1px solid var(--color-border);
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--color-text-soft);
  font-size: 0.72rem;
  font-weight: 700;
}

.currency-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.currency-legend i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.inr-dot { background: var(--color-primary); }
.usd-dot { background: var(--color-positive); }

.empty-portfolio-icon {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 14px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 1.5rem;
}

.insight-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, #172943, #0f1e32);
  box-shadow: var(--shadow-sm);
}

.insight-strip article {
  display: flex;
  min-width: 0;
  flex-direction: column;
  padding: 17px 20px;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
}

.insight-strip article:last-child {
  border-right: 0;
}

.insight-strip span {
  color: #9fb0c7;
  font-size: 0.67rem;
  font-weight: 750;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.insight-strip strong {
  margin-top: 5px;
  overflow: hidden;
  color: #fff;
  font-size: 1.04rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.insight-strip small {
  margin-top: 2px;
  color: #b5c3d5;
  font-size: 0.69rem;
}

.charts-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 16px;
}

.wide-chart {
  grid-column: 1 / -1;
}

.foreign-section {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-top: 8px;
  padding-top: 27px;
  border-top: 1px solid var(--color-border);
}

@media (max-width: 900px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }

  .wide-chart {
    grid-column: auto;
  }
}

@media (max-width: 620px) {
  .currency-legend {
    align-items: flex-start;
    flex-direction: column;
  }

  .insight-strip {
    grid-template-columns: 1fr;
  }

  .insight-strip article {
    border-right: 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }

  .insight-strip article:last-child {
    border-bottom: 0;
  }
}
</style>
