<template>
  <div class="monthly-chart-wrapper">
    <!-- Loading -->
    <div v-if="loading" class="chart-loading">
      <div class="spinner"></div>
      <p>Loading monthly analysis...</p>
    </div>

    <!-- No data -->
    <div v-else-if="!data || !data.months || data.months.length === 0" class="chart-empty">
      <p>No transaction data available yet. Upload a bank statement to see your monthly income & expenses.</p>
    </div>

    <div v-else>
      <!-- Summary row -->
      <div class="monthly-summary">
        <div class="summary-item income">
          <span class="summary-label">Total Income</span>
          <span class="summary-value">{{ formatCurrency(totalIncome) }}</span>
        </div>
        <div class="summary-item expenses">
          <span class="summary-label">Total Expenses</span>
          <span class="summary-value">{{ formatCurrency(totalExpenses) }}</span>
        </div>
        <div class="summary-item net" :class="totalNet >= 0 ? 'positive' : 'negative'">
          <span class="summary-label">Net Savings</span>
          <span class="summary-value">{{ formatCurrency(totalNet) }}</span>
        </div>
        <div class="summary-item avg">
          <span class="summary-label">Avg Monthly Income</span>
          <span class="summary-value">{{ formatCurrency(avgIncome) }}</span>
        </div>
      </div>

      <!-- Bar chart -->
      <div class="chart-container">
        <Bar :data="chartData" :options="chartOptions" />
      </div>

      <!-- Monthly table -->
      <div class="monthly-table-wrapper">
        <table class="monthly-table">
          <thead>
            <tr>
              <th>Month</th>
              <th class="num">Income</th>
              <th class="num">Expenses</th>
              <th class="num">Net</th>
              <th class="num">Savings %</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(month, i) in data.months" :key="month">
              <td>{{ month }}</td>
              <td class="num income-cell">{{ formatCurrency(data.income[i]) }}</td>
              <td class="num expense-cell">{{ formatCurrency(data.expenses[i]) }}</td>
              <td class="num" :class="data.net[i] >= 0 ? 'net-positive' : 'net-negative'">
                {{ formatCurrency(data.net[i]) }}
              </td>
              <td class="num">
                <span v-if="data.income[i] > 0">
                  {{ Math.round((data.net[i] / data.income[i]) * 100) }}%
                </span>
                <span v-else class="muted">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import { formatCurrency as formatMoney } from '@/utils/currency'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const props = defineProps({
  data: {
    type: Object,
    default: null
  },
  currency: {
    type: String,
    default: 'INR'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

function formatCurrency(value) {
  return formatMoney(value, props.currency, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  })
}

const totalIncome = computed(() =>
  (props.data?.income || []).reduce((s, v) => s + v, 0)
)
const totalExpenses = computed(() =>
  (props.data?.expenses || []).reduce((s, v) => s + v, 0)
)
const totalNet = computed(() => totalIncome.value - totalExpenses.value)
const avgIncome = computed(() => {
  const months = (props.data?.months || []).length
  return months > 0 ? totalIncome.value / months : 0
})

const chartData = computed(() => ({
  labels: props.data?.months || [],
  datasets: [
    {
      label: 'Income',
      data: props.data?.income || [],
      backgroundColor: 'rgba(16, 185, 129, 0.85)',
      borderColor: '#10b981',
      borderWidth: 1,
      borderRadius: 4
    },
    {
      label: 'Expenses',
      data: props.data?.expenses || [],
      backgroundColor: 'rgba(239, 68, 68, 0.85)',
      borderColor: '#ef4444',
      borderWidth: 1,
      borderRadius: 4
    }
  ]
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: {
      display: true,
      position: 'top',
      labels: { boxWidth: 12, padding: 12, font: { size: 11 } }
    },
    tooltip: {
      backgroundColor: 'rgba(0,0,0,0.8)',
      padding: 12,
      cornerRadius: 8,
      callbacks: {
        label: (ctx) =>
          `${ctx.dataset.label}: ${formatMoney(ctx.parsed.y, props.currency, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
          })}`,
        footer: (items) => {
          const income = items[0]?.parsed.y || 0
          const expense = items[1]?.parsed.y || 0
          const net = income - expense
          return `Net: ${formatMoney(net, props.currency, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
        }
      }
    }
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { font: { size: 11 } }
    },
    y: {
      beginAtZero: true,
      grid: { color: 'rgba(0,0,0,0.05)' },
      ticks: {
        callback: (v) =>
          formatMoney(v, props.currency, { maximumFractionDigits: 0, notation: 'compact' }),
        font: { size: 11 }
      }
    }
  }
}
</script>

<style scoped>
.monthly-chart-wrapper {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.chart-loading,
.chart-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #6b7280;
  gap: 12px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Summary row */
.monthly-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.summary-item {
  background: #f9fafb;
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-item.income  { border-left: 4px solid #10b981; }
.summary-item.expenses { border-left: 4px solid #ef4444; }
.summary-item.net.positive { border-left: 4px solid #3b82f6; }
.summary-item.net.negative { border-left: 4px solid #f59e0b; }
.summary-item.avg     { border-left: 4px solid #8b5cf6; }

.summary-label {
  font-size: 11px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.summary-value {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

/* Chart */
.chart-container {
  position: relative;
  height: 280px;
  margin-bottom: 20px;
}

/* Table */
.monthly-table-wrapper {
  overflow-x: auto;
}

.monthly-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.monthly-table th {
  background: #f3f4f6;
  color: #374151;
  font-weight: 600;
  padding: 10px 12px;
  text-align: left;
}

.monthly-table th.num,
.monthly-table td.num {
  text-align: right;
}

.monthly-table td {
  padding: 9px 12px;
  border-top: 1px solid #f3f4f6;
  color: #374151;
}

.monthly-table tbody tr:hover td {
  background: #f9fafb;
}

.income-cell  { color: #065f46; font-weight: 500; }
.expense-cell { color: #991b1b; font-weight: 500; }
.net-positive { color: #1d4ed8; font-weight: 600; }
.net-negative { color: #b45309; font-weight: 600; }
.muted        { color: #9ca3af; }
</style>
