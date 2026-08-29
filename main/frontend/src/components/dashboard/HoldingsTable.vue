<template>
  <section class="holdings-card" :aria-labelledby="headingId">
    <div class="table-header">
      <div>
        <h2 :id="headingId">{{ title }}</h2>
        <p>{{ resultLabel }}<span v-if="subtitle"> · {{ subtitle }}</span></p>
      </div>
      <button
        v-if="hasActiveFilters"
        type="button"
        class="clear-button"
        @click="clearFilters"
      >
        Clear filters
      </button>
    </div>

    <div class="table-controls">
      <label class="search-control">
        <span class="sr-only">Search holdings</span>
        <span class="search-icon" aria-hidden="true"></span>
        <input
          v-model.trim="searchQuery"
          type="search"
          placeholder="Search symbol or category"
          autocomplete="off"
        />
      </label>

      <label v-if="availableTypes.length > 1" class="select-control">
        <span>Asset</span>
        <select v-model="filterType" aria-label="Filter by asset type">
          <option value="">All assets</option>
          <option v-for="type in availableTypes" :key="type" :value="type">
            {{ typeLabel(type) }}
          </option>
        </select>
      </label>

      <label class="select-control">
        <span>Performance</span>
        <select v-model="performanceFilter" aria-label="Filter by performance">
          <option value="">All positions</option>
          <option value="gains">In profit</option>
          <option value="losses">In loss</option>
        </select>
      </label>

      <label class="select-control mobile-sort">
        <span>Sort by</span>
        <select v-model="sortBy" aria-label="Sort holdings">
          <option value="current_value">Current value</option>
          <option value="pnl_percentage">Return</option>
          <option value="pnl">Profit and loss</option>
          <option v-if="showDayChange" value="day_change_percentage">% Day change</option>
          <option v-if="showMember" value="account_name">Member</option>
          <option value="tradingsymbol">Name</option>
        </select>
      </label>

      <button
        type="button"
        class="direction-button"
        :aria-label="sortDirection === 'desc' ? 'Sort descending; activate for ascending' : 'Sort ascending; activate for descending'"
        :title="sortDirection === 'desc' ? 'Descending' : 'Ascending'"
        @click="toggleSortDirection"
      >
        <span aria-hidden="true">{{ sortDirection === 'desc' ? '↓' : '↑' }}</span>
      </button>
    </div>

    <template v-if="filteredHoldings.length">
      <div class="table-wrapper">
        <table class="holdings-table">
          <thead>
            <tr>
              <th
                v-for="column in columns"
                :key="column.key"
                :class="{ 'text-right': column.numeric }"
                :aria-sort="ariaSort(column.key)"
              >
                <button type="button" @click="setSort(column.key)">
                  {{ column.label }}
                  <span
                    class="sort-indicator"
                    :class="{ inactive: sortBy !== column.key }"
                    aria-hidden="true"
                  >{{ sortBy === column.key ? (sortDirection === 'desc' ? '↓' : '↑') : '↕' }}</span>
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="holding in filteredHoldings" :key="holdingKey(holding)">
              <td class="symbol-cell">
                <div class="symbol">{{ holding.tradingsymbol || 'Unnamed holding' }}</div>
                <div v-if="holding.sector" class="sector">{{ holding.sector }}</div>
                <div v-if="quoteMeta(holding)" class="source-meta">{{ quoteMeta(holding) }}</div>
              </td>
              <td v-if="showMember" class="member-cell">{{ holding.account_name || '—' }}</td>
              <td>
                <span class="type-badge" :class="holding.instrument_type">
                  {{ typeLabel(holding.instrument_type) }}
                </span>
              </td>
              <td class="text-right number-cell">{{ formatQuantity(holding.quantity) }}</td>
              <td class="text-right number-cell">{{ formatMoney(holding.average_price) }}</td>
              <td class="text-right number-cell">{{ formatMoney(holding.last_price) }}</td>
              <td class="text-right current-value">{{ formatMoney(holding.current_value) }}</td>
              <td class="text-right" :class="pnlClass(holding.pnl)">
                {{ formatSignedMoney(holding.pnl) }}
              </td>
              <td class="text-right" :class="pnlClass(holding.pnl_percentage)">
                {{ formatPercentage(holding.pnl_percentage) }}
              </td>
              <td v-if="showDayChange" class="text-right" :class="pnlClass(holding.day_change_percentage)">
                {{ formatPercentage(holding.day_change_percentage) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <ul class="mobile-holdings" aria-label="Filtered holdings">
        <li v-for="holding in filteredHoldings" :key="`mobile-${holdingKey(holding)}`">
          <div class="mobile-card-head">
            <div>
              <strong>{{ holding.tradingsymbol || 'Unnamed holding' }}</strong>
              <span>{{ holding.sector || typeLabel(holding.instrument_type) }}</span>
              <small v-if="showMember && holding.account_name" class="mobile-source">{{ holding.account_name }}</small>
              <small v-if="quoteMeta(holding)" class="mobile-source">{{ quoteMeta(holding) }}</small>
            </div>
            <span class="return-pill" :class="pnlClass(holding.pnl_percentage)">
              {{ formatPercentage(holding.pnl_percentage) }}
            </span>
          </div>
          <dl>
            <div>
              <dt>Current value</dt>
              <dd>{{ formatMoney(holding.current_value) }}</dd>
            </div>
            <div>
              <dt>Profit / loss</dt>
              <dd :class="pnlClass(holding.pnl)">{{ formatSignedMoney(holding.pnl) }}</dd>
            </div>
            <div>
              <dt>Quantity</dt>
              <dd>{{ formatQuantity(holding.quantity) }}</dd>
            </div>
            <div>
              <dt>Avg. / latest</dt>
              <dd>{{ formatMoney(holding.average_price) }} / {{ formatMoney(holding.last_price) }}</dd>
            </div>
            <div v-if="showDayChange">
              <dt>% Day change</dt>
              <dd :class="pnlClass(holding.day_change_percentage)">{{ formatPercentage(holding.day_change_percentage) }}</dd>
            </div>
          </dl>
        </li>
      </ul>
    </template>

    <div v-else class="empty-state">
      <span class="empty-icon" aria-hidden="true">{{ holdings.length ? '⌕' : '—' }}</span>
      <h3>{{ holdings.length ? 'No matching holdings' : emptyTitle }}</h3>
      <p>{{ holdings.length ? 'Try a broader search or clear your filters.' : emptyMessage }}</p>
      <button
        v-if="holdings.length && hasActiveFilters"
        type="button"
        class="secondary-button"
        @click="clearFilters"
      >
        Clear filters
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import {
  filterAndSortHoldings,
  holdingTypeLabel,
  safeNumber
} from '@/utils/holdings'

const props = defineProps({
  holdings: {
    type: Array,
    required: true
  },
  showDayChange: {
    type: Boolean,
    default: false
  },
  showMember: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: 'Holdings'
  },
  subtitle: {
    type: String,
    default: ''
  },
  currency: {
    type: String,
    default: 'INR'
  },
  emptyTitle: {
    type: String,
    default: 'No holdings yet'
  },
  emptyMessage: {
    type: String,
    default: 'Sync an account to see positions here.'
  }
})

const searchQuery = ref('')
const filterType = ref('')
const performanceFilter = ref('')
const sortBy = ref('current_value')
const sortDirection = ref('desc')
const headingId = `holdings-${Math.random().toString(36).slice(2, 9)}`

const baseColumns = [
  { key: 'tradingsymbol', label: 'Instrument', numeric: false },
  { key: 'instrument_type', label: 'Asset', numeric: false },
  { key: 'quantity', label: 'Quantity', numeric: true },
  { key: 'average_price', label: 'Avg. price', numeric: true },
  { key: 'last_price', label: 'Latest', numeric: true },
  { key: 'current_value', label: 'Current value', numeric: true },
  { key: 'pnl', label: 'P&L', numeric: true },
  { key: 'pnl_percentage', label: 'Return', numeric: true }
]

const columns = computed(() => {
  const cols = [...baseColumns]
  if (props.showMember) {
    cols.splice(1, 0, { key: 'account_name', label: 'Member', numeric: false })
  }
  if (props.showDayChange) {
    cols.push({ key: 'day_change_percentage', label: '% Day change', numeric: true })
  }
  return cols
})

const availableTypes = computed(() => {
  return [...new Set(props.holdings.map(holding => holding.instrument_type).filter(Boolean))].sort()
})

const hasActiveFilters = computed(() => {
  return Boolean(searchQuery.value || filterType.value || performanceFilter.value)
})

const filteredHoldings = computed(() => {
  return filterAndSortHoldings(props.holdings, {
    searchQuery: searchQuery.value,
    filterType: filterType.value,
    performanceFilter: performanceFilter.value,
    sortBy: sortBy.value,
    sortDirection: sortDirection.value
  })
})

const resultLabel = computed(() => {
  const shown = filteredHoldings.value.length
  const total = props.holdings.length
  if (hasActiveFilters.value) return `${shown} of ${total} positions`
  return `${total} ${total === 1 ? 'position' : 'positions'}`
})

const typeLabel = holdingTypeLabel

const moneyFormatter = computed(() => new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: props.currency,
  minimumFractionDigits: 0,
  maximumFractionDigits: 2
}))

