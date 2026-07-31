<template>
  <div class="page-stack fixed-deposits-page">
    <div class="page-intro">
      <div>
        <p class="eyebrow">Fixed deposits</p>
        <h2>Predictable returns, fully visible</h2>
        <p>Track principal and an accrued simple-interest estimate in INR.</p>
      </div>
      <div class="page-actions">
        <button
          v-if="hasFDHoldings"
          type="button"
          class="secondary-button"
          @click="showImporter = !showImporter"
        >
          {{ showImporter ? 'Close import' : 'Replace deposit register' }}
        </button>
        <button
          v-if="hasFDHoldings"
          type="button"
          class="primary-button"
          :disabled="refreshing || !accountsStore.currentAccount"
          :title="accountsStore.currentAccount ? 'Recalculate the selected member’s deposits' : 'Select Member scope to recalculate deposits'"
          @click="handleRefreshValues"
        >
          <span aria-hidden="true">↻</span>
          {{ refreshing ? 'Recalculating…' : 'Recalculate interest' }}
        </button>
      </div>
    </div>

    <section
      v-if="showImporter || !hasFDHoldings"
      class="import-card"
      aria-labelledby="fd-import-title"
    >
      <div class="import-copy">
        <span class="import-mark" aria-hidden="true">FD</span>
        <div>
          <h2 id="fd-import-title">{{ hasFDHoldings ? 'Replace deposit register' : 'Import fixed deposits' }}</h2>
          <p>Use a complete Excel workbook with one deposit per row. Importing replaces the current fixed-deposit list for the family account you choose.</p>
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
            {{ uploading ? 'Replacing securely…' : hasFDHoldings ? 'Replace and calculate' : 'Import and calculate' }}
          </button>
        </div>

        <div class="format-guide">
          <h3>Required columns</h3>
          <dl>
            <div><dt>Bank Name</dt><dd>HDFC Bank</dd></div>
            <div><dt>Investment Amount</dt><dd>250000</dd></div>
            <div><dt>Investment Date</dt><dd>2025-01-15</dd></div>
            <div><dt>Interest Rate</dt><dd>7.25</dd></div>
            <div><dt>Maturity Date</dt><dd>Optional</dd></div>
          </dl>
          <p class="security-note">
            Files are sent only to the authenticated API. The browser validates file type and size before upload.
          </p>
        </div>
      </div>
    </section>

    <template v-if="hasFDHoldings">
      <PortfolioSummary
        :summary="fdSummary"
        currency="INR"
        value-title="Estimated current value"
        value-subtitle="Simple-interest estimate"
        return-title="Estimated accrued interest"
      />

      <div class="estimate-notice" role="note">
        <span aria-hidden="true">i</span>
        <p>
          <strong>Estimated values.</strong>
          Accrued interest and current value use simple interest from the imported
          principal, rate and investment date. Compounding frequency, payout
          schedules, tax and bank-specific terms are not modelled.
        </p>
      </div>

      <section class="deposit-insights" aria-label="Fixed deposit highlights">
        <article>
          <span>Highest rate</span>
          <strong>{{ highestRate.toFixed(2) }}% p.a.</strong>
          <small>Across imported deposits</small>
        </article>
        <article>
          <span>Bank relationships</span>
          <strong>{{ bankCount }}</strong>
          <small>{{ fdHoldings.length }} total deposits</small>
        </article>
        <article>
          <span>Average age</span>
          <strong>{{ averageAgeDays.toLocaleString('en-IN') }} days</strong>
          <small>Since investment date</small>
        </article>
      </section>

      <div class="charts-grid">
        <ChartPanel
          title="Bank concentration"
          subtitle="Estimated current deposit value by bank"
          :has-data="bankDistributionData.labels.length > 0"
        >
          <PieChart :data="bankDistributionData" />
        </ChartPanel>

        <ChartPanel
          title="Largest deposits"
          subtitle="Top deposits by estimated current value"
          :has-data="topFDsData.labels.length > 0"
        >
          <BarChart :data="topFDsData" horizontal />
        </ChartPanel>
      </div>

      <FixedDepositTable :deposits="fdHoldings" />
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useHoldingsStore } from '@/stores/holdings'
import { useAccountsStore } from '@/stores/accounts'
import { useUiStore } from '@/stores/ui'

import PortfolioSummary from '@/components/dashboard/PortfolioSummary.vue'
import FixedDepositTable from '@/components/dashboard/FixedDepositTable.vue'
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

const fdHoldings = computed(() => holdingsStore.fdHoldings)
const hasFDHoldings = computed(() => fdHoldings.value.length > 0)
const targetAccountId = computed(() => accountsStore.currentAccount || uploadAccountId.value || null)
const canUpload = computed(() => Boolean(selectedFile.value && targetAccountId.value && !uploadError.value))

