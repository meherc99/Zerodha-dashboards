<template>
  <section class="deposit-table-card" aria-labelledby="deposit-register-title">
    <div class="register-heading">
      <div>
        <h2 id="deposit-register-title">Fixed deposit register</h2>
        <p>{{ filteredDeposits.length }} of {{ deposits.length }} deposits · values shown in INR</p>
      </div>
      <button v-if="hasFilters" type="button" class="clear-button" @click="clearFilters">
        Clear filters
      </button>
    </div>

    <div class="register-controls">
      <label class="search-field">
        <span>Search</span>
        <input v-model.trim="searchQuery" class="control" type="search" placeholder="Bank or account" />
      </label>
      <label>
        <span>Maturity</span>
        <select v-model="statusFilter" class="control">
          <option value="">All deposits</option>
          <option value="active">Active</option>
          <option value="soon">Due within 90 days</option>
          <option value="matured">Matured</option>
          <option value="open">No maturity date</option>
        </select>
      </label>
      <label>
        <span>Sort by</span>
        <select v-model="sortBy" class="control">
          <option value="current_value">Estimated current value</option>
          <option value="average_price">Principal</option>
          <option value="interest_rate">Interest rate</option>
          <option value="maturity_date">Maturity date</option>
          <option value="tradingsymbol">Bank name</option>
          <option value="account_name">Member</option>
        </select>
      </label>
      <button
        type="button"
        class="direction-button"
        :aria-label="sortDirection === 'desc' ? 'Sort descending; activate for ascending' : 'Sort ascending; activate for descending'"
        @click="sortDirection = sortDirection === 'desc' ? 'asc' : 'desc'"
      >
        <span aria-hidden="true">{{ sortDirection === 'desc' ? '↓' : '↑' }}</span>
      </button>
    </div>

    <template v-if="filteredDeposits.length">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Bank / Scheme</th>
              <th>Member</th>
              <th class="text-right">Principal</th>
              <th>Booked</th>
              <th class="text-right">Rate</th>
              <th>Maturity</th>
              <th class="text-right">Interest earned</th>
              <th class="text-right">Current value</th>
              <th class="text-right">Maturity value</th>
              <th class="text-center">Progress</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="deposit in filteredDeposits" :key="depositKey(deposit)">
              <td>
                <strong>{{ deposit.tradingsymbol || 'Unnamed bank' }}</strong>
                <small v-if="deposit.folio || deposit.sector">{{ deposit.folio || deposit.sector }}</small>
              </td>
              <td>
                <span class="member-tag">{{ deposit.account_name || '—' }}</span>
              </td>
              <td class="text-right number">{{ formatMoney(deposit.average_price) }}</td>
              <td>{{ formatDate(deposit.purchase_date) }}</td>
              <td class="text-right rate">{{ formatRate(deposit) }}</td>
              <td>
                <span>{{ formatDate(deposit.maturity_date) }}</span>
                <span class="maturity-badge" :class="maturityStatus(deposit).value">
                  {{ maturityStatus(deposit).label }}
                </span>
              </td>
              <td class="text-right number positive">{{ formatMoney(deposit.pnl) }}</td>
              <td class="text-right number current">{{ formatMoney(deposit.current_value) }}</td>
              <td class="text-right number">{{ formatMoney(maturityValue(deposit)) }}</td>
              <td class="text-center">
                <div class="progress-wrap">
                  <div class="progress-bar">
                    <div
                      class="progress-fill"
                      :style="{ width: progressPct(deposit) + '%', background: progressColor(deposit) }"
                    ></div>
                  </div>
                  <span class="progress-pct">{{ progressPct(deposit).toFixed(0) }}%</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <ul class="mobile-deposits" aria-label="Filtered fixed deposits">
        <li v-for="deposit in filteredDeposits" :key="`mobile-${depositKey(deposit)}`">
          <div class="mobile-head">
            <div>
              <strong>{{ deposit.tradingsymbol || 'Unnamed bank' }}</strong>
              <span>{{ formatRate(deposit) }} · {{ deposit.account_name }}</span>
            </div>
            <span class="maturity-badge" :class="maturityStatus(deposit).value">
              {{ maturityStatus(deposit).label }}
            </span>
          </div>
          <dl>
            <div><dt>Principal</dt><dd>{{ formatMoney(deposit.average_price) }}</dd></div>
            <div><dt>Current value</dt><dd>{{ formatMoney(deposit.current_value) }}</dd></div>
            <div><dt>Interest earned</dt><dd class="positive">{{ formatMoney(deposit.pnl) }}</dd></div>
            <div><dt>Maturity value</dt><dd>{{ formatMoney(maturityValue(deposit)) }}</dd></div>
            <div><dt>Booked</dt><dd>{{ formatDate(deposit.purchase_date) }}</dd></div>
            <div><dt>Maturity</dt><dd>{{ formatDate(deposit.maturity_date) }}</dd></div>
            <div>
              <dt>Progress</dt>
              <dd>
                <div class="progress-bar" style="width:100%;display:inline-block;vertical-align:middle">
                  <div class="progress-fill" :style="{ width: progressPct(deposit) + '%', background: progressColor(deposit) }"></div>
                </div>
                {{ progressPct(deposit).toFixed(0) }}%
              </dd>
            </div>
          </dl>
        </li>
      </ul>
    </template>

    <div v-else class="empty-register">
      <strong>No matching deposits</strong>
      <p>Try a different bank name or maturity filter.</p>
      <button type="button" class="secondary-button" @click="clearFilters">Clear filters</button>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { safeNumber } from '@/utils/holdings'

