<template>
  <div class="page-stack us-stocks-page">
    <div class="page-intro">
      <div>
        <p class="eyebrow">US equities</p>
        <h2>Your foreign portfolio, in USD</h2>
        <p>US positions stay separate from INR totals, with price refreshes performed only when you request them.</p>
      </div>
      <div class="page-actions">
        <span class="status-chip">USD portfolio</span>
        <button
          v-if="hasUSHoldings"
          type="button"
          class="secondary-button"
          @click="showImporter = !showImporter"
        >
          {{ showImporter ? 'Close import' : 'Replace US holdings' }}
        </button>
        <button
          v-if="hasUSHoldings"
          type="button"
          class="primary-button"
          :disabled="refreshing || !accountsStore.currentAccount"
          :title="accountsStore.currentAccount ? 'Refresh the selected member’s US prices' : 'Select Member scope to refresh prices'"
          @click="handleRefreshPrices"
        >
          <span aria-hidden="true">↻</span>
          {{ refreshing ? 'Refreshing…' : 'Refresh USD prices' }}
        </button>
      </div>
    </div>

    <section
      v-if="showImporter || !hasUSHoldings"
      class="import-card"
      aria-labelledby="us-import-title"
    >
      <div class="import-copy">
        <span class="import-mark" aria-hidden="true">US</span>
        <div>
          <h2 id="us-import-title">{{ hasUSHoldings ? 'Replace US holdings' : 'Import US holdings' }}</h2>
          <p>Upload a complete workbook for one family member. Importing replaces that account’s current US positions; prices and values are interpreted as USD.</p>
        </div>
      </div>

      <div class="import-layout">
        <div>
          <label v-if="!accountsStore.currentAccount" class="account-field">
            <span>Destination account</span>
            <select v-model="uploadAccountId" class="control" required>
              <option value="" disabled>Select a family member</option>
              <option
                v-for="account in accountsStore.activeAccounts"
                :key="account.id"
                :value="Number(account.id)"
              >
                {{ account.account_name || `Account ${account.id}` }}
              </option>
            </select>
          </label>
          <div v-else class="scope-confirmation">
            <span>Destination account</span>
            <strong>{{ selectedAccountName }}</strong>
          </div>

          <div
            class="drop-zone"
            :class="{ active: dragActive, invalid: uploadError }"
            @dragenter.prevent="dragActive = true"
            @dragover.prevent="dragActive = true"
            @dragleave.prevent="dragActive = false"
            @drop.prevent="handleDrop"
          >
            <input
              ref="fileInput"
              class="sr-only"
              type="file"
              accept=".xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
              @change="handleFileSelect"
            />
            <span class="file-icon" aria-hidden="true">XL</span>
            <strong>{{ selectedFile ? selectedFile.name : 'Choose or drop an Excel file' }}</strong>
            <small>{{ selectedFile ? formatFileSize(selectedFile.size) : 'XLSX or XLS · maximum 10 MB' }}</small>
            <button type="button" class="secondary-button" @click="fileInput?.click()">
              {{ selectedFile ? 'Choose another file' : 'Choose file' }}
            </button>
          </div>
          <p v-if="uploadError" class="upload-error" role="alert">{{ uploadError }}</p>

          <button
            type="button"
            class="primary-button upload-button"
            :disabled="!canUpload || uploading"
            @click="handleUpload"
          >
            {{ uploading ? 'Replacing securely…' : hasUSHoldings ? 'Replace and fetch prices' : 'Import and fetch prices' }}
          </button>
        </div>

        <div class="format-guide">
          <h3>Workbook columns</h3>
          <dl>
            <div><dt>Symbol</dt><dd>AAPL</dd></div>
            <div><dt>Quantity</dt><dd>10</dd></div>
            <div><dt>Average Price</dt><dd>182.50</dd></div>
            <div><dt>Purchase Date</dt><dd>Optional</dd></div>
          </dl>
          <p class="security-note">Uploads use the authenticated API and are assigned only to the account shown here.</p>
        </div>
      </div>
    </section>

    <template v-if="hasUSHoldings">
      <PortfolioSummary :summary="holdingsStore.usSummary" currency="USD" />

      <div class="currency-notice">
        <span aria-hidden="true">$</span>
        <p>
          <strong>No silent currency conversion.</strong>
          Every value on this page is shown in USD and excluded from the INR overview total.
          <template v-if="atCostCount">
            {{ atCostCount }} {{ atCostCount === 1 ? 'position is' : 'positions are' }} shown at import cost because a market quote was unavailable.
          </template>
          Quote source and price date are shown with each holding.
        </p>
      </div>

      <div class="charts-grid">
        <ChartPanel
          title="US stock allocation"
          subtitle="Largest positions by current USD value"
          :has-data="allocationData.labels.length > 0"
        >
          <PieChart :data="allocationData" currency="USD" />
        </ChartPanel>

        <ChartPanel
          title="Largest positions"
          subtitle="Top holdings by current USD value"
          :has-data="topHoldingsData.labels.length > 0"
        >
          <BarChart :data="topHoldingsData" currency="USD" horizontal />
        </ChartPanel>
      </div>

      <HoldingsTable
        :holdings="holdingsStore.usHoldings"
        title="US stock holdings"
        subtitle="Values shown in USD"
        currency="USD"
        empty-title="No US stocks"
      />
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useHoldingsStore } from '@/stores/holdings'
import { useAccountsStore } from '@/stores/accounts'
import { useUiStore } from '@/stores/ui'