const formatMoney = value => moneyFormatter.value.format(safeNumber(value))
const formatQuantity = value => safeNumber(value).toLocaleString('en-IN', { maximumFractionDigits: 4 })

const formatSignedMoney = value => {
  const number = safeNumber(value)
  if (number === 0) return moneyFormatter.value.format(0)
  return `${number > 0 ? '+' : '−'}${moneyFormatter.value.format(Math.abs(number))}`
}

const formatPercentage = value => {
  const number = safeNumber(value)
  return `${number > 0 ? '+' : number < 0 ? '−' : ''}${Math.abs(number).toFixed(2)}%`
}

const pnlClass = value => {
  const number = safeNumber(value)
  if (number > 0) return 'positive'
  if (number < 0) return 'negative'
  return 'neutral'
}

const setSort = key => {
  if (sortBy.value === key) {
    toggleSortDirection()
    return
  }
  sortBy.value = key
  sortDirection.value = key === 'tradingsymbol' || key === 'instrument_type' ? 'asc' : 'desc'
}

const toggleSortDirection = () => {
  sortDirection.value = sortDirection.value === 'desc' ? 'asc' : 'desc'
}

const ariaSort = key => {
  if (sortBy.value !== key) return 'none'
  return sortDirection.value === 'desc' ? 'descending' : 'ascending'
}