const props = defineProps({
  deposits: {
    type: Array,
    required: true
  }
})

const searchQuery = ref('')
const statusFilter = ref('')
const sortBy = ref('current_value')
const sortDirection = ref('desc')

const hasFilters = computed(() => Boolean(searchQuery.value || statusFilter.value))

const rateValue = deposit => {
  if (deposit.interest_rate !== undefined && deposit.interest_rate !== null) {
    return safeNumber(deposit.interest_rate)
  }
  const legacyRate = String(deposit.sector || '').match(/[\d.]+/)
  return legacyRate ? safeNumber(legacyRate[0]) : 0
}

const maturityStatus = deposit => {
  if (!deposit.maturity_date) return { value: 'open', label: 'Open-ended' }
  const maturity = new Date(deposit.maturity_date)
  if (Number.isNaN(maturity.getTime())) return { value: 'open', label: 'Date unavailable' }

  const days = Math.ceil((maturity.getTime() - Date.now()) / 86400000)
  if (days < 0) return { value: 'matured', label: '✓ Matured' }
  if (days <= 90) return { value: 'soon', label: `${days}d left` }
  if (days < 365) return { value: 'active', label: `${days}d left` }
  return { value: 'active', label: `${(days / 365).toFixed(1)}y left` }
}

const maturityValue = deposit => {
  const principal = safeNumber(deposit.average_price)
  const rate = rateValue(deposit)
  if (!principal || !rate || !deposit.purchase_date || !deposit.maturity_date) return 0
  const start = new Date(deposit.purchase_date)
  const end = new Date(deposit.maturity_date)
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return 0
  const tenureYears = Math.max(0, (end.getTime() - start.getTime()) / (365.25 * 86400000))
  return principal + principal * (rate / 100) * tenureYears
}

const progressPct = deposit => {
  if (!deposit.purchase_date || !deposit.maturity_date) return 0
  const start = new Date(deposit.purchase_date)
  const end = new Date(deposit.maturity_date)
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return 0
  const total = end.getTime() - start.getTime()
  if (total <= 0) return 100
  const elapsed = Date.now() - start.getTime()
  return Math.min(100, Math.max(0, (elapsed / total) * 100))
}

const progressColor = deposit => {
  const pct = progressPct(deposit)
  if (pct >= 80) return '#16a34a'
  if (pct >= 50) return '#d97706'
  return '#2563eb'
}

const filteredDeposits = computed(() => {
  const query = searchQuery.value.toLocaleLowerCase()
  const direction = sortDirection.value === 'desc' ? -1 : 1

  return props.deposits
    .filter(deposit => {
      if (statusFilter.value && maturityStatus(deposit).value !== statusFilter.value) return false
      if (!query) return true
      return [
        deposit.tradingsymbol,
        deposit.account_name,
        deposit.account_id
      ].filter(Boolean).some(value => String(value).toLocaleLowerCase().includes(query))
    })
    .slice()
    .sort((leftDeposit, rightDeposit) => {
      let left = sortBy.value === 'interest_rate' ? rateValue(leftDeposit) : leftDeposit[sortBy.value]
      let right = sortBy.value === 'interest_rate' ? rateValue(rightDeposit) : rightDeposit[sortBy.value]

      if (sortBy.value === 'maturity_date') {
        left = left ? new Date(left).getTime() : Number.MAX_SAFE_INTEGER
        right = right ? new Date(right).getTime() : Number.MAX_SAFE_INTEGER
      }

      let comparison
      if (sortBy.value === 'tradingsymbol' || sortBy.value === 'account_name') {
        comparison = String(left || '').localeCompare(String(right || ''), undefined, { sensitivity: 'base' })
      } else {
        comparison = safeNumber(left) - safeNumber(right)
      }
      if (comparison !== 0) return comparison * direction
      return depositKey(leftDeposit).localeCompare(depositKey(rightDeposit))
    })
})

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0
})

