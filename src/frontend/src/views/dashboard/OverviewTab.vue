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
        <span v-if="euHoldings.length"><i class="eur-dot"></i> EU equities · EUR</span>
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
      <!-- ── Net Worth Panel ──────────────────────────────────────── -->
      <section class="net-worth-panel" aria-labelledby="net-worth-title">
        <div class="nw-header">
          <div class="nw-title-block">
            <p class="eyebrow" id="net-worth-title">Total net worth</p>
            <div class="nw-total">
              <span class="nw-value">{{ formatLakhs(totalNetWorthInr) }}</span>
              <span
                class="nw-badge"
                :class="totalDayChangePct >= 0 ? 'pos' : 'neg'"
              >
                {{ totalDayChangePct >= 0 ? '+' : '' }}{{ totalDayChangePct.toFixed(2) }}% today
              </span>
            </div>
            <p class="nw-sub">
              Converted at live rates
              <template v-if="holdingsStore.exchangeRates">
                · USD {{ holdingsStore.exchangeRates.USD?.rate?.toFixed(2) }} / EUR {{ holdingsStore.exchangeRates.EUR?.rate?.toFixed(2) }}
              </template>
              <template v-else>(rates unavailable — using fallback)</template>
            </p>
          </div>
          <div class="nw-refresh">
            <span v-if="fxLoading" class="nw-loading">Fetching rates…</span>
            <button v-else type="button" class="ghost-button" @click="reloadFxRates">↻ Refresh rates</button>
          </div>
        </div>

        <div class="nw-currencies">
          <div class="nw-currency-tile inr-tile">
            <span class="nw-cy-label">INR</span>
            <span class="nw-cy-value">{{ formatCurrency(domesticSummary.current_value, 'INR') }}</span>
            <span
              class="nw-cy-change"
              :class="domesticSummary.day_change >= 0 ? 'pos' : 'neg'"
            >
              ({{ domesticSummary.day_change >= 0 ? '+' : '' }}{{ formatCurrency(domesticSummary.day_change, 'INR') }} today)
            </span>
          </div>

          <div v-if="usHoldings.length" class="nw-currency-tile usd-tile">
            <span class="nw-cy-label">USD</span>
            <span class="nw-cy-value">{{ formatCurrency(usSummary.current_value, 'USD') }}</span>
            <span
              class="nw-cy-change"
              :class="usSummary.day_change >= 0 ? 'pos' : 'neg'"
            >
              ({{ usSummary.day_change >= 0 ? '+' : '' }}{{ formatCurrency(usSummary.day_change, 'USD') }} today)
            </span>
          </div>

          <div v-if="euHoldings.length" class="nw-currency-tile eur-tile">
            <span class="nw-cy-label">EUR</span>
            <span class="nw-cy-value">{{ formatCurrency(euSummary.current_value, 'EUR') }}</span>
            <span
              class="nw-cy-change"
              :class="euSummary.day_change >= 0 ? 'pos' : 'neg'"
            >
              ({{ euSummary.day_change >= 0 ? '+' : '' }}{{ formatCurrency(euSummary.day_change, 'EUR') }} today)
            </span>
          </div>
        </div>
      </section>

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

      <div v-if="allHoldings.length" class="charts-grid">
        <ChartPanel
          title="Asset allocation"
          subtitle="Total portfolio value by asset class · all currencies converted to INR"
          :has-data="assetAllocationData.labels.length > 0"
          empty-message="Asset allocation will appear after a successful sync."
        >
          <PieChart :data="assetAllocationData" />
        </ChartPanel>

        <ChartPanel
          v-if="domesticHoldings.length"
          title="Holdings distribution (Top 15)"
          subtitle="Largest domestic positions by current value"
          :has-data="allocationData.labels.length > 0"
          empty-message="Holdings allocation will appear after a successful sync."
        >
          <BarChart :data="allocationData" horizontal />
        </ChartPanel>

        <ChartPanel
          v-if="domesticHoldings.length"
          title="Sector allocation"
          subtitle="Domestic portfolio value by sector and asset class"
          :has-data="sectorData.labels.length > 0"
          empty-title="No allocation data"
          empty-message="Allocation labels are not available for these holdings."
        >
          <PieChart :data="sectorData" />
        </ChartPanel>

        <ChartPanel
          v-if="memberBreakdown.length > 1"
          title="Member portfolio split"
          subtitle="Each family member’s share of the domestic portfolio by value"
          :has-data="memberSplitData.labels.length > 0"
        >
          <PieChart :data="memberSplitData" />
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

      <!-- ── Family Member Breakdown ──────────────────────────────── -->
      <section v-if="memberBreakdown.length > 1" class="members-section" aria-labelledby="members-title">
        <div class="section-heading">
          <div>
            <h2 id="members-title">Family members</h2>
            <p>Individual portfolio breakdown · all currencies shown in native units</p>
          </div>
        </div>

        <div class="family-allocation-chart">
          <ChartPanel
            title="Family portfolio share"
            subtitle="Each member's total portfolio value converted to INR"
            :has-data="memberTotalSplitData.labels.length > 0"
          >
            <PieChart :data="memberTotalSplitData" />
          </ChartPanel>
        </div>
        <div class="member-grid">
          <div
            v-for="member in memberBreakdown"
            :key="member.accountId"
            class="member-card"
          >
            <div class="mc-header">
              <span class="mc-avatar" :style="{ background: member.color }">{{ member.initials }}</span>
              <div class="mc-info">
                <strong>{{ member.name }}</strong>
                <span>{{ member.holdingsCount }} positions</span>
              </div>
              <span class="mc-pnl-badge" :class="member.pnlPct >= 0 ? 'pos' : 'neg'">
                {{ member.pnlPct >= 0 ? '+' : '' }}{{ member.pnlPct.toFixed(2) }}%
              </span>
            </div>
            <div class="mc-stats">
              <div class="mc-stat">
                <span>Current value</span>
                <strong>{{ formatCurrency(member.currentValue, 'INR') }}</strong>
              </div>
              <div class="mc-stat">
                <span>Invested</span>
                <strong>{{ formatCurrency(member.invested, 'INR') }}</strong>
              </div>
              <div class="mc-stat">
                <span>P&amp;L</span>
                <strong :class="member.pnl >= 0 ? 'pos' : 'neg'">{{ formatCurrency(member.pnl, 'INR') }}</strong>
              </div>
              <div class="mc-stat">
                <span>Today</span>
                <strong :class="member.dayChange >= 0 ? 'pos' : 'neg'">
                  {{ member.dayChange >= 0 ? '+' : '' }}{{ formatCurrency(member.dayChange, 'INR') }}
                </strong>
              </div>
            </div>
            <div class="mc-bar">
              <div
                class="mc-bar-fill"
                :style="{ width: member.portfolioShare + '%', background: member.color }"
              ></div>
            </div>
            <p class="mc-share">{{ member.portfolioShare.toFixed(1) }}% of domestic portfolio</p>
          </div>
        </div>
      </section>

      <section v-if="usHoldings.length" class="foreign-section" aria-labelledby="foreign-summary-title">
        <div class="section-heading">
          <div>
            <h2 id="foreign-summary-title">US equities</h2>
            <p>Kept separate from domestic totals · USD</p>
          </div>
          <router-link to="/dashboard/us-stocks" class="secondary-button">Open US portfolio</router-link>
        </div>
        <PortfolioSummary :summary="usSummary" currency="USD" />
      </section>

      <section v-if="euHoldings.length" class="foreign-section" aria-labelledby="eu-summary-title">
        <div class="section-heading">
          <div>
            <h2 id="eu-summary-title">EU equities</h2>
            <p>Kept separate from domestic totals · EUR</p>
          </div>
          <router-link to="/dashboard/eu-stocks" class="secondary-button">Open EU portfolio</router-link>
        </div>
        <PortfolioSummary :summary="euSummary" currency="EUR" />
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useHoldingsStore } from '@/stores/holdings'
import { useBankAccountsStore } from '@/stores/bankAccounts'
import { summarizeHoldings } from '@/utils/holdings'