const selectedAccountName = computed(() => {
  const account = accountsStore.accounts.find(item => Number(item.id) === Number(accountsStore.currentAccount))
  return account?.account_name || `Account ${accountsStore.currentAccount}`
})

const fdSummary = computed(() => holdingsStore.fdSummary)

const parseRate = holding => {
  if (holding.interest_rate !== undefined && holding.interest_rate !== null) {
    return Number(holding.interest_rate) || 0
  }
  const match = String(holding.sector || '').match(/[\d.]+/)
  return match ? Number(match[0]) : 0
}

const highestRate = computed(() => Math.max(0, ...fdHoldings.value.map(parseRate)))
const bankCount = computed(() => new Set(fdHoldings.value.map(holding => holding.tradingsymbol)).size)

const daysElapsed = dateString => {
  if (!dateString) return 0
  const date = new Date(dateString)
  if (Number.isNaN(date.getTime())) return 0
  return Math.max(0, Math.floor((Date.now() - date.getTime()) / 86400000))
}

const averageAgeDays = computed(() => {
  const datedHoldings = fdHoldings.value.filter(holding => holding.purchase_date)
  if (!datedHoldings.length) return 0
  const total = datedHoldings.reduce((sum, holding) => sum + daysElapsed(holding.purchase_date), 0)
  return Math.round(total / datedHoldings.length)
})

const bankDistributionData = computed(() => {
  const banks = fdHoldings.value.reduce((totals, holding) => {
    const bank = holding.tradingsymbol || 'Unknown bank'
    totals[bank] = (totals[bank] || 0) + Number(holding.current_value || 0)
    return totals
  }, {})
  const sorted = Object.entries(banks).sort((left, right) => right[1] - left[1])
  return {
    labels: sorted.map(([bank]) => bank),
    values: sorted.map(([, value]) => value)
  }
})

const topFDsData = computed(() => {
  const deposits = fdHoldings.value
    .slice()
    .sort((left, right) => Number(right.current_value || 0) - Number(left.current_value || 0))
    .slice(0, 8)
  return {
    labels: deposits.map(deposit => deposit.tradingsymbol),
    values: deposits.map(deposit => Number(deposit.current_value || 0)),
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
  if (file.size > MAX_FILE_SIZE) {
    return 'The selected file is larger than 10 MB.'
  }
  return ''
}

const setSelectedFile = file => {
  uploadError.value = validateFile(file)
  selectedFile.value = uploadError.value ? null : file
}

const handleFileSelect = event => {
  setSelectedFile(event.target.files?.[0])
}

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
      : 'Choose the family account that owns these deposits.'
    return
  }

  uploading.value = true
  uploadError.value = ''
  try {
    await holdingsStore.uploadFDHoldings(selectedFile.value, Number(targetAccountId.value))
    try {
      await holdingsStore.loadPortfolio(accountsStore.currentAccount || null)
    } catch {
      uiStore.addNotification({
        type: 'info',
        message: 'Deposits were imported, but the refreshed family view could not be loaded.'
      })
    }
    resetFile()
    showImporter.value = false
    uiStore.addNotification({ type: 'success', message: 'Fixed-deposit register saved successfully.' })
  } catch {
    uploadError.value = holdingsStore.error || 'The deposit file could not be imported.'
  } finally {
    uploading.value = false
  }
}

const handleRefreshValues = async () => {
  if (!accountsStore.currentAccount) {
    uiStore.addNotification({ type: 'info', message: 'Select Member scope before recalculating deposits.' })
    return
  }
  refreshing.value = true
  try {
    await holdingsStore.refreshFDValues(accountsStore.currentAccount)
    uiStore.addNotification({ type: 'success', message: 'Simple-interest estimates recalculated.' })
  } catch {
    uiStore.addNotification({ type: 'error', message: holdingsStore.error || 'Interest recalculation failed.' })
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
  background: var(--color-primary);
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
  color: var(--color-text);
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

.estimate-notice {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  padding: 13px 15px;
  border: 1px solid #d7ccef;
  border-radius: 11px;
  background: #f8f5ff;
  color: #574778;
}

.estimate-notice > span {
  display: grid;
  width: 22px;
  height: 22px;
  flex: 0 0 22px;
  place-items: center;
  border-radius: 50%;
  background: #e8def9;
  font-size: 0.72rem;
  font-weight: 850;
}

.estimate-notice p {
  margin: 0;
  font-size: 0.74rem;
  line-height: 1.5;
}

.deposit-insights {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.deposit-insights article {
  display: flex;
  flex-direction: column;
  padding: 15px 17px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.deposit-insights span {
  color: var(--color-text-faint);
  font-size: 0.66rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.deposit-insights strong {
  margin-top: 4px;
  font-size: 1.03rem;
}

.deposit-insights small {
  margin-top: 2px;
  color: var(--color-text-faint);
  font-size: 0.68rem;
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

  .deposit-insights {
    grid-template-columns: 1fr;
  }
}
</style>