const formatMoney = value => moneyFormatter.format(safeNumber(value))
const formatRate = deposit => `${rateValue(deposit).toFixed(2)}% p.a.`
const formatDate = value => {
  if (!value) return 'Not provided'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Not provided'
  return new Intl.DateTimeFormat('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  }).format(date)
}

const depositKey = deposit => String(
  deposit.id || deposit.holding_key || `${deposit.account_id}-${deposit.tradingsymbol}-${deposit.purchase_date}`
)

const clearFilters = () => {
  searchQuery.value = ''
  statusFilter.value = ''
}
</script>

<style scoped>
.deposit-table-card {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.register-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 20px 14px;
}

.register-heading h2 {
  margin: 0;
  font-size: 1.05rem;
}

.register-heading p {
  margin: 4px 0 0;
  color: var(--color-text-faint);
  font-size: 0.75rem;
}

.clear-button {
  padding: 4px 0;
  border: 0;
  background: transparent;
  color: var(--color-primary-dark);
  font-size: 0.75rem;
  font-weight: 750;
}

.register-controls {
  display: grid;
  grid-template-columns: minmax(200px, 1fr) auto auto 40px;
  align-items: end;
  gap: 9px;
  padding: 0 20px 18px;
}

.register-controls label > span {
  display: block;
  margin: 0 0 4px 2px;
  color: var(--color-text-faint);
  font-size: 0.68rem;
  font-weight: 750;
}

.register-controls .control {
  width: 100%;
  font-size: 0.78rem;
}

.direction-button {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border: 1px solid var(--color-border-strong);
  border-radius: 10px;
  background: var(--color-surface);
  font-weight: 800;
}

.table-scroll {
  overflow-x: auto;
  border-top: 1px solid var(--color-border);
}

table {
  width: 100%;
  min-width: 900px;
  border-collapse: collapse;
}

thead {
  background: var(--color-surface-subtle);
}

th {
  padding: 11px 14px;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-faint);
  font-size: 0.67rem;
  letter-spacing: 0.045em;
  text-align: left;
  text-transform: uppercase;
}

td {
  padding: 13px 14px;
  border-bottom: 1px solid #edf1f5;
  color: var(--color-text-soft);
  font-size: 0.77rem;
  white-space: nowrap;
}

tbody tr:last-child td {
  border-bottom: 0;
}

td strong {
  display: block;
  color: var(--color-text);
  font-size: 0.8rem;
}

td small {
  color: var(--color-text-faint);
  font-size: 0.65rem;
}

.number {
  font-variant-numeric: tabular-nums;
}

.current {
  color: var(--color-text);
  font-weight: 800;
}

.rate {
  color: var(--color-primary-dark);
  font-weight: 750;
}

.member-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 8px;
  background: var(--color-surface-subtle, #f3f4f6);
  color: var(--color-text-soft);
  font-size: 0.73rem;
  font-weight: 650;
  white-space: nowrap;
}

.text-center { text-align: center; }

.progress-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
  justify-content: center;
}

.progress-bar {
  width: 64px;
  height: 6px;
  background: var(--color-border, #e5e7eb);
  border-radius: 3px;
  overflow: hidden;
  flex-shrink: 0;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}

.progress-pct {
  color: var(--color-text-faint);
  font-size: 0.68rem;
  white-space: nowrap;
}

.maturity-badge {
  display: inline-flex;
  margin-left: 6px;
  padding: 3px 6px;
  border-radius: 6px;
  background: var(--color-surface-strong);
  color: var(--color-text-soft);
  font-size: 0.62rem;
  font-weight: 750;
}

.maturity-badge.soon {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}

.maturity-badge.matured {
  background: var(--color-negative-soft);
  color: var(--color-negative);
}

.maturity-badge.active {
  background: var(--color-positive-soft);
  color: var(--color-positive);
}

.mobile-deposits {
  display: none;
}

.empty-register {
  display: flex;
  min-height: 210px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  border-top: 1px solid var(--color-border);
}

.empty-register p {
  margin: 3px 0 14px;
  color: var(--color-text-soft);
  font-size: 0.78rem;
}

@media (max-width: 760px) {
  .register-heading {
    padding: 17px 15px 13px;
  }

  .register-controls {
    grid-template-columns: 1fr 40px;
    padding: 0 15px 15px;
  }

  .search-field,
  .register-controls label:nth-child(2) {
    grid-column: 1 / -1;
  }

  .table-scroll {
    display: none;
  }

  .mobile-deposits {
    display: grid;
    gap: 10px;
    margin: 0;
    padding: 12px;
    border-top: 1px solid var(--color-border);
    background: var(--color-surface-subtle);
    list-style: none;
  }

  .mobile-deposits li {
    padding: 14px;
    border: 1px solid var(--color-border);
    border-radius: 12px;
    background: var(--color-surface);
  }

  .mobile-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
  }

  .mobile-head > div {
    display: flex;
    min-width: 0;
    flex-direction: column;
  }

  .mobile-head strong {
    font-size: 0.86rem;
  }

  .mobile-head div span {
    margin-top: 2px;
    color: var(--color-text-faint);
    font-size: 0.67rem;
  }

  .mobile-head .maturity-badge {
    flex: 0 0 auto;
    margin: 0;
  }

  dl {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 11px 16px;
    margin: 13px 0 0;
    padding-top: 12px;
    border-top: 1px solid #edf1f5;
  }

  dt {
    color: var(--color-text-faint);
    font-size: 0.63rem;
  }

  dd {
    margin: 2px 0 0;
    color: var(--color-text);
    font-size: 0.75rem;
    font-weight: 750;
  }
}
</style>