import PortfolioSummary from '@/components/dashboard/PortfolioSummary.vue'
import ChartPanel from '@/components/dashboard/ChartPanel.vue'
import PieChart from '@/components/charts/PieChart.vue'
import BarChart from '@/components/charts/BarChart.vue'
import LineChart from '@/components/charts/LineChart.vue'

const holdingsStore = useHoldingsStore()
const bankAccountsStore = useBankAccountsStore()
const fxLoading = ref(false)

const allHoldings = computed(() => holdingsStore.holdings)
const domesticHoldings = computed(() =>
  allHoldings.value.filter(h => h.instrument_type !== 'us_equity' && h.instrument_type !== 'eu_equity')
)
const usHoldings = computed(() => allHoldings.value.filter(h => h.instrument_type === 'us_equity'))
const euHoldings = computed(() => allHoldings.value.filter(h => h.instrument_type === 'eu_equity'))
const domesticSummary = computed(() => summarizeHoldings(domesticHoldings.value))
const usSummary = computed(() => summarizeHoldings(usHoldings.value))
const euSummary = computed(() => summarizeHoldings(euHoldings.value))

// ── Exchange rates & net worth ─────────────────────────────────────────────
const USD_INR_FALLBACK = 84
const EUR_INR_FALLBACK = 92

