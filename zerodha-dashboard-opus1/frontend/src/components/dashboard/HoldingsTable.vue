<template>
  <div class="holdings-table-container">
    <div class="table-header">
      <h2>Holdings</h2>
      <div class="table-controls">
        <select v-model="filterType" class="filter-select">
          <option value="">All Types</option>
          <option value="equity">Equity</option>
          <option value="mf">Mutual Funds</option>
        </select>
        <select v-model="sortBy" class="sort-select">
          <option value="pnl_percentage">Sort by P&L %</option>
          <option value="current_value">Sort by Value</option>
          <option value="tradingsymbol">Sort by Symbol</option>
        </select>
      </div>
    </div>

    <div class="table-wrapper">
      <table class="holdings-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Type</th>
            <th class="text-right">Qty</th>
            <th class="text-right">Avg Price</th>
            <th class="text-right">LTP</th>
            <th class="text-right">Current Value</th>
            <th class="text-right">P&L</th>
            <th class="text-right">P&L %</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="holding in filteredHoldings" :key="holding.id">
            <td class="symbol-cell">
              <div class="symbol">{{ holding.tradingsymbol }}</div>
              <div v-if="holding.sector" class="sector">{{ holding.sector }}</div>
            </td>
            <td>
              <span class="type-badge" :class="holding.instrument_type">
                {{ holding.instrument_type.toUpperCase() }}
              </span>
            </td>
            <td class="text-right">{{ holding.quantity }}</td>
            <td class="text-right">₹{{ formatNumber(holding.average_price) }}</td>
            <td class="text-right">₹{{ formatNumber(holding.last_price) }}</td>
            <td class="text-right">₹{{ formatNumber(holding.current_value) }}</td>
            <td class="text-right" :class="getPnLClass(holding.pnl)">
              {{ formatPnL(holding.pnl) }}
            </td>
            <td class="text-right" :class="getPnLClass(holding.pnl_percentage)">
              {{ formatPercentage(holding.pnl_percentage) }}
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="filteredHoldings.length === 0" class="empty-state">
        <p>No holdings found</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  holdings: {
    type: Array,
    required: true
  }
})

const filterType = ref('')
const sortBy = ref('pnl_percentage')

const filteredHoldings = computed(() => {
  let filtered = [...props.holdings]

  // Apply type filter
  if (filterType.value) {
    filtered = filtered.filter(h => h.instrument_type === filterType.value)
  }

  // Apply sorting
  filtered.sort((a, b) => {
    const aVal = a[sortBy.value] || 0
    const bVal = b[sortBy.value] || 0

    if (sortBy.value === 'tradingsymbol') {
      return aVal.localeCompare(bVal)
    }
    return bVal - aVal
  })

  return filtered
})

const formatNumber = (value) => {
  return Number(value).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

const formatPnL = (value) => {
  const num = Number(value)
  const formatted = formatNumber(Math.abs(num))
  return num >= 0 ? `+₹${formatted}` : `-₹${formatted}`
}

const formatPercentage = (value) => {
  const num = Number(value)
  return num >= 0 ? `+${num.toFixed(2)}%` : `${num.toFixed(2)}%`
}

const getPnLClass = (value) => {
  return Number(value) >= 0 ? 'positive' : 'negative'
}
</script>

<style scoped>
.holdings-table-container {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.table-header h2 {
  margin: 0;
  font-size: 20px;
  color: #111827;
}

.table-controls {
  display: flex;
  gap: 10px;
}

.filter-select,
.sort-select {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.table-wrapper {
  overflow-x: auto;
}

.holdings-table {
  width: 100%;
  border-collapse: collapse;
}

.holdings-table thead {
  background: #f9fafb;
  border-bottom: 2px solid #e5e7eb;
}

.holdings-table th {
  padding: 12px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.holdings-table td {
  padding: 12px;
  border-bottom: 1px solid #f3f4f6;
  font-size: 14px;
}

.holdings-table tbody tr:hover {
  background: #f9fafb;
}

.symbol-cell {
  font-weight: 600;
}

.symbol {
  color: #111827;
}

.sector {
  font-size: 11px;
  color: #6b7280;
  margin-top: 2px;
}

.type-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.type-badge.equity {
  background: #dbeafe;
  color: #1e40af;
}

.type-badge.mf {
  background: #fef3c7;
  color: #92400e;
}

.text-right {
  text-align: right;
}

.positive {
  color: #10b981;
  font-weight: 600;
}

.negative {
  color: #ef4444;
  font-weight: 600;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #9ca3af;
}

@media (max-width: 768px) {
  .table-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }

  .table-controls {
    width: 100%;
    flex-direction: column;
  }

  .filter-select,
  .sort-select {
    width: 100%;
  }
}
</style>
