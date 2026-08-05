<template>
  <section class="mf-table-card" aria-labelledby="mf-table-heading">
    <div class="mf-table-header">
      <div>
        <h2 id="mf-table-heading">Mutual fund holdings</h2>
        <p>{{ resultLabel }}</p>
      </div>
      <label class="mf-search">
        <span class="sr-only">Search funds</span>
        <input
          v-model.trim="searchQuery"
          type="search"
          placeholder="Search scheme or folio"
          autocomplete="off"
        />
      </label>
    </div>

    <div v-if="visibleFunds.length" class="mf-table-wrap">
      <table class="mf-table">
        <thead>
          <tr>
            <th class="col-expand"></th>
            <th class="col-fund">
              <button type="button" @click="setSort('symbol')">
                Fund <span class="sort-ind" :class="{ active: sortKey === 'symbol' }" aria-hidden="true">{{ sortIcon('symbol') }}</span>
              </button>
            </th>
            <th class="col-num">
              <button type="button" @click="setSort('quantity')">
                Units <span class="sort-ind" :class="{ active: sortKey === 'quantity' }" aria-hidden="true">{{ sortIcon('quantity') }}</span>
              </button>
            </th>
            <th class="col-num">
              <button type="button" @click="setSort('last_price')">
                NAV / LTP <span class="sort-ind" :class="{ active: sortKey === 'last_price' }" aria-hidden="true">{{ sortIcon('last_price') }}</span>
              </button>
            </th>
            <th class="col-num">
              <button type="button" @click="setSort('invested')">
                Invested <span class="sort-ind" :class="{ active: sortKey === 'invested' }" aria-hidden="true">{{ sortIcon('invested') }}</span>
              </button>
            </th>
            <th class="col-num">
              <button type="button" @click="setSort('current_value')">
                Current value <span class="sort-ind" :class="{ active: sortKey === 'current_value' }" aria-hidden="true">{{ sortIcon('current_value') }}</span>
              </button>
            </th>
            <th class="col-num">
              <button type="button" @click="setSort('pnl')">
                P&amp;L <span class="sort-ind" :class="{ active: sortKey === 'pnl' }" aria-hidden="true">{{ sortIcon('pnl') }}</span>
              </button>
            </th>
            <th class="col-num">
              <button type="button" @click="setSort('pnl_pct')">
                Return <span class="sort-ind" :class="{ active: sortKey === 'pnl_pct' }" aria-hidden="true">{{ sortIcon('pnl_pct') }}</span>
              </button>
            </th>
            <th class="col-num">
              <button type="button" @click="setSort('day_change_pct')">
                % Day <span class="sort-ind" :class="{ active: sortKey === 'day_change_pct' }" aria-hidden="true">{{ sortIcon('day_change_pct') }}</span>
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-for="fund in visibleFunds" :key="fund.symbol">
            <!-- Main row -->
            <tr
              class="fund-row"
              :class="{ expanded: expandedFund === fund.symbol }"
              @click="toggleExpand(fund.symbol)"
            >
              <td class="col-expand">
                <span class="expand-chevron" aria-hidden="true">
                  {{ expandedFund === fund.symbol ? '▲' : '▼' }}
                </span>
              </td>
              <td class="col-fund">
                <div class="fund-cell">
                  <div class="fund-icon" :style="{ background: iconBg(fund.symbol), color: iconColor(fund.symbol) }">
                    {{ fund.symbol.slice(0, 2) }}
                  </div>
                  <div>
                    <div class="fund-name">{{ fund.symbol }}</div>
                    <div class="fund-meta">
                      {{ fund.exchange }} · {{ fund.accounts.length }} account{{ fund.accounts.length !== 1 ? 's' : '' }}
                      <template v-if="fund.fund_name && fund.fund_name !== fund.symbol"> · {{ fund.fund_name }}</template>
                    </div>
                  </div>
                </div>
              </td>
              <td class="col-num">{{ formatQty(fund.quantity) }}</td>
              <td class="col-num">{{ fmt(fund.last_price) }}</td>
              <td class="col-num">{{ fmt(fund.invested) }}</td>
              <td class="col-num bold">{{ fmt(fund.current_value) }}</td>
              <td class="col-num" :class="pnlCls(fund.pnl)">{{ fmtSigned(fund.pnl) }}</td>
              <td class="col-num">
                <span class="pct-pill" :class="pnlCls(fund.pnl_pct)">{{ fmtPct(fund.pnl_pct) }}</span>
              </td>
              <td class="col-num" :class="pnlCls(fund.day_change_pct)">{{ fmtPct(fund.day_change_pct) }}</td>
            </tr>

            <!-- Drill-down row -->
            <tr v-if="expandedFund === fund.symbol" class="drilldown-row">
              <td :colspan="9" class="drilldown-cell">
                <div class="drilldown">
                  <!-- Header stats -->
                  <div class="dd-header">
                    <div class="dd-title">{{ fund.symbol }} — Position detail</div>
                    <div class="dd-stats">
                      <div class="dd-stat">
                        <div class="dd-label">Total units</div>
                        <div class="dd-value">{{ formatQty(fund.quantity) }}</div>
                      </div>
                      <div class="dd-stat">
                        <div class="dd-label">NAV / LTP</div>
                        <div class="dd-value">{{ fmt(fund.last_price) }}</div>
                      </div>
                      <div class="dd-stat">
                        <div class="dd-label">Total invested</div>
                        <div class="dd-value">{{ fmt(fund.invested) }}</div>
                      </div>
                      <div class="dd-stat">
                        <div class="dd-label">Current value</div>
                        <div class="dd-value">{{ fmt(fund.current_value) }}</div>
                      </div>
                      <div class="dd-stat">
                        <div class="dd-label">Total P&amp;L</div>
                        <div class="dd-value" :class="pnlCls(fund.pnl)">{{ fmtSigned(fund.pnl) }}</div>
                      </div>
                      <div class="dd-stat">
                        <div class="dd-label">Return</div>
                        <div class="dd-value">
                          <span class="pct-pill" :class="pnlCls(fund.pnl_pct)">{{ fmtPct(fund.pnl_pct) }}</span>
                        </div>
                      </div>
                      <div class="dd-stat">
                        <div class="dd-label">Day change</div>
                        <div class="dd-value" :class="pnlCls(fund.day_change_pct)">{{ fmtPct(fund.day_change_pct) }}</div>
                      </div>
                    </div>
                  </div>

                  <!-- Per-account breakdown -->
                  <div class="dd-accounts">
                    <div
                      v-for="acct in fund.accounts"
                      :key="acct.account_name"
                      class="acct-block"
                    >
                      <div class="acct-badge">
                        <span class="acct-dot" :style="{ background: accountColor(acct.account_name) }"></span>
                        <strong>{{ acct.account_name }}</strong>
                        <span class="acct-sub">
                          · {{ formatQty(acct.quantity) }} units
                          · Avg. {{ fmt(acct.average_price) }}
                          <template v-if="acct.folio"> · Folio {{ acct.folio }}</template>
                        </span>
                      </div>
                      <table class="acct-table">
                        <thead>
                          <tr>
                            <th>Account</th>
                            <th class="text-right">Units</th>
                            <th class="text-right">Avg. price</th>
                            <th class="text-right">NAV / LTP</th>
                            <th class="text-right">Invested</th>
                            <th class="text-right">Current value</th>
                            <th class="text-right">P&amp;L</th>
                            <th class="text-right">Return</th>
                            <th class="text-right">% Day</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td>{{ acct.account_name }}</td>
                            <td class="text-right bold">{{ formatQty(acct.quantity) }}</td>
                            <td class="text-right">{{ fmt(acct.average_price) }}</td>
                            <td class="text-right bold">{{ fmt(fund.last_price) }}</td>
                            <td class="text-right">{{ fmt(acct.invested) }}</td>
                            <td class="text-right bold">{{ fmt(acct.current_value) }}</td>
                            <td class="text-right" :class="pnlCls(acct.pnl)">{{ fmtSigned(acct.pnl) }}</td>
                            <td class="text-right">
                              <span class="pct-pill sm" :class="pnlCls(acct.pnl_pct)">{{ fmtPct(acct.pnl_pct) }}</span>
                            </td>
                            <td class="text-right" :class="pnlCls(acct.day_change_pct)">{{ fmtPct(acct.day_change_pct) }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <div v-else class="mf-empty">
      <span aria-hidden="true">—</span>
      <h3>No matching funds</h3>
      <p>Try clearing your search.</p>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  holdings: {
    type: Array,
    required: true
  },
  currency: {
    type: String,
    default: 'INR'
  }
})