import PortfolioSummary from '@/components/dashboard/PortfolioSummary.vue'
import HoldingsTable from '@/components/dashboard/HoldingsTable.vue'
import ChartPanel from '@/components/dashboard/ChartPanel.vue'
import PieChart from '@/components/charts/PieChart.vue'
import BarChart from '@/components/charts/BarChart.vue'

const MAX_FILE_SIZE = 10 * 1024 * 1024
const VALID_EXTENSIONS = ['.xlsx', '.xls']

const holdingsStore = useHoldingsStore()
const accountsStore = useAccountsStore()
const uiStore = useUiStore()

const fileInput = ref(null)
const selectedFile = ref(null)
const uploadAccountId = ref('')
const uploading = ref(false)
const refreshing = ref(false)
const dragActive = ref(false)
const showImporter = ref(false)
const uploadError = ref('')

const hasUSHoldings = computed(() => holdingsStore.usHoldings.length > 0)
const atCostCount = computed(() => {
  return holdingsStore.usHoldings.filter(holding => {
    const source = String(holding.source || '').toLocaleLowerCase()
    return source === 'cost_basis' || source.includes('at_cost')
  }).length
})
const targetAccountId = computed(() => accountsStore.currentAccount || uploadAccountId.value || null)
const canUpload = computed(() => Boolean(selectedFile.value && targetAccountId.value && !uploadError.value))

const selectedAccountName = computed(() => {
  const account = accountsStore.accounts.find(item => Number(item.id) === Number(accountsStore.currentAccount))
  return account?.account_name || `Account ${accountsStore.currentAccount}`
})

const sortedHoldings = computed(() => {
  return holdingsStore.usHoldings
    .slice()
    .sort((left, right) => Number(right.current_value || 0) - Number(left.current_value || 0))
})

const allocationData = computed(() => {
  const holdings = sortedHoldings.value.slice(0, 8)
  return {
    labels: holdings.map(holding => holding.tradingsymbol),
    values: holdings.map(holding => Number(holding.current_value || 0))
  }
})

const topHoldingsData = computed(() => {
  const holdings = sortedHoldings.value.slice(0, 8)
  return {
    labels: holdings.map(holding => holding.tradingsymbol),
    values: holdings.map(holding => Number(holding.current_value || 0)),
    label: 'Current value'
  }
})

watch(() => accountsStore.currentAccount, accountId => {
  uploadAccountId.value = accountId || ''
})

const validateFile = file => {
  if (!file) return 'Choose an Excel file to continue.'
  const lowerName = file.name.toLocaleLowerCase()
  if (!VALID_EXTENSIONS.some(extension => lowerName.endsWith(extension))) {
    return 'Only .xlsx and .xls files are supported.'
  }
  if (file.size > MAX_FILE_SIZE) return 'The selected file is larger than 10 MB.'
  return ''
}

const setSelectedFile = file => {
  uploadError.value = validateFile(file)
  selectedFile.value = uploadError.value ? null : file
}

const handleFileSelect = event => setSelectedFile(event.target.files?.[0])
const handleDrop = event => {
  dragActive.value = false
  setSelectedFile(event.dataTransfer.files?.[0])
}