const usdRate = computed(() => holdingsStore.exchangeRates?.USD?.rate ?? USD_INR_FALLBACK)
const eurRate = computed(() => holdingsStore.exchangeRates?.EUR?.rate ?? EUR_INR_FALLBACK)

const totalNetWorthInr = computed(() => {
  const inr = Number(domesticSummary.value.current_value || 0)
  const usd = Number(usSummary.value.current_value || 0) * usdRate.value
  const eur = Number(euSummary.value.current_value || 0) * eurRate.value
  return inr + usd + eur
})

const totalDayChangePct = computed(() => {
  const inrCurrent = Number(domesticSummary.value.current_value || 0)
  const inrChange = Number(domesticSummary.value.day_change || 0)
  const usdCurrent = Number(usSummary.value.current_value || 0) * usdRate.value
  const usdChange = Number(usSummary.value.day_change || 0) * usdRate.value
  const eurCurrent = Number(euSummary.value.current_value || 0) * eurRate.value
  const eurChange = Number(euSummary.value.day_change || 0) * eurRate.value

  const current = inrCurrent + usdCurrent + eurCurrent
  const prev = (inrCurrent - inrChange) + (usdCurrent - usdChange) + (eurCurrent - eurChange)
  return prev > 0 ? ((current - prev) / prev) * 100 : 0
})

const reloadFxRates = async () => {
  fxLoading.value = true
  try {
    await holdingsStore.fetchExchangeRates()
  } finally {
    fxLoading.value = false
  }
}

onMounted(() => {
  if (!holdingsStore.exchangeRates) reloadFxRates()
})
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

const OPUS_COLORS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#ef4444', '#f97316',
  '#f59e0b', '#10b981', '#06b6d4', '#3b82f6', '#14b8a6',
  '#a855f7', '#e879f9', '#fb7185', '#fbbf24', '#34d399',
]

const allocationData = computed(() => {
  const holdings = sortedDomestic.value.slice(0, 15)
  return {
    labels: holdings.map(holding => holding.tradingsymbol),
    values: holdings.map(holding => Number(holding.current_value || 0)),
    colors: holdings.map((_, i) => OPUS_COLORS[i % OPUS_COLORS.length]),
  }
})

const SECTOR_COLORS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#ef4444', '#f97316',
  '#f59e0b', '#10b981', '#06b6d4', '#3b82f6', '#14b8a6',
  '#a855f7', '#e879f9', '#fb7185', '#fbbf24', '#34d399',
  '#22d3ee', '#60a5fa', '#c084fc',
]