const searchQuery = ref('')
const sortKey = ref('current_value')
const sortDir = ref('desc')
const expandedFund = ref(null)

// ── Aggregate raw holdings rows into one entry per tradingsymbol ──
const aggregatedFunds = computed(() => {
  const map = {}
  for (const h of props.holdings) {
    const sym = h.tradingsymbol || h.fund_name || 'Unknown'
    if (!map[sym]) {
      map[sym] = {
        symbol: sym,
        fund_name: h.fund_name || null,
        exchange: h.exchange || 'MF',
        isin: h.isin || null,
        last_price: Number(h.last_price || 0),
        quantity: 0,
        invested: 0,
        current_value: 0,
        pnl: 0,
        day_change_pct: 0,
        accounts: [],
        _dayChangePctSum: 0,
        _acctCount: 0,
      }
    }
    const entry = map[sym]
    const qty = Number(h.quantity || 0)
    const invested = Number(h.current_value || 0) - Number(h.pnl || 0)
    const currentVal = Number(h.current_value || 0)
    const pnl = Number(h.pnl || 0)

    entry.quantity += qty
    entry.invested += invested
    entry.current_value += currentVal
    entry.pnl += pnl
    entry._dayChangePctSum += Number(h.day_change_percentage || 0)
    entry._acctCount++

    entry.accounts.push({
      account_name: h.account_name || 'Account',
      folio: h.folio || null,
      quantity: qty,
      average_price: Number(h.average_price || 0),
      invested,
      current_value: currentVal,
      pnl,
      pnl_pct: Number(h.pnl_percentage || 0),
      day_change_pct: Number(h.day_change_percentage || 0),
    })
  }

  return Object.values(map).map(f => ({
    ...f,
    pnl_pct: f.invested > 0 ? (f.pnl / f.invested) * 100 : 0,
    day_change_pct: f._acctCount > 0 ? f._dayChangePctSum / f._acctCount : 0,
  }))
})

