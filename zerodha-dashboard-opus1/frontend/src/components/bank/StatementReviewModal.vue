<template>
  <Teleport to="body">
    <div v-if="isOpen" class="modal-overlay" @click="handleOverlayClick">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h2>Review Statement Transactions</h2>
          <button class="close-btn" @click="handleClose" :disabled="loading">×</button>
        </div>

        <div class="modal-body">
          <!-- Loading State -->
          <div v-if="loading" class="loading-state">
            <div class="spinner"></div>
            <p>Loading transactions...</p>
          </div>

          <!-- Error State -->
          <div v-else-if="error" class="error-state">
            <div class="error-icon">⚠️</div>
            <p class="error-text">{{ error }}</p>
            <button class="retry-btn" @click="loadPreview">Retry</button>
          </div>

          <!-- Review Content -->
          <div v-else class="review-content">
            <!-- Warnings Section -->
            <div v-if="warnings.length > 0" class="warnings-section">
              <div class="warnings-header">
                <span class="warning-icon">⚠️</span>
                <span class="warnings-title">Warnings ({{ warnings.length }})</span>
              </div>
              <div class="warnings-list">
                <div
                  v-for="(warning, index) in warnings"
                  :key="index"
                  class="warning-item"
                  :class="warning.severity"
                >
                  <span class="warning-message">{{ warning.message }}</span>
                </div>
              </div>
            </div>

            <!-- Transaction Summary -->
            <div class="summary-section">
              <div class="summary-item">
                <span class="summary-label">Total Transactions</span>
                <span class="summary-value">{{ transactions.length }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">Total Debits</span>
                <span class="summary-value debit">{{ formatCurrency(totalDebits) }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">Total Credits</span>
                <span class="summary-value credit">{{ formatCurrency(totalCredits) }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">Net Change</span>
                <span class="summary-value" :class="netChange >= 0 ? 'credit' : 'debit'">
                  {{ formatCurrency(netChange) }}
                </span>
              </div>
            </div>

            <!-- Transactions Table -->
            <div class="table-container">
              <table class="transactions-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Description</th>
                    <th>Debit</th>
                    <th>Credit</th>
                    <th>Balance</th>
                    <th>Category</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(txn, index) in transactions"
                    :key="index"
                    class="transaction-row"
                    :class="{ 'low-confidence': txn.confidence && txn.confidence < 0.7 }"
                  >
                    <td class="date-cell">{{ formatDate(txn.date) }}</td>
                    <td class="description-cell">
                      <div class="description-content">
                        <span>{{ txn.description }}</span>
                        <input
                          v-if="txn.editable_note !== false"
                          type="text"
                          v-model="txn.note"
                          placeholder="Add note..."
                          class="note-input"
                          @blur="updateTransaction(index, 'note', txn.note)"
                        />
                      </div>
                    </td>
                    <td class="amount-cell debit">
                      {{ txn.debit ? formatCurrency(txn.debit) : '-' }}
                    </td>
                    <td class="amount-cell credit">
                      {{ txn.credit ? formatCurrency(txn.credit) : '-' }}
                    </td>
                    <td class="amount-cell balance">
                      {{ formatCurrency(txn.balance) }}
                    </td>
                    <td class="category-cell">
                      <select
                        v-model="txn.category_id"
                        @change="updateTransaction(index, 'category_id', txn.category_id)"
                        class="category-select"
                        :style="{ borderColor: getCategoryColor(txn.category_id) }"
                      >
                        <option :value="null">Uncategorized</option>
                        <option
                          v-for="category in categories"
                          :key="category.id"
                          :value="category.id"
                        >
                          {{ category.name }}
                        </option>
                      </select>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button
            class="btn-secondary"
            @click="handleClose"
            :disabled="loading"
          >
            Cancel
          </button>
          <button
            class="btn-primary"
            @click="handleApprove"
            :disabled="loading || transactions.length === 0"
          >
            Approve & Save
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useBankAccountsStore } from '@/stores/bankAccounts'
import { useCategoriesStore } from '@/stores/categories'
import { useUiStore } from '@/stores/ui'
import { storeToRefs } from 'pinia'

const bankAccountsStore = useBankAccountsStore()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

const { reviewModal } = storeToRefs(bankAccountsStore)
const { categories } = storeToRefs(categoriesStore)

const isOpen = computed(() => reviewModal.value.isOpen)
const loading = computed(() => reviewModal.value.loading)
const error = computed(() => reviewModal.value.error)
const transactions = computed(() => reviewModal.value.transactions)
const warnings = computed(() => reviewModal.value.warnings)

const totalDebits = computed(() => {
  return transactions.value.reduce((sum, txn) => sum + (txn.debit || 0), 0)
})

const totalCredits = computed(() => {
  return transactions.value.reduce((sum, txn) => sum + (txn.credit || 0), 0)
})

const netChange = computed(() => totalCredits.value - totalDebits.value)

// Load categories when modal opens
onMounted(() => {
  if (isOpen.value && categories.value.length === 0) {
    categoriesStore.fetchCategories()
  }
})

const loadPreview = async () => {
  if (reviewModal.value.statementId) {
    await bankAccountsStore.openReviewModal(reviewModal.value.statementId)
  }
}

const updateTransaction = (index, field, value) => {
  bankAccountsStore.updateReviewTransaction(index, field, value)
}

const getCategoryColor = (categoryId) => {
  return categoriesStore.getCategoryColor(categoryId)
}

const handleApprove = async () => {
  try {
    await bankAccountsStore.approveStatement(
      reviewModal.value.statementId,
      transactions.value
    )
    uiStore.addNotification({
      type: 'success',
      message: 'Statement approved successfully!'
    })
  } catch (error) {
    uiStore.addNotification({
      type: 'error',
      message: error.response?.data?.error || 'Failed to approve statement'
    })
  }
}

const handleClose = () => {
  if (!loading.value) {
    bankAccountsStore.closeReviewModal()
  }
}

const handleOverlayClick = () => {
  handleClose()
}

const formatCurrency = (value) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value || 0)
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content.large {
  max-width: 1200px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 24px 16px;
  border-bottom: 1px solid #e5e7eb;
  position: sticky;
  top: 0;
  background: white;
  z-index: 10;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #111827;
}

.close-btn {
  background: none;
  border: none;
  font-size: 28px;
  color: #6b7280;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s;
}

.close-btn:hover:not(:disabled) {
  background: #f3f4f6;
  color: #111827;
}

.close-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-body {
  padding: 24px;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 16px;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e5e7eb;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-state p,
.error-text {
  margin: 0;
  color: #6b7280;
  font-size: 16px;
}

.error-icon {
  font-size: 48px;
}

.retry-btn {
  padding: 10px 24px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.retry-btn:hover {
  background: #2563eb;
}

.review-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.warnings-section {
  background: #fef3c7;
  border: 1px solid #fcd34d;
  border-radius: 12px;
  padding: 16px;
}

.warnings-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.warning-icon {
  font-size: 20px;
}

.warnings-title {
  font-size: 14px;
  font-weight: 600;
  color: #92400e;
}

.warnings-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.warning-item {
  background: white;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
  border-left: 3px solid #fbbf24;
}

.warning-item.error {
  border-left-color: #ef4444;
  background: #fef2f2;
}

.warning-message {
  color: #374151;
}

.summary-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.summary-item {
  background: #f9fafb;
  padding: 16px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-label {
  font-size: 12px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.summary-value {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}

.summary-value.debit {
  color: #ef4444;
}

.summary-value.credit {
  color: #10b981;
}

.table-container {
  overflow-x: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.transactions-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.transactions-table thead {
  background: #f9fafb;
  position: sticky;
  top: 0;
  z-index: 5;
}

.transactions-table th {
  padding: 12px;
  text-align: left;
  font-weight: 600;
  color: #374151;
  border-bottom: 2px solid #e5e7eb;
  white-space: nowrap;
}

.transactions-table tbody tr {
  border-bottom: 1px solid #e5e7eb;
  transition: background 0.2s;
}

.transactions-table tbody tr:hover {
  background: #f9fafb;
}

.transaction-row.low-confidence {
  background: #fef3c7;
}

.transaction-row.low-confidence:hover {
  background: #fde68a;
}

.transactions-table td {
  padding: 12px;
}

.date-cell {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #6b7280;
  white-space: nowrap;
}

.description-cell {
  max-width: 300px;
}

.description-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.description-content > span {
  color: #111827;
  word-break: break-word;
}

.note-input {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 12px;
  color: #6b7280;
  font-style: italic;
  transition: all 0.2s;
}

.note-input:focus {
  outline: none;
  border-color: #667eea;
  background: #f9fafb;
}

.amount-cell {
  font-family: 'Courier New', monospace;
  font-weight: 600;
  text-align: right;
  white-space: nowrap;
}

.amount-cell.debit {
  color: #ef4444;
}

.amount-cell.credit {
  color: #10b981;
}

.amount-cell.balance {
  color: #374151;
}

.category-cell {
  min-width: 150px;
}

.category-select {
  width: 100%;
  padding: 6px 8px;
  border: 2px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
  color: #374151;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
}

.category-select:focus {
  outline: none;
  border-color: #667eea;
}

.category-select:hover {
  background: #f9fafb;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px 24px;
  border-top: 1px solid #e5e7eb;
  position: sticky;
  bottom: 0;
  background: white;
}

.btn-secondary,
.btn-primary {
  padding: 10px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover:not(:disabled) {
  background: #e5e7eb;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

@media (max-width: 768px) {
  .modal-overlay {
    padding: 0;
  }

  .modal-content {
    border-radius: 0;
    max-height: 100vh;
    height: 100vh;
  }

  .summary-section {
    grid-template-columns: 1fr 1fr;
  }

  .transactions-table {
    font-size: 12px;
  }

  .transactions-table th,
  .transactions-table td {
    padding: 8px;
  }

  .description-cell {
    max-width: 200px;
  }
}
</style>