const normalizeSector = sector => {
  if (!sector) return 'Other'
  const s = sector.trim()
  const map = {
    'Financial Services': 'Financial Services', 'Banks': 'Financial Services',
    'Insurance': 'Financial Services', 'Capital Markets': 'Financial Services',
    'Diversified Financials': 'Financial Services',
    'Information Technology': 'Technology', 'IT': 'Technology',
    'Software': 'Technology', 'Internet': 'Technology',
    'Consumer Discretionary': 'Consumer', 'Consumer Goods': 'Consumer',
    'Consumer Staples': 'Consumer', 'FMCG': 'Consumer', 'Retailing': 'Consumer',
    'Automobile': 'Automobiles', 'Automobiles': 'Automobiles', 'Auto Components': 'Automobiles',
    'Healthcare': 'Healthcare', 'Pharma': 'Healthcare',
    'Pharmaceuticals': 'Healthcare', 'Biotechnology': 'Healthcare',
    'Energy': 'Energy', 'Oil & Gas': 'Energy', 'Petroleum': 'Energy', 'Power': 'Energy',
    'Metals': 'Metals & Mining', 'Metals & Mining': 'Metals & Mining',
    'Steel': 'Metals & Mining', 'Mining': 'Metals & Mining',
    'Infrastructure': 'Infrastructure', 'Construction': 'Infrastructure',
    'Real Estate': 'Real Estate', 'Realty': 'Real Estate',
    'Telecom': 'Telecom', 'Communication': 'Telecom',
    'Media': 'Media & Entertainment', 'Entertainment': 'Media & Entertainment',
    'Chemicals': 'Chemicals', 'Materials': 'Chemicals',
    'Fertilisers': 'Chemicals', 'Agro Chemicals': 'Chemicals',
    'Agriculture': 'Agriculture', 'Textiles': 'Textiles',
    'Utilities': 'Utilities', 'Transport': 'Transport', 'Logistics': 'Transport',
  }
  return map[s] || s
}

const sectorData = computed(() => {
  const categories = domesticHoldings.value.reduce((totals, holding) => {
    const category = holding.instrument_type === 'mf'
      ? 'Mutual Funds'
      : holding.instrument_type === 'fd'
        ? 'Fixed Deposits'
        : normalizeSector(holding.sector)
    totals[category] = (totals[category] || 0) + Number(holding.current_value || 0)
    return totals
  }, {})
  const sorted = Object.entries(categories).sort((left, right) => right[1] - left[1])
  return {
    labels: sorted.map(([label]) => label),
    values: sorted.map(([, value]) => value),
    colors: sorted.map((_, i) => SECTOR_COLORS[i % SECTOR_COLORS.length]),
    label: 'Current value'
  }
})

const MEMBER_COLORS = [
  '#6366f1', '#10b981', '#f59e0b', '#ef4444', '#06b6d4',
  '#8b5cf6', '#ec4899', '#f97316', '#14b8a6', '#3b82f6',
]

const memberBreakdown = computed(() => {
  const byAccount = {}
  for (const h of domesticHoldings.value) {
    const id = h.account_id
    if (!byAccount[id]) byAccount[id] = { name: h.account_name || `Account ${id}`, accountId: id, holdings: [] }
    byAccount[id].holdings.push(h)
  }
  const totalDomestic = Number(domesticSummary.value.current_value || 0)
  return Object.values(byAccount).map((member, i) => {
    const summary = summarizeHoldings(member.holdings)
    const currentValue = Number(summary.current_value || 0)
    const invested = Number(summary.total_investment || 0)
    const pnl = Number(summary.total_pnl || 0)
    const dayChange = Number(summary.day_change || 0)
    const pnlPct = invested > 0 ? (pnl / invested) * 100 : 0
    const portfolioShare = totalDomestic > 0 ? (currentValue / totalDomestic) * 100 : 0
    const words = member.name.trim().split(/\s+/)
    const initials = words.length > 1
      ? (words[0][0] + words[1][0]).toUpperCase()
      : member.name.slice(0, 2).toUpperCase()
    return {
      accountId: member.accountId,
      name: member.name,
      initials,
      color: MEMBER_COLORS[i % MEMBER_COLORS.length],
      holdingsCount: member.holdings.length,
      currentValue,
      invested,
      pnl,
      pnlPct,
      dayChange,
      portfolioShare,
    }
  }).sort((a, b) => b.currentValue - a.currentValue)
})

const memberSplitData = computed(() => ({
  labels: memberBreakdown.value.map(m => m.name),
  values: memberBreakdown.value.map(m => m.currentValue),
  colors: memberBreakdown.value.map(m => m.color),
}))