const visibleFunds = computed(() => {
  let funds = aggregatedFunds.value

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    funds = funds.filter(f =>
      f.symbol.toLowerCase().includes(q) ||
      f.accounts.some(a => (a.folio || '').toLowerCase().includes(q) || (a.account_name || '').toLowerCase().includes(q))
    )
  }

  const dir = sortDir.value === 'asc' ? 1 : -1
  funds = funds.slice().sort((a, b) => {
    const va = a[sortKey.value]
    const vb = b[sortKey.value]
    if (typeof va === 'string') return va.localeCompare(vb) * dir
    return ((va || 0) - (vb || 0)) * dir
  })

  return funds
})

const resultLabel = computed(() => {
  const shown = visibleFunds.value.length
  const total = aggregatedFunds.value.length
  return searchQuery.value ? `${shown} of ${total} funds` : `${total} ${total === 1 ? 'fund' : 'funds'}`
})

const toggleExpand = sym => {
  expandedFund.value = expandedFund.value === sym ? null : sym
}

const setSort = key => {
  if (sortKey.value === key) sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc'
  else { sortKey.value = key; sortDir.value = 'desc' }
}

const sortIcon = key => {
  if (sortKey.value !== key) return '↕'
  return sortDir.value === 'desc' ? '↓' : '↑'
}

// ── Formatters ──
const moneyFmt = computed(() =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: props.currency, minimumFractionDigits: 0, maximumFractionDigits: 2 })
)
const fmt = v => moneyFmt.value.format(Number(v || 0))
const formatQty = v => Number(v || 0).toLocaleString('en-IN', { maximumFractionDigits: 4 })
const fmtSigned = v => {
  const n = Number(v || 0)
  return `${n >= 0 ? '+' : '−'}${moneyFmt.value.format(Math.abs(n))}`
}
const fmtPct = v => {
  const n = Number(v || 0)
  return `${n >= 0 ? '+' : '−'}${Math.abs(n).toFixed(2)}%`
}
const pnlCls = v => Number(v || 0) > 0 ? 'positive' : Number(v || 0) < 0 ? 'negative' : 'neutral'

