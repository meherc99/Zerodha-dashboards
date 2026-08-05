<template>
  <div class="page-stack mutual-funds-page">
    <div class="page-intro">
      <div>
        <p class="eyebrow">Mutual funds</p>
        <h2>Funds, clearly organised</h2>
        <p>Review scheme-level value and returns without mixing funds into equity-sector analytics.</p>
      </div>
      <span class="status-chip">INR portfolio</span>
    </div>

    <section v-if="!mfHoldings.length" class="state-panel">
      <span class="state-icon" aria-hidden="true">MF</span>
      <h2>No mutual fund holdings</h2>
      <p>When Coin mutual-fund holdings are available for the selected account, they will appear on this dedicated page.</p>
      <div class="state-actions">
        <button type="button" class="primary-button" :disabled="holdingsStore.loading" @click="retrySync">
          {{ holdingsStore.loading ? 'Syncing…' : 'Sync portfolio' }}
        </button>
        <router-link to="/accounts" class="secondary-button">Check accounts</router-link>
      </div>
    </section>

    <template v-else>
      <PortfolioSummary :summary="holdingsStore.mfSummary" currency="INR" />

      <section class="fund-insights" aria-label="Mutual fund highlights">
        <article>
          <span>Largest fund</span>
          <strong>{{ largestFund?.fund_name || largestFund?.tradingsymbol || '—' }}</strong>
          <small>{{ largestAllocation.toFixed(1) }}% of fund value</small>
        </article>
        <article>
          <span>Schemes</span>
          <strong>{{ schemeCount }}</strong>
          <small>Across {{ mfHoldings.length }} {{ mfHoldings.length === 1 ? 'folio' : 'positions' }}</small>
        </article>
        <article>
          <span>Best return</span>
          <strong>{{ bestFund?.fund_name || bestFund?.tradingsymbol || '—' }}</strong>
          <small :class="pnlClass(bestFund?.pnl_percentage)">
            {{ formatPercentage(bestFund?.pnl_percentage) }}
          </small>
        </article>
      </section>

      <div class="charts-grid">
        <ChartPanel
          title="Fund allocation"
          subtitle="Largest schemes by current value"
          :has-data="allocationData.labels.length > 0"
        >
          <PieChart :data="allocationData" />
        </ChartPanel>

        <ChartPanel
          title="Scheme returns"
          subtitle="Unrealised return by scheme"
          :has-data="returnData.labels.length > 0"
          empty-title="No scheme returns"
          empty-message="Scheme return data will appear after a successful sync."
        >
          <BarChart :data="returnData" horizontal />
        </ChartPanel>
      </div>

      <MFHoldingsTable
        :holdings="mfHoldings"
        currency="INR"
      />
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useHoldingsStore } from '@/stores/holdings'
import { useAccountsStore } from '@/stores/accounts'
import { useUiStore } from '@/stores/ui'

import PortfolioSummary from '@/components/dashboard/PortfolioSummary.vue'
import MFHoldingsTable from '@/components/dashboard/MFHoldingsTable.vue'
import ChartPanel from '@/components/dashboard/ChartPanel.vue'
import PieChart from '@/components/charts/PieChart.vue'
import BarChart from '@/components/charts/BarChart.vue'

const holdingsStore = useHoldingsStore()
const accountsStore = useAccountsStore()
const uiStore = useUiStore()

const mfHoldings = computed(() => holdingsStore.mfHoldings)
const sortedFunds = computed(() => {
  return mfHoldings.value
    .slice()
    .sort((left, right) => Number(right.current_value || 0) - Number(left.current_value || 0))
})
const largestFund = computed(() => sortedFunds.value[0])
const bestFund = computed(() => {
  return mfHoldings.value
    .slice()
    .sort((left, right) => Number(right.pnl_percentage || 0) - Number(left.pnl_percentage || 0))[0]
})

const schemeCount = computed(() => {
  return new Set(
    mfHoldings.value.map(holding => holding.fund_name || holding.tradingsymbol)
  ).size
})
const largestAllocation = computed(() => {
  const total = holdingsStore.mfSummary.current_value
  return total > 0 ? (Number(largestFund.value?.current_value || 0) / total) * 100 : 0
})

const allocationData = computed(() => {
  const holdings = sortedFunds.value.slice(0, 8)
  return {
    labels: holdings.map(holding => holding.fund_name || holding.tradingsymbol),
    values: holdings.map(holding => Number(holding.current_value || 0))
  }
})

const returnData = computed(() => {
  const funds = mfHoldings.value
    .slice()
    .sort((left, right) => Number(right.pnl_percentage || 0) - Number(left.pnl_percentage || 0))
    .slice(0, 8)
  return {
    labels: funds.map(holding => holding.fund_name || holding.tradingsymbol),
    values: funds.map(holding => Number(holding.pnl_percentage || 0)),
    label: 'Unrealised return (%)'
  }
})

const retrySync = async () => {
  try {
    await holdingsStore.syncHoldings(accountsStore.currentAccount || null)
    uiStore.addNotification({ type: 'success', message: 'Portfolio synced successfully.' })
  } catch {
    uiStore.addNotification({ type: 'error', message: holdingsStore.error || 'Portfolio sync failed.' })
  }
}

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
.fund-insights {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.fund-insights article {
  display: flex;
  min-width: 0;
  flex-direction: column;
  padding: 15px 17px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.fund-insights span {
  color: var(--color-text-faint);
  font-size: 0.66rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.fund-insights strong {
  margin-top: 5px;
  overflow: hidden;
  color: var(--color-text);
  font-size: 0.95rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fund-insights small {
  margin-top: 2px;
  color: var(--color-text-faint);
  font-size: 0.69rem;
}

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
  background: #f1edff;
  color: #6940b6;
  font-size: 0.74rem;
  font-weight: 850;
}

@media (max-width: 900px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 620px) {
  .fund-insights {
    grid-template-columns: 1fr;
  }
}
</style>