// ── Asset Allocation pie (all asset classes in INR equivalent) ─────────────
const ASSET_CLASS_COLORS = {
  'Indian Stocks': '#6366f1',
  'Mutual Funds': '#10b981',
  'Fixed Deposits': '#f59e0b',
  'US Stocks': '#06b6d4',
  'EU Stocks': '#3b82f6',
  'Bank Balance': '#8b5cf6',
}

const assetAllocationData = computed(() => {
  const equityVal = Number(summarizeHoldings(allHoldings.value.filter(h => h.instrument_type === 'equity')).current_value || 0)
  const mfVal = Number(summarizeHoldings(allHoldings.value.filter(h => h.instrument_type === 'mf')).current_value || 0)
  const fdVal = Number(summarizeHoldings(allHoldings.value.filter(h => h.instrument_type === 'fd')).current_value || 0)
  const usVal = Number(summarizeHoldings(allHoldings.value.filter(h => h.instrument_type === 'us_equity')).current_value || 0) * usdRate.value
  const euVal = Number(summarizeHoldings(allHoldings.value.filter(h => h.instrument_type === 'eu_equity')).current_value || 0) * eurRate.value

  // Bank balance: sum all INR balances + convert foreign balances
  const balances = bankAccountsStore.balancesByCurrency
  const bankInr = (Number(balances.INR || 0))
    + (Number(balances.USD || 0) * usdRate.value)
    + (Number(balances.EUR || 0) * eurRate.value)

  const entries = [
    ['Indian Stocks', equityVal],
    ['Mutual Funds', mfVal],
    ['Fixed Deposits', fdVal],
    ['US Stocks', usVal],
    ['EU Stocks', euVal],
    ['Bank Balance', bankInr],
  ].filter(([, v]) => v > 0)

  return {
    labels: entries.map(([label]) => label),
    values: entries.map(([, v]) => v),
    colors: entries.map(([label]) => ASSET_CLASS_COLORS[label]),
  }
})

// ── Family total split (domestic + foreign all converted to INR) ───────────
const memberTotalSplitData = computed(() => {
  const byAccount = {}
  for (const h of allHoldings.value) {
    const id = h.account_id
    if (!byAccount[id]) byAccount[id] = { name: h.account_name || `Account ${id}`, holdings: [], colorIndex: 0 }
    byAccount[id].holdings.push(h)
  }
  const entries = Object.values(byAccount).map((member, i) => {
    const domestic = summarizeHoldings(member.holdings.filter(h => h.instrument_type !== 'us_equity' && h.instrument_type !== 'eu_equity'))
    const us = summarizeHoldings(member.holdings.filter(h => h.instrument_type === 'us_equity'))
    const eu = summarizeHoldings(member.holdings.filter(h => h.instrument_type === 'eu_equity'))
    const totalInr = Number(domestic.current_value || 0)
      + Number(us.current_value || 0) * usdRate.value
      + Number(eu.current_value || 0) * eurRate.value
    return { name: member.name, value: totalInr, color: MEMBER_COLORS[i % MEMBER_COLORS.length] }
  }).filter(e => e.value > 0).sort((a, b) => b.value - a.value)

  return {
    labels: entries.map(e => e.name),
    values: entries.map(e => e.value),
    colors: entries.map(e => e.color),
  }
})

const pnlClass = value => {
  const number = Number(value || 0)
  return number > 0 ? 'positive' : number < 0 ? 'negative' : 'neutral'
}
const formatPercentage = value => {
  const number = Number(value || 0)
  return `${number > 0 ? '+' : number < 0 ? '\u2212' : ''}${Math.abs(number).toFixed(2)}% return`
}

const formatCurrency = (value, currency) => {
  const num = Number(value || 0)
  const abs = Math.abs(num)
  const prefix = currency === 'INR' ? '\u20B9' : currency === 'USD' ? '$' : '\u20AC'
  if (abs >= 10000000) return `${prefix}${(num / 10000000).toFixed(2)} Cr`
  if (abs >= 100000) return `${prefix}${(num / 100000).toFixed(2)} L`
  if (abs >= 1000) return `${prefix}${(num / 1000).toFixed(1)} K`
  return `${prefix}${num.toFixed(0)}`
}

