<template>
  <div class="analytics-view">
    <!-- Period Selector -->
    <div class="period-selector">
      <button
        v-for="period in periods"
        :key="period.value"
        :class="['period-btn', { active: selectedPeriod === period.value }]"
        @click="selectPeriod(period.value)"
      >
        {{ period.label }}
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading analytics...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button @click="refreshAnalytics" class="retry-btn">Retry</button>
    </div>

    <!-- Analytics Charts Grid -->
    <div v-else class="charts-grid">
      <!-- Balance Trend -->
      <div class="chart-card">
        <BalanceTrendChart
          :data="balanceTrend"
          :title="`Balance Trend (Last ${selectedPeriod} Days)`"
        />
      </div>

      <!-- Category Breakdown -->
      <div class="chart-card">
        <CategoryBreakdownChart
          :data="categoryBreakdown"
          title="Spending by Category"
        />
      </div>

      <!-- Cashflow -->
      <div class="chart-card full-width">
        <CashflowChart
          :data="cashflow"
          title="Weekly Income vs Expenses"
        />
      </div>

      <!-- Top Merchants -->
      <div class="chart-card">
        <TopMerchantsChart
          :data="topMerchants"
          title="Top 10 Merchants"
        />
      </div>

      <!-- Summary Stats -->
      <div class="chart-card stats-card">
        <h3>Summary</h3>
        <div class="stat-grid">
          <div class="stat">
            <span class="stat-label">Total Transactions</span>
            <span class="stat-value">{{ totalTransactions }}</span>
          </div>
          <div class="stat">
            <span class="stat-label">Total Income</span>
            <span class="stat-value positive">₹{{ formatCurrency(totalIncome) }}</span>
          </div>
          <div class="stat">
            <span class="stat-label">Total Expenses</span>
            <span class="stat-value negative">₹{{ formatCurrency(totalExpenses) }}</span>
          </div>
          <div class="stat">
            <span class="stat-label">Net Change</span>
            <span :class="['stat-value', netChange >= 0 ? 'positive' : 'negative']">
              ₹{{ formatCurrency(netChange) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useBankAccountsStore } from '@/stores/bankAccounts'
import BalanceTrendChart from './BalanceTrendChart.vue'
import CategoryBreakdownChart from './CategoryBreakdownChart.vue'
import CashflowChart from './CashflowChart.vue'
import TopMerchantsChart from './TopMerchantsChart.vue'

const props = defineProps({
  accountId: {
    type: Number,
    required: true
  }
})

const bankStore = useBankAccountsStore()
const { analytics } = storeToRefs(bankStore)

const periods = [
  { label: '7D', value: 7 },
  { label: '30D', value: 30 },
  { label: '90D', value: 90 },
  { label: '1Y', value: 365 }
]

const selectedPeriod = ref(30)

const loading = computed(() => analytics.value.loading)
const error = computed(() => analytics.value.error)
const balanceTrend = computed(() => analytics.value.balanceTrend)
const categoryBreakdown = computed(() => analytics.value.categoryBreakdown)
const cashflow = computed(() => analytics.value.cashflow)
const topMerchants = computed(() => analytics.value.topMerchants)

const totalTransactions = computed(() => {
  const categoryTotal = categoryBreakdown.value.reduce((sum, cat) => sum + (cat.count || 0), 0)
  const merchantTotal = topMerchants.value.reduce((sum, m) => sum + (m.transaction_count || 0), 0)
  return Math.max(categoryTotal, merchantTotal)
})

const totalIncome = computed(() => {
  return cashflow.value.reduce((sum, week) => sum + Math.abs(week.total_credit || 0), 0)
})

const totalExpenses = computed(() => {
  return cashflow.value.reduce((sum, week) => sum + Math.abs(week.total_debit || 0), 0)
})

const netChange = computed(() => totalIncome.value - totalExpenses.value)

function formatCurrency(value) {
  return Math.abs(value).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

async function selectPeriod(days) {
  selectedPeriod.value = days
  await loadAnalytics()
}

async function loadAnalytics() {
  await bankStore.fetchAllAnalytics(props.accountId, selectedPeriod.value)
}

async function refreshAnalytics() {
  await loadAnalytics()
}

// Watch for account ID changes
watch(() => props.accountId, () => {
  loadAnalytics()
}, { immediate: true })

onMounted(() => {
  loadAnalytics()
})
</script>

<style scoped>
.analytics-view {
  padding: 20px;
}

.period-selector {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  justify-content: center;
}

.period-btn {
  padding: 8px 20px;
  border: 2px solid #e5e7eb;
  background: white;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.period-btn:hover {
  border-color: #3b82f6;
  color: #3b82f6;
}

.period-btn.active {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f4f6;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state p {
  color: #ef4444;
  margin-bottom: 16px;
}

.retry-btn {
  padding: 10px 24px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.retry-btn:hover {
  background: #2563eb;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

.chart-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.chart-card.full-width {
  grid-column: 1 / -1;
}

.stats-card {
  padding: 24px;
}

.stats-card h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: bold;
  color: #111827;
}

.stat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 20px;
  font-weight: bold;
  color: #111827;
}

.stat-value.positive {
  color: #10b981;
}

.stat-value.negative {
  color: #ef4444;
}

/* Responsive */
@media (max-width: 768px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }

  .stat-grid {
    grid-template-columns: 1fr;
  }

  .period-selector {
    justify-content: flex-start;
    overflow-x: auto;
    padding-bottom: 8px;
  }
}
</style>
