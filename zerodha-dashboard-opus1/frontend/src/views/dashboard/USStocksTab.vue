<template>
  <div class="us-stocks-tab">
    <!-- Upload Section (shown when no US holdings exist) -->
    <div v-if="!hasUSHoldings && !holdingsStore.loading" class="upload-section">
      <div class="upload-card">
        <h3>📤 Upload Your US Stock Holdings</h3>
        <p class="upload-description">
          Upload an Excel file (.xlsx) with your US stock holdings to get started.
          Required columns: Symbol, Quantity, Average Price
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
              {{ uploading ? 'Uploading...' : 'Upload & Fetch Prices' }}
            </button>
          </div>
        </div>

        <div class="upload-help">
          <h4>File Format Requirements:</h4>
          <ul>
            <li><strong>Symbol</strong> - Stock ticker (e.g., AAPL, TSLA)</li>
            <li><strong>Quantity</strong> - Number of shares</li>
            <li><strong>Average Price</strong> - Average purchase price per share</li>
            <li><strong>Purchase Date</strong> - Optional, date of purchase</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Holdings Display (shown when US holdings exist) -->
    <div v-else>
      <!-- Summary Cards with Refresh Button -->
      <div class="summary-header">
        <PortfolioSummary :summary="holdingsStore.usSummary" title="US Stocks Summary" />
        <button @click="handleRefreshPrices" :disabled="refreshing" class="refresh-prices-btn">
          <span v-if="!refreshing">🔄 Refresh Prices</span>
          <span v-else>Refreshing...</span>
        </button>
      </div>

      <!-- Charts Row -->
      <div class="charts-row">
        <div class="chart-card">
          <h3>US Stock Allocation</h3>
          <PieChart v-if="allocationData.labels.length" :data="allocationData" />
          <div v-else class="empty-chart">No allocation data</div>
        </div>

        <div class="chart-card">
          <h3>Top Holdings</h3>
          <BarChart v-if="topHoldingsData.labels.length" :data="topHoldingsData" />
          <div v-else class="empty-chart">No holdings data</div>
        </div>
      </div>

      <!-- Holdings Table -->
      <HoldingsTable :holdings="holdingsStore.usHoldings" />

      <!-- Re-upload Option -->
      <div class="reupload-section">
        <button @click="showUploadAgain" class="secondary-btn">
          Upload New Holdings File
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useHoldingsStore } from '@/stores/holdings'
import { useAccountsStore } from '@/stores/accounts'

import PortfolioSummary from '@/components/dashboard/PortfolioSummary.vue'
import HoldingsTable from '@/components/dashboard/HoldingsTable.vue'
import PieChart from '@/components/charts/PieChart.vue'
import BarChart from '@/components/charts/BarChart.vue'

const holdingsStore = useHoldingsStore()
const accountsStore = useAccountsStore()

const fileInput = ref(null)
const selectedFile = ref(null)
const uploading = ref(false)
const refreshing = ref(false)

const hasUSHoldings = computed(() => holdingsStore.usHoldings.length > 0)

const allocationData = computed(() => {
  const holdings = holdingsStore.usHoldings.slice(0, 10) // Top 10
  return {
    labels: holdings.map(h => h.tradingsymbol),
    values: holdings.map(h => h.current_value)
  }
})

const topHoldingsData = computed(() => {
  const holdings = [...holdingsStore.usHoldings]
    .sort((a, b) => b.current_value - a.current_value)
    .slice(0, 10)
  return {
    labels: holdings.map(h => h.tradingsymbol),
    values: holdings.map(h => h.current_value),
    label: 'Current Value'
  }
})

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
    // Get current account ID (or use first account)
    const accountId = accountsStore.accounts[0]?.id || 1

    await holdingsStore.uploadUSHoldings(selectedFile.value, accountId)

    alert('US holdings uploaded and prices fetched successfully!')

    selectedFile.value = null
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  } catch (error) {
    alert(error.message || 'Failed to upload holdings')
  } finally {
    uploading.value = false
  }
}

const handleRefreshPrices = async () => {
  refreshing.value = true
  try {
    const accountId = accountsStore.accounts[0]?.id
    await holdingsStore.refreshUSPrices(accountId)

    console.log('US stock prices refreshed successfully!')
  } catch (error) {
    console.error('Failed to refresh prices', error)
  } finally {
    refreshing.value = false
  }
}

const showUploadAgain = () => {
  fileInput.value?.click()
}

// Auto-refresh prices on component mount
onMounted(async () => {
  if (hasUSHoldings.value) {
    await handleRefreshPrices()
  }
})
</script>

<style scoped>
.us-stocks-tab {
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
  margin: 0;
  padding-left: 20px;
  color: #6b7280;
  font-size: 14px;
  line-height: 1.8;
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  flex-wrap: wrap;
}

.refresh-prices-btn {
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
}

.refresh-prices-btn:hover:not(:disabled) {
  background: #2563eb;
}

.refresh-prices-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
  .us-stocks-tab {
    padding: 15px;
  }

  .upload-card {
    padding: 20px;
  }

  .charts-row {
    grid-template-columns: 1fr;
  }
}
</style>
