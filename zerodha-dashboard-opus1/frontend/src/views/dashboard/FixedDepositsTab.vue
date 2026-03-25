<template>
  <div class="fixed-deposits-tab">
    <!-- Upload Section (shown when no FD holdings exist) -->
    <div v-if="!hasFDHoldings && !holdingsStore.loading" class="upload-section">
      <div class="upload-card">
        <h3>🏦 Upload Your Fixed Deposit Details</h3>
        <p class="upload-description">
          Upload an Excel file (.xlsx) with your fixed deposit details.
          Interest will be calculated automatically based on the current date.
        </p>

        <div class="file-upload-area" @dragover.prevent @drop.prevent="handleDrop">
          <input
            ref="fileInput"
            type="file"
            accept=".xlsx,.xls"
            @change="handleFileSelect"
            style="display: none"
          />

          <div class="upload-prompt">
            <span class="upload-icon">📁</span>
            <p>Drag and drop your Excel file here, or</p>
            <button @click="$refs.fileInput.click()" class="select-file-btn">
              Select File
            </button>
          </div>

          <div v-if="selectedFile" class="selected-file">
            <span>📄 {{ selectedFile.name }}</span>
            <button @click="handleUpload" :disabled="uploading" class="upload-btn">
              {{ uploading ? 'Uploading...' : 'Upload & Calculate Returns' }}
            </button>
          </div>
        </div>

        <div class="upload-help">
          <h4>File Format Requirements:</h4>
          <ul>
            <li><strong>Bank Name</strong> - Name of the bank (e.g., HDFC, SBI, ICICI)</li>
            <li><strong>Investment Amount</strong> - Principal amount invested</li>
            <li><strong>Investment Date</strong> - Date of FD booking (YYYY-MM-DD)</li>
            <li><strong>Interest Rate</strong> - Annual interest rate (e.g., 7.5 for 7.5%)</li>
            <li><strong>Maturity Date</strong> - Optional, maturity date of FD</li>
          </ul>
          <p class="note">💡 Interest is calculated using simple interest: P × R × T / 100</p>
        </div>
      </div>
    </div>

    <!-- Holdings Display (shown when FD holdings exist) -->
    <div v-else>
      <!-- Summary Cards with Refresh Button -->
      <div class="summary-header">
        <div class="summary-cards">
          <div class="summary-card">
            <div class="card-label">Total Investment</div>
            <div class="card-value">₹{{ formatCurrency(holdingsStore.fdSummary.total_investment) }}</div>
          </div>
          <div class="summary-card">
            <div class="card-label">Current Value</div>
            <div class="card-value">₹{{ formatCurrency(holdingsStore.fdSummary.current_value) }}</div>
          </div>
          <div class="summary-card">
            <div class="card-label">Total Interest Earned</div>
            <div class="card-value positive">₹{{ formatCurrency(holdingsStore.fdSummary.total_interest) }}</div>
          </div>
          <div class="summary-card">
            <div class="card-label">Average Return</div>
            <div class="card-value">{{ holdingsStore.fdSummary.total_interest_percentage.toFixed(2) }}%</div>
          </div>
        </div>
        <button @click="handleRefreshValues" :disabled="refreshing" class="refresh-btn">
          <span v-if="!refreshing">🔄 Recalculate Interest</span>
          <span v-else>Calculating...</span>
        </button>
      </div>

      <!-- FD Holdings Table -->
      <div class="fd-table-card">
        <h3>Fixed Deposits</h3>
        <div class="table-responsive">
          <table class="fd-table">
            <thead>
              <tr>
                <th>Bank Name</th>
                <th>Investment Amount</th>
                <th>Investment Date</th>
                <th>Interest Rate</th>
                <th>Days Elapsed</th>
                <th>Interest Earned</th>
                <th>Current Value</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="fd in sortedFDs" :key="fd.id">
                <td class="bank-name">{{ fd.tradingsymbol }}</td>
                <td>₹{{ formatCurrency(fd.average_price) }}</td>
                <td>{{ formatDate(fd.purchase_date) }}</td>
                <td class="interest-rate">{{ fd.sector }}</td>
                <td>{{ calculateDaysElapsed(fd.purchase_date) }} days</td>
                <td class="interest-earned">₹{{ formatCurrency(fd.pnl) }}</td>
                <td class="current-value">₹{{ formatCurrency(fd.current_value) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Charts Row -->
      <div class="charts-row">
        <div class="chart-card">
          <h3>Bank-wise Distribution</h3>
          <PieChart v-if="bankDistributionData.labels.length" :data="bankDistributionData" />
          <div v-else class="empty-chart">No distribution data</div>
        </div>

        <div class="chart-card">
          <h3>Top Fixed Deposits by Value</h3>
          <BarChart v-if="topFDsData.labels.length" :data="topFDsData" />
          <div v-else class="empty-chart">No FD data</div>
        </div>
      </div>

      <!-- Re-upload Option -->
      <div class="reupload-section">
        <button @click="showUploadAgain" class="secondary-btn">
          Upload New FD Records
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useHoldingsStore } from '@/stores/holdings'
import { useAccountsStore } from '@/stores/accounts'

import PieChart from '@/components/charts/PieChart.vue'
import BarChart from '@/components/charts/BarChart.vue'

const holdingsStore = useHoldingsStore()
const accountsStore = useAccountsStore()

const fileInput = ref(null)
const selectedFile = ref(null)
const uploading = ref(false)
const refreshing = ref(false)

const hasFDHoldings = computed(() => holdingsStore.fdHoldings.length > 0)

const sortedFDs = computed(() => {
  return [...holdingsStore.fdHoldings].sort((a, b) => b.current_value - a.current_value)
})

const bankDistributionData = computed(() => {
  const fds = holdingsStore.fdHoldings
  return {
    labels: fds.map(fd => fd.tradingsymbol),
    values: fds.map(fd => fd.current_value)
  }
})

const topFDsData = computed(() => {
  const fds = [...holdingsStore.fdHoldings]
    .sort((a, b) => b.current_value - a.current_value)
    .slice(0, 10)
  return {
    labels: fds.map(fd => fd.tradingsymbol),
    values: fds.map(fd => fd.current_value),
    label: 'Current Value'
  }
})

const formatCurrency = (value) => {
  return new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value || 0)
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

const calculateDaysElapsed = (investmentDate) => {
  if (!investmentDate) return 0
  const start = new Date(investmentDate)
  const today = new Date()
  const diffTime = Math.abs(today - start)
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  return diffDays
}

const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    selectedFile.value = file
  }
}