const clearFilters = () => {
  searchQuery.value = ''
  filterType.value = ''
  performanceFilter.value = ''
}

const holdingKey = holding => {
  const folio = holding.folio || holding.folio_number || 'position'
  return holding.id || `${holding.account_id || 'all'}-${holding.instrument_type || 'asset'}-${folio}-${holding.tradingsymbol}`
}

const quoteMeta = holding => {
  if (holding.instrument_type !== 'us_equity') return ''
  const source = String(holding.source || '').toLocaleLowerCase()
  if (source === 'cost_basis' || source.includes('at_cost')) {
    return 'At cost · market quote unavailable'
  }

  const sourceLabel = source === 'finnhub'
    ? 'Finnhub quote'
    : source
      ? source.replaceAll('_', ' ')
      : 'Price source unavailable'
  const priceDate = holding.last_price_date || holding.valued_at
  if (!priceDate) return sourceLabel

  const date = new Date(priceDate)
  if (Number.isNaN(date.getTime())) return sourceLabel
  return `${sourceLabel} · ${date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}`
}
</script>

<style scoped>
.holdings-card {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.table-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 20px 14px;
}

.table-header h2 {
  margin: 0;
  color: var(--color-text);
  font-size: 1.05rem;
  letter-spacing: -0.015em;
}

.table-header p {
  margin: 4px 0 0;
  color: var(--color-text-faint);
  font-size: 0.77rem;
}