const resetFile = () => {
  selectedFile.value = null
  uploadError.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

const handleUpload = async () => {
  if (!canUpload.value) {
    uploadError.value = targetAccountId.value
      ? 'Choose a valid Excel file to continue.'
      : 'Choose the family account that owns these holdings.'
    return
  }

  uploading.value = true
  uploadError.value = ''
  try {
    await holdingsStore.uploadUSHoldings(selectedFile.value, Number(targetAccountId.value))
    try {
      await holdingsStore.loadPortfolio(accountsStore.currentAccount || null)
    } catch {
      uiStore.addNotification({
        type: 'info',
        message: 'US holdings were imported, but the refreshed family view could not be loaded.'
      })
    }
    resetFile()
    showImporter.value = false
    uiStore.addNotification({ type: 'success', message: 'US holdings list saved successfully.' })
  } catch {
    uploadError.value = holdingsStore.error || 'The holdings file could not be imported.'
  } finally {
    uploading.value = false
  }
}

const handleRefreshPrices = async () => {
  if (!accountsStore.currentAccount) {
    uiStore.addNotification({ type: 'info', message: 'Select Member scope before refreshing US prices.' })
    return
  }
  refreshing.value = true
  try {
    const result = await holdingsStore.refreshUSPrices(accountsStore.currentAccount)
    if (!result) return

    if (result.status === 'partial') {
      uiStore.addNotification({
        type: 'info',
        message: (
          `${result.updated_count} US prices were refreshed, but `
          + `${result.accounts_failed || 0} account refresh failed.`
        )
      })
    } else {
      uiStore.addNotification({
        type: 'success',
        message: `${result.updated_count} US prices refreshed.`
      })
    }
  } catch {
    uiStore.addNotification({ type: 'error', message: holdingsStore.error || 'Price refresh failed.' })
  } finally {
    refreshing.value = false
  }
}

const formatFileSize = bytes => {
  if (!bytes) return '0 KB'
  return bytes >= 1048576
    ? `${(bytes / 1048576).toFixed(1)} MB`
    : `${(bytes / 1024).toFixed(1)} KB`
}
</script>

<style scoped>
.page-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 9px;
}

.import-card {
  padding: 22px;
  border: 1px solid #cbd9f7;
  border-radius: var(--radius-lg);
  background: linear-gradient(145deg, #fff, #f5f8ff);
  box-shadow: var(--shadow-sm);
}

.import-copy {
  display: flex;
  align-items: flex-start;
  gap: 13px;
  margin-bottom: 20px;
}

.import-mark {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  place-items: center;
  border-radius: 12px;
  background: #0c7159;
  color: #fff;
  font-size: 0.7rem;
  font-weight: 850;
}

.import-copy h2 {
  margin: 0;
  font-size: 1.05rem;
}

.import-copy p {
  max-width: 700px;
  margin: 4px 0 0;
  color: var(--color-text-soft);
  font-size: 0.8rem;
}

.import-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(270px, 0.7fr);
  gap: 20px;
}

.account-field,
.scope-confirmation {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.account-field > span,
.scope-confirmation > span {
  color: var(--color-text-soft);
  font-size: 0.75rem;
  font-weight: 750;
}

.account-field select {
  min-width: 220px;
}

.scope-confirmation strong {
  font-size: 0.8rem;
}

.drop-zone {
  display: flex;
  min-height: 188px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  padding: 22px;
  border: 1.5px dashed var(--color-border-strong);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.78);
  text-align: center;
  transition: border-color 160ms ease, background 160ms ease;
}

.drop-zone.active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.drop-zone.invalid {
  border-color: var(--color-negative);
}

.file-icon {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 10px;
  background: #e8f1e9;
  color: #28713a;
  font-size: 0.65rem;
  font-weight: 850;
}

.drop-zone strong {
  max-width: 90%;
  margin-top: 9px;
  overflow: hidden;
  font-size: 0.84rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.drop-zone small {
  margin: 2px 0 11px;
  color: var(--color-text-faint);
  font-size: 0.69rem;
}

.upload-error {
  margin: 7px 0 0;
  color: var(--color-negative);
  font-size: 0.75rem;
  font-weight: 650;
}

.upload-button {
  width: 100%;
  margin-top: 12px;
}

.format-guide {
  padding: 17px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-surface);
}

.format-guide h3 {
  margin: 0 0 10px;
  font-size: 0.85rem;
}

.format-guide dl {
  margin: 0;
}

.format-guide dl div {
  display: flex;
  justify-content: space-between;
  gap: 15px;
  padding: 6px 0;
  border-bottom: 1px solid #edf1f5;
  font-size: 0.7rem;
}

.format-guide dt {
  color: var(--color-text-soft);
  font-weight: 750;
}

.format-guide dd {
  margin: 0;
  color: var(--color-text-faint);
}

.security-note {
  margin: 12px 0 0;
  padding: 9px;
  border-radius: 8px;
  background: var(--color-positive-soft);
  color: #336b59;
  font-size: 0.67rem;
}

.currency-notice {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 15px;
  border: 1px solid #c9eadf;
  border-radius: 12px;
  background: var(--color-positive-soft);
}

.currency-notice > span {
  display: grid;
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  place-items: center;
  border-radius: 50%;
  background: #fff;
  color: var(--color-positive);
  font-weight: 850;
}

.currency-notice p {
  margin: 0;
  color: #376a5a;
  font-size: 0.75rem;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

@media (max-width: 900px) {
  .import-layout,
  .charts-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 620px) {
  .page-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .page-actions button {
    flex: 1;
  }

  .import-card {
    padding: 16px;
  }

  .account-field,
  .scope-confirmation {
    align-items: stretch;
    flex-direction: column;
  }

  .account-field select {
    width: 100%;
    min-width: 0;
  }
}
</style>
