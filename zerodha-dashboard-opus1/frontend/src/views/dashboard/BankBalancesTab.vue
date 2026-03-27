<template>
  <div class="bank-balances-tab">
    <!-- Modals -->
    <BankUploadModal />
    <StatementReviewModal />

    <!-- Total Balance Section -->
    <div class="total-balance-card">
      <div class="total-info">
        <h2>Total Bank Balance</h2>
        <p class="total-amount">{{ formatCurrency(bankAccountsStore.totalBalance) }}</p>
        <p class="account-count">Across {{ activeBankCount }} active accounts</p>
      </div>
      <button class="add-bank-btn" @click="showAddBankModal">
        + Add Bank Account
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="bankAccountsStore.loading && !bankAccountsStore.bankAccounts.length" class="loading-state">
      <div class="spinner"></div>
      <p>Loading bank accounts...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="bankAccountsStore.error" class="error-state">
      <p>{{ bankAccountsStore.error }}</p>
      <button @click="loadBankAccounts" class="retry-btn">Retry</button>
    </div>

    <!-- Empty State -->
    <div v-else-if="!bankAccountsStore.bankAccounts.length" class="empty-state">
      <div class="empty-icon">🏦</div>
      <h3>No Bank Accounts Added</h3>
      <p>Add your first bank account to track your balances</p>
      <button class="add-bank-btn-large" @click="showAddBankModal">
        + Add Bank Account
      </button>
    </div>

    <!-- Content with bank selected or not -->
    <div v-else>
      <!-- No bank selected - show grid -->
      <div v-if="!selectedBank" class="bank-cards-grid">
        <BankCard
          v-for="bank in bankAccountsStore.activeBankAccounts"
          :key="bank.id"
          :bank="bank"
          :is-selected="false"
          @select="handleBankSelect"
          @upload="handleStatementUpload"
        />
      </div>

      <!-- Bank selected - show tabs and content -->
      <div v-else class="bank-detail-view">
        <!-- Back button and bank header -->
        <div class="bank-header">
          <button class="back-btn" @click="handleBankSelect(null)">
            ← Back to All Accounts
          </button>
          <div class="bank-info">
            <h2>{{ selectedBank.bank_name }}</h2>
            <p>{{ selectedBank.account_number }}</p>
          </div>
        </div>

        <!-- Tab Navigation -->
        <div class="tab-navigation">
          <button
            :class="['tab-btn', { active: activeTab === 'overview' }]"
            @click="activeTab = 'overview'"
          >
            Overview
          </button>
          <button
            :class="['tab-btn', { active: activeTab === 'analytics' }]"
            @click="activeTab = 'analytics'"
          >
            Analytics
          </button>
        </div>

        <!-- Tab Content -->
        <div class="tab-content">
          <!-- Overview Tab -->
          <div v-if="activeTab === 'overview'" class="overview-content">
            <div class="balance-card">
              <h3>Current Balance</h3>
              <p class="balance-amount">{{ formatCurrency(selectedBank.current_balance) }}</p>
              <p class="last-updated">
                Last updated: {{ formatDate(selectedBank.last_statement_date) }}
              </p>
            </div>
            <button class="upload-statement-btn" @click="handleStatementUpload(selectedBank)">
              📄 Upload Statement
            </button>
          </div>

          <!-- Analytics Tab -->
          <div v-if="activeTab === 'analytics'" class="analytics-content">
            <BankAnalyticsView :account-id="selectedBank.id" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useBankAccountsStore } from '@/stores/bankAccounts'
import { useUiStore } from '@/stores/ui'
import { storeToRefs } from 'pinia'
import { format, parseISO } from 'date-fns'
import BankCard from '@/components/bank/BankCard.vue'
import BankUploadModal from '@/components/bank/BankUploadModal.vue'
import StatementReviewModal from '@/components/bank/StatementReviewModal.vue'
import BankAnalyticsView from '@/components/bank/BankAnalyticsView.vue'

const bankAccountsStore = useBankAccountsStore()
const uiStore = useUiStore()
const { selectedBank } = storeToRefs(bankAccountsStore)

const activeTab = ref('overview')

const activeBankCount = computed(() => {
  return bankAccountsStore.activeBankAccounts.length
})

const formatCurrency = (value) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value || 0)
}