.clear-button {
  padding: 5px 0;
  border: 0;
  background: transparent;
  color: var(--color-primary-dark);
  font-size: 0.76rem;
  font-weight: 750;
}

.clear-button:hover {
  text-decoration: underline;
}

.table-controls {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) repeat(3, auto) 40px;
  gap: 9px;
  padding: 0 20px 18px;
}

.search-control {
  position: relative;
  display: flex;
  min-width: 0;
}

.search-control input,
.select-control select {
  min-height: 40px;
  border: 1px solid var(--color-border-strong);
  border-radius: 10px;
  background: var(--color-surface);
  font-size: 0.8rem;
}

.search-control input {
  width: 100%;
  padding: 8px 12px 8px 36px;
}

.search-control input::placeholder {
  color: var(--color-text-faint);
}

.search-icon {
  position: absolute;
  z-index: 1;
  top: 12px;
  left: 13px;
  width: 12px;
  height: 12px;
  border: 2px solid var(--color-text-faint);
  border-radius: 50%;
  pointer-events: none;
}

.search-icon::after {
  position: absolute;
  width: 6px;
  height: 2px;
  right: -5px;
  bottom: -2px;
  transform: rotate(45deg);
  border-radius: 2px;
  background: var(--color-text-faint);
  content: "";
}

.select-control {
  display: flex;
  align-items: center;
  gap: 6px;
}

.select-control > span {
  color: var(--color-text-faint);
  font-size: 0.7rem;
  font-weight: 700;
}

.select-control select {
  max-width: 160px;
  padding: 7px 30px 7px 10px;
  color: var(--color-text-soft);
  font-weight: 650;
}

.mobile-sort {
  display: none;
}

.direction-button {
  display: grid;
  width: 40px;
  min-height: 40px;
  place-items: center;
  border: 1px solid var(--color-border-strong);
  border-radius: 10px;
  background: var(--color-surface);
  color: var(--color-text-soft);
  font-size: 1rem;
  font-weight: 800;
}

.table-wrapper {
  overflow-x: auto;
  border-top: 1px solid var(--color-border);
}

.holdings-table {
  width: 100%;
  min-width: 880px;
  border-collapse: collapse;
}

.holdings-table thead {
  background: var(--color-surface-subtle);
}

.holdings-table th {
  padding: 0;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-faint);
  text-align: left;
}

.holdings-table th button {
  width: 100%;
  padding: 11px 14px;
  border: 0;
  background: transparent;
  color: inherit;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.045em;
  text-align: inherit;
  text-transform: uppercase;
  white-space: nowrap;
}

.holdings-table th button:hover {
  color: var(--color-text);
}

.sort-indicator {
  color: var(--color-primary);
}

.sort-indicator.inactive {
  color: var(--color-text-faint);
  opacity: 0.5;
}

.holdings-table td {
  padding: 13px 14px;
  border-bottom: 1px solid #edf1f5;
  color: var(--color-text-soft);
  font-size: 0.79rem;
  white-space: nowrap;
}

.holdings-table tbody tr:last-child td {
  border-bottom: 0;
}

.holdings-table tbody tr:hover {
  background: var(--color-surface-subtle);
}

.symbol-cell {
  min-width: 170px;
}

.member-cell {
  color: var(--color-text-soft);
  font-size: 0.78rem;
  white-space: nowrap;
}

.symbol {
  color: var(--color-text);
  font-weight: 800;
}

.sector {
  max-width: 210px;
  margin-top: 2px;
  overflow: hidden;
  color: var(--color-text-faint);
  font-size: 0.68rem;
  text-overflow: ellipsis;
}

.source-meta {
  margin-top: 3px;
  color: var(--color-warning);
  font-size: 0.62rem;
  font-weight: 650;
  text-transform: capitalize;
}

.type-badge {
  display: inline-flex;
  padding: 3px 7px;
  border-radius: 6px;
  background: var(--color-surface-strong);
  color: var(--color-text-soft);
  font-size: 0.64rem;
  font-weight: 750;
}