const handleDrop = (event) => {
  const file = event.dataTransfer.files[0]
  if (file && (file.name.endsWith('.xlsx') || file.name.endsWith('.xls'))) {
    selectedFile.value = file
  } else {
    alert('Please drop an Excel file (.xlsx)')
  }
}

const handleUpload = async () => {
  if (!selectedFile.value) return

  uploading.value = true
  try {
    const accountId = accountsStore.accounts[0]?.id || 1

    await holdingsStore.uploadFDHoldings(selectedFile.value, accountId)

    alert('Fixed deposits uploaded and interest calculated successfully!')

    selectedFile.value = null
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  } catch (error) {
    alert(error.message || 'Failed to upload FD records')
  } finally {
    uploading.value = false
  }
}

const handleRefreshValues = async () => {
  refreshing.value = true
  try {
    const accountId = accountsStore.accounts[0]?.id
    await holdingsStore.refreshFDValues(accountId)

    console.log('FD interest values recalculated successfully!')
  } catch (error) {
    console.error('Failed to refresh FD values', error)
  } finally {
    refreshing.value = false
  }
}

const showUploadAgain = () => {
  fileInput.value?.click()
}

// Auto-refresh values on component mount
onMounted(async () => {
  if (hasFDHoldings.value) {
    await handleRefreshValues()
  }
})
</script>

<style scoped>
.fixed-deposits-tab {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.upload-section {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.upload-card {
  background: white;
  border-radius: 8px;
  padding: 40px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  max-width: 600px;
  width: 100%;
}

.upload-card h3 {
  margin: 0 0 10px 0;
  font-size: 24px;
  color: #111827;
}

.upload-description {
  color: #6b7280;
  margin-bottom: 30px;
  line-height: 1.5;
}

.file-upload-area {
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  margin-bottom: 30px;
  transition: all 0.2s;
}

.file-upload-area:hover {
  border-color: #3b82f6;
  background: #f9fafb;
}

.upload-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
}

.upload-icon {
  font-size: 48px;
}

.select-file-btn {
  padding: 10px 24px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.select-file-btn:hover {
  background: #2563eb;
}

.selected-file {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
  align-items: center;
}

.upload-btn {
  padding: 10px 24px;
  background: #10b981;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-btn:hover:not(:disabled) {
  background: #059669;
}

.upload-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.upload-help {
  background: #f9fafb;
  padding: 20px;
  border-radius: 6px;
}

.upload-help h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #111827;
}

.upload-help ul {
  margin: 0 0 10px 0;
  padding-left: 20px;
  color: #6b7280;
  font-size: 14px;
  line-height: 1.8;
}

.upload-help .note {
  margin: 15px 0 0 0;
  padding: 10px;
  background: #eff6ff;
  border-left: 3px solid #3b82f6;
  color: #1e40af;
  font-size: 13px;
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  flex-wrap: wrap;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  flex: 1;
}

.summary-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.card-label {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 8px;
  font-weight: 500;
}

.card-value {
  font-size: 24px;
  font-weight: 700;
  color: #111827;
}

.card-value.positive {
  color: #10b981;
}

.refresh-btn {
  padding: 10px 20px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  height: fit-content;
}

.refresh-btn:hover:not(:disabled) {
  background: #2563eb;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.fd-table-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.fd-table-card h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #111827;
}

.table-responsive {
  overflow-x: auto;
}

.fd-table {
  width: 100%;
  border-collapse: collapse;
}

.fd-table thead {
  background: #f9fafb;
}

.fd-table th {
  padding: 12px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  border-bottom: 2px solid #e5e7eb;
}

.fd-table td {
  padding: 12px;
  font-size: 14px;
  color: #111827;
  border-bottom: 1px solid #e5e7eb;
}

.fd-table tbody tr:hover {
  background: #f9fafb;
}

.bank-name {
  font-weight: 600;
  color: #1f2937;
}

.interest-rate {
  color: #3b82f6;
  font-weight: 600;
}

.interest-earned {
  color: #10b981;
  font-weight: 600;
}

.current-value {
  font-weight: 700;
  color: #111827;
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

.chart-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chart-card h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #111827;
}

.empty-chart {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #9ca3af;
  font-size: 14px;
}

.reupload-section {
  text-align: center;
  padding: 20px;
}

.secondary-btn {
  padding: 10px 20px;
  background: white;
  color: #3b82f6;
  border: 2px solid #3b82f6;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.secondary-btn:hover {
  background: #eff6ff;
}

@media (max-width: 768px) {
  .fixed-deposits-tab {
    padding: 15px;
  }

  .upload-card {
    padding: 20px;
  }

  .summary-cards {
    grid-template-columns: 1fr;
  }

  .charts-row {
    grid-template-columns: 1fr;
  }

  .table-responsive {
    overflow-x: scroll;
  }
}
</style>