const formatDate = (dateString) => {
  if (!dateString) return 'Never'
  try {
    return format(parseISO(dateString), 'MMM dd, yyyy')
  } catch {
    return dateString
  }
}

const loadBankAccounts = async () => {
  try {
    await bankAccountsStore.fetchBankAccounts()
  } catch (error) {
    console.error('Failed to load bank accounts:', error)
  }
}

const handleBankSelect = (bank) => {
  bankAccountsStore.selectBank(bank)
  if (bank) {
    activeTab.value = 'overview'
  }
}

const handleStatementUpload = (bank) => {
  bankAccountsStore.openUploadModal(bank.id)
}

const showAddBankModal = () => {
  // Placeholder for add bank modal
  uiStore.addNotification({
    type: 'info',
    message: 'Add bank account modal - Coming soon!'
  })
}

onMounted(() => {
  loadBankAccounts()
})
</script>

<style scoped>
.bank-balances-tab {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.total-balance-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 32px;
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.total-info h2 {
  margin: 0 0 12px 0;
  font-size: 18px;
  font-weight: 500;
  opacity: 0.9;
}

.total-amount {
  margin: 0 0 8px 0;
  font-size: 42px;
  font-weight: 700;
  letter-spacing: -1px;
}

.account-count {
  margin: 0;
  font-size: 14px;
  opacity: 0.85;
}

.add-bank-btn {
  padding: 12px 24px;
  background: white;
  color: #667eea;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.add-bank-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.bank-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  background: white;
  border-radius: 12px;
  text-align: center;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-state p,
.error-state p {
  margin: 0;
  color: #6b7280;
  font-size: 16px;
}

.retry-btn {
  margin-top: 16px;
  padding: 10px 24px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.retry-btn:hover {
  background: #2563eb;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-state h3 {
  margin: 0 0 8px 0;
  font-size: 20px;
  color: #111827;
}

.empty-state p {
  margin: 0 0 24px 0;
  color: #6b7280;
  font-size: 14px;
}

.add-bank-btn-large {
  padding: 12px 32px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.add-bank-btn-large:hover {
  background: #2563eb;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.bank-detail-view {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.bank-header {
  padding: 24px;
  border-bottom: 1px solid #e5e7eb;
}

.back-btn {
  padding: 8px 16px;
  background: transparent;
  color: #3b82f6;
  border: 1px solid #3b82f6;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 16px;
}

.back-btn:hover {
  background: #eff6ff;
}

.bank-info h2 {
  margin: 0 0 4px 0;
  font-size: 24px;
  color: #111827;
}

.bank-info p {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
}

.tab-navigation {
  display: flex;
  gap: 0;
  border-bottom: 2px solid #e5e7eb;
  padding: 0 24px;
}

.tab-btn {
  padding: 16px 24px;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  font-size: 15px;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: -2px;
}

.tab-btn:hover {
  color: #3b82f6;
}

.tab-btn.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
}

.tab-content {
  min-height: 400px;
}

.overview-content {
  padding: 32px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.balance-card {
  text-align: center;
  padding: 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  color: white;
  width: 100%;
  max-width: 400px;
}

.balance-card h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 500;
  opacity: 0.9;
}

.balance-amount {
  margin: 0 0 12px 0;
  font-size: 48px;
  font-weight: 700;
  letter-spacing: -1px;
}

.last-updated {
  margin: 0;
  font-size: 13px;
  opacity: 0.85;
}

.upload-statement-btn {
  padding: 14px 32px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-statement-btn:hover {
  background: #2563eb;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.analytics-content {
  /* No padding - BankAnalyticsView has its own */
}

@media (max-width: 768px) {
  .bank-balances-tab {
    padding: 15px;
    gap: 20px;
  }

  .total-balance-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
    padding: 24px;
  }

  .total-amount {
    font-size: 32px;
  }

  .add-bank-btn {
    width: 100%;
  }

  .bank-cards-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .bank-header {
    padding: 16px;
  }

  .tab-navigation {
    padding: 0 16px;
  }

  .tab-btn {
    padding: 12px 16px;
    font-size: 14px;
  }

  .overview-content {
    padding: 20px;
  }

  .balance-amount {
    font-size: 36px;
  }
}
</style>