// ── Color helpers ──
const PALETTE = ['#10b981', '#6366f1', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316']
const _hash = s => { let h = 0; for (let i = 0; i < s.length; i++) h = s.charCodeAt(i) + ((h << 5) - h); return Math.abs(h) }
const iconColor = sym => PALETTE[_hash(sym) % PALETTE.length]
const iconBg = sym => iconColor(sym) + '22'

const ACCT_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
const _acctColorCache = {}
let _acctIdx = 0
const accountColor = name => {
  if (!_acctColorCache[name]) _acctColorCache[name] = ACCT_COLORS[_acctIdx++ % ACCT_COLORS.length]
  return _acctColorCache[name]
}
</script>

<style scoped>
.mf-table-card {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.mf-table-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 20px 20px 14px;
  flex-wrap: wrap;
}

.mf-table-header h2 {
  margin: 0;
  font-size: 1.05rem;
  letter-spacing: -0.015em;
  color: var(--color-text);
}

.mf-table-header p {
  margin: 4px 0 0;
  color: var(--color-text-faint);
  font-size: 0.78rem;
}

.mf-search input {
  padding: 7px 12px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 0.83rem;
  min-width: 220px;
  outline: none;
}

.mf-search input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.mf-table-wrap {
  overflow-x: auto;
}

.mf-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.79rem;
}

.mf-table thead th {
  padding: 10px 14px;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-faint);
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
  background: var(--color-surface);
}

.mf-table thead th button {
  all: unset;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  color: inherit;
  font: inherit;
  white-space: nowrap;
}

.mf-table thead th button:hover {
  color: var(--color-text);
}

.col-expand { width: 36px; text-align: center; }
.col-num { text-align: right; }
.col-fund { min-width: 200px; }

.sort-ind { font-size: 0.7rem; opacity: 0.4; }
.sort-ind.active { color: var(--color-primary); opacity: 1; }

/* Fund row */
.fund-row {
  cursor: pointer;
  transition: background 0.12s;
}
.fund-row:hover { background: var(--color-bg); }
.fund-row.expanded { background: var(--color-bg); }

.fund-row td {
  padding: 13px 14px;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-soft);
  white-space: nowrap;
  vertical-align: middle;
}

.expand-chevron {
  font-size: 0.65rem;
  color: var(--color-text-faint);
  transition: transform 0.2s;
}

.fund-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.fund-icon {
  width: 34px; height: 34px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700;
  flex-shrink: 0;
}

.fund-name { color: var(--color-text); font-weight: 700; }
.fund-meta { color: var(--color-text-faint); font-size: 0.68rem; margin-top: 2px; }

.bold { font-weight: 700; color: var(--color-text); }
.positive { color: var(--color-success, #16a34a); }
.negative { color: var(--color-danger, #dc2626); }
.neutral  { color: var(--color-text-soft); }

.pct-pill {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 10px;
  font-weight: 700;
  font-size: 0.75rem;
}
.pct-pill.positive { background: #dcfce7; color: #166534; }
.pct-pill.negative { background: #fee2e2; color: #991b1b; }
.pct-pill.neutral  { background: var(--color-bg); color: var(--color-text-faint); }
.pct-pill.sm { font-size: 0.7rem; padding: 1px 6px; }

/* Drill-down */
.drilldown-row td { padding: 0; border-bottom: 1px solid var(--color-border); }
.drilldown-cell { padding: 0 !important; }

.drilldown {
  padding: 16px 20px 20px;
  background: var(--color-bg);
  border-top: 1px solid var(--color-border);
}

.dd-header {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.dd-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text);
}

.dd-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.dd-stat { text-align: center; }

.dd-label {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-faint);
  margin-bottom: 3px;
}

.dd-value {
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--color-text);
}

/* Account blocks */
.dd-accounts { display: flex; flex-direction: column; gap: 12px; }

.acct-block {
  border: 1px solid var(--color-border);
  border-radius: 10px;
  overflow: hidden;
  background: var(--color-surface);
}

.acct-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--color-border);
  font-size: 0.82rem;
}

.acct-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.acct-sub {
  color: var(--color-text-faint);
  font-weight: 400;
  font-size: 0.76rem;
}

.acct-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.77rem;
}

.acct-table thead th {
  padding: 8px 12px;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-faint);
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
}

.acct-table tbody td {
  padding: 10px 12px;
  color: var(--color-text-soft);
  white-space: nowrap;
}

.text-right { text-align: right; }

/* Empty */
.mf-empty {
  padding: 40px 20px;
  text-align: center;
  color: var(--color-text-faint);
}

.mf-empty h3 { margin: 10px 0 4px; font-size: 0.95rem; color: var(--color-text); }
.mf-empty p  { font-size: 0.82rem; }

.sr-only {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  white-space: nowrap;
  border: 0;
}
</style>
