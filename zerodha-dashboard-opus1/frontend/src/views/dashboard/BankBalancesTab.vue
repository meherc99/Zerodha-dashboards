<template>
  <div class="bank-balances-tab">
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

    <!-- Bank Cards Grid -->
    <div v-else class="bank-cards-grid">
      <BankCard
        v-for="bank in bankAccountsStore.activeBankAccounts"
        :key="bank.id"
        :bank="bank"
        :is-selected="selectedBankId === bank.id"
        @select="handleBankSelect"
        @upload="handleStatementUpload"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useBankAccountsStore } from '@/stores/bankAccounts'
import { useUiStore } from '@/stores/ui'
import BankCard from '@/components/bank/BankCard.vue'

const bankAccountsStore = useBankAccountsStore()
const uiStore = useUiStore()

const selectedBankId = ref(null)

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

const loadBankAccounts = async () => {
  try {
    await bankAccountsStore.fetchBankAccounts()
  } catch (error) {
    console.error('Failed to load bank accounts:', error)
  }
}

const handleBankSelect = (bank) => {
  selectedBankId.value = bank.id === selectedBankId.value ? null : bank.id
  bankAccountsStore.selectBank(bank.id === selectedBankId.value ? null : bank)
}

const handleStatementUpload = (bank) => {
  // Placeholder for statement upload functionality
  uiStore.addNotification({
    type: 'info',
    message: `Statement upload for ${bank.bank_name} - Coming soon!`
  })
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
}
</style>