const formatLakhs = value => {
  const num = Number(value || 0)
  if (num >= 10000000) return `\u20B9${(num / 10000000).toFixed(2)} Cr`
  return `\u20B9${(num / 100000).toFixed(2)} L`
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
.eur-dot { background: #003399; }

/* ── Member Breakdown ──────────────────────────────────────────────── */
.members-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.member-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.member-card {
  padding: 18px 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
  transition: box-shadow 160ms ease;
}

.member-card:hover {
  box-shadow: var(--shadow-md, 0 4px 16px rgba(0,0,0,0.08));
}

/* ── Family Allocation Chart ────────────────────────────────────────── */
.family-allocation-chart {
  margin-bottom: 20px;
}

.mc-header {
  display: flex;
  align-items: center;
  gap: 11px;
  margin-bottom: 16px;
}

.mc-avatar {
  display: grid;
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  place-items: center;
  border-radius: 12px;
  color: #fff;
  font-size: 0.72rem;
  font-weight: 850;
}

.mc-info {
  flex: 1;
  min-width: 0;
}

.mc-info strong {
  display: block;
  overflow: hidden;
  font-size: 0.87rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mc-info span {
  color: var(--color-text-faint);
  font-size: 0.67rem;
}

.mc-pnl-badge {
  flex-shrink: 0;
  padding: 3px 8px;
  border-radius: 20px;
  font-size: 0.69rem;
  font-weight: 750;
}

.mc-pnl-badge.pos { background: var(--color-positive-soft); color: var(--color-positive); }
.mc-pnl-badge.neg { background: var(--color-negative-soft, #fef2f2); color: var(--color-negative); }

.mc-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 14px;
}

.mc-stat span {
  display: block;
  color: var(--color-text-faint);
  font-size: 0.63rem;
  font-weight: 750;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 2px;
}

.mc-stat strong {
  font-size: 0.83rem;
}

.mc-stat .pos { color: var(--color-positive); }
.mc-stat .neg { color: var(--color-negative); }

.mc-bar {
  height: 4px;
  border-radius: 2px;
  background: var(--color-border);
  overflow: hidden;
  margin-bottom: 5px;
}

.mc-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 400ms ease;
}

.mc-share {
  color: var(--color-text-faint);
  font-size: 0.63rem;
}

/* ── Net Worth Panel ──────────────────────────────────────────────── */
.net-worth-panel {
  padding: 22px 24px;
  border: 1px solid #cbd9f7;
  border-radius: var(--radius-lg);
  background: linear-gradient(145deg, #0e1f3d, #132a50);
  box-shadow: var(--shadow-sm);
}

.nw-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.nw-title-block .eyebrow {
  color: #7a9ac8;
  margin: 0 0 6px;
}

.nw-total {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.nw-value {
  color: #fff;
  font-size: 1.9rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.nw-badge {
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 750;
}

.nw-badge.pos {
  background: rgba(52, 211, 153, 0.15);
  color: #34d399;
}

.nw-badge.neg {
  background: rgba(248, 113, 113, 0.15);
  color: #f87171;
}

.nw-sub {
  margin: 6px 0 0;
  color: #5e7da5;
  font-size: 0.69rem;
}

.nw-refresh {
  flex-shrink: 0;
}

.nw-loading {
  color: #5e7da5;
  font-size: 0.72rem;
}

.ghost-button {
  padding: 6px 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: #7a9ac8;
  cursor: pointer;
  font-size: 0.72rem;
  font-weight: 700;
  transition: background 150ms ease, color 150ms ease;
}

.ghost-button:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

.nw-currencies {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.nw-currency-tile {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.nw-cy-label {
  font-size: 0.62rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.inr-tile .nw-cy-label { color: #7db9d7; }
.usd-tile .nw-cy-label { color: #7dd3a8; }
.eur-tile .nw-cy-label { color: #7ba7f7; }

.nw-cy-value {
  color: #e8eef8;
  font-size: 1.1rem;
  font-weight: 750;
}

.nw-cy-change {
  font-size: 0.69rem;
  font-weight: 650;
}

.nw-cy-change.pos { color: #34d399; }
.nw-cy-change.neg { color: #f87171; }

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

  .nw-header {
    flex-direction: column;
  }

  .nw-value {
    font-size: 1.45rem;
  }

  .nw-currencies {
    grid-template-columns: 1fr;
  }
}
</style>