.type-badge.equity {
  background: var(--color-primary-soft);
  color: var(--color-primary-dark);
}

.type-badge.mf {
  background: var(--color-accent-soft);
  color: var(--color-accent);
}

.type-badge.us_equity {
  background: var(--color-positive-soft);
  color: var(--color-positive);
}

.type-badge.fd {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}

.number-cell {
  font-variant-numeric: tabular-nums;
}

.current-value {
  color: var(--color-text) !important;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
}

.neutral {
  color: var(--color-text-soft);
}

.positive,
.negative {
  font-weight: 750;
  font-variant-numeric: tabular-nums;
}

.empty-state {
  display: flex;
  min-height: 230px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  padding: 30px;
  border-top: 1px solid var(--color-border);
  text-align: center;
}

.empty-icon {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 50%;
  background: var(--color-surface-strong);
  color: var(--color-text-faint);
  font-size: 1.1rem;
}

.empty-state h3 {
  margin: 10px 0 3px;
  font-size: 0.95rem;
}

.empty-state p {
  margin: 0 0 15px;
  color: var(--color-text-soft);
  font-size: 0.8rem;
}

.mobile-holdings {
  display: none;
}

@media (max-width: 1060px) {
  .table-controls {
    grid-template-columns: minmax(190px, 1fr) repeat(2, auto) 40px;
  }
}

@media (max-width: 760px) {
  .table-header {
    padding: 17px 15px 13px;
  }

  .table-controls {
    grid-template-columns: 1fr 1fr 40px;
    padding: 0 15px 15px;
  }

  .search-control {
    grid-column: 1 / -1;
  }

  .select-control {
    display: block;
  }

  .select-control > span {
    display: block;
    margin: 0 0 4px 2px;
  }

  .select-control select {
    width: 100%;
    max-width: none;
  }

  .mobile-sort {
    display: block;
  }

  .direction-button {
    align-self: end;
  }

  .table-wrapper {
    display: none;
  }

  .mobile-holdings {
    display: grid;
    gap: 10px;
    margin: 0;
    padding: 12px;
    border-top: 1px solid var(--color-border);
    background: var(--color-surface-subtle);
    list-style: none;
  }

  .mobile-holdings li {
    padding: 14px;
    border: 1px solid var(--color-border);
    border-radius: 12px;
    background: var(--color-surface);
  }

  .mobile-card-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .mobile-card-head > div {
    display: flex;
    min-width: 0;
    flex-direction: column;
  }

  .mobile-card-head strong {
    overflow: hidden;
    font-size: 0.86rem;
    text-overflow: ellipsis;
  }

  .mobile-card-head div span {
    overflow: hidden;
    margin-top: 2px;
    color: var(--color-text-faint);
    font-size: 0.68rem;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mobile-source {
    margin-top: 3px;
    color: var(--color-warning);
    font-size: 0.62rem;
    font-weight: 650;
  }

  .return-pill {
    flex-shrink: 0;
    padding: 4px 7px;
    border-radius: 6px;
    background: var(--color-surface-strong);
    font-size: 0.7rem;
    font-weight: 800;
  }

  .return-pill.positive {
    background: var(--color-positive-soft);
  }

  .return-pill.negative {
    background: var(--color-negative-soft);
  }

  .mobile-holdings dl {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 11px 16px;
    margin: 14px 0 0;
    padding-top: 12px;
    border-top: 1px solid #edf1f5;
  }

  .mobile-holdings dl div {
    min-width: 0;
  }

  .mobile-holdings dt {
    color: var(--color-text-faint);
    font-size: 0.64rem;
  }

  .mobile-holdings dd {
    margin: 2px 0 0;
    overflow: hidden;
    color: var(--color-text);
    font-size: 0.75rem;
    font-weight: 700;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

@media (max-width: 480px) {
  .table-controls {
    grid-template-columns: 1fr 40px;
  }

  .select-control {
    grid-column: 1 / -1;
  }

  .mobile-sort {
    grid-column: 1;
  }

  .direction-button {
    grid-column: 2;
  }
}
</style>
