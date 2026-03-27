<template>
  <div class="transactions-list">
    <!-- Filters Bar -->
    <div class="filters-bar">
      <div class="search-box">
        <input
          v-model="filters.search"
          type="text"
          placeholder="Search by description or merchant..."
          @input="handleFilterChange"
        />
      </div>

      <div class="filter-group">
        <select v-model="filters.transactionType" @change="handleFilterChange">
          <option value="">All Types</option>
          <option value="credit">Income</option>
          <option value="debit">Expenses</option>
        </select>

        <select v-model="filters.categoryId" @change="handleFilterChange">
          <option value="">All Categories</option>
          <option v-for="category in categories" :key="category.id" :value="category.id">
            {{ category.name }}
          </option>
        </select>

        <select v-model="filters.sortBy" @change="handleFilterChange">
          <option value="-date">Newest First</option>
          <option value="date">Oldest First</option>
          <option value="-amount">Highest Amount</option>
          <option value="amount">Lowest Amount</option>
        </select>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && !transactions.length" class="loading-state">
      <div class="spinner"></div>
      <p>Loading transactions...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button @click="refreshTransactions" class="retry-btn">Retry</button>
    </div>

    <!-- Empty State -->
    <div v-else-if="!transactions.length" class="empty-state">
      <div class="empty-icon">📝</div>
      <h3>No Transactions Found</h3>
      <p v-if="hasActiveFilters">Try adjusting your filters</p>
      <p v-else>Upload a bank statement to see transactions</p>
    </div>

    <!-- Transactions Table -->
    <div v-else class="table-container">
      <table class="transactions-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Description</th>
            <th>Merchant</th>
            <th>Category</th>
            <th>Amount</th>
            <th>Balance</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="transaction in transactions" :key="transaction.id">
            <td class="date-cell">{{ formatDate(transaction.transaction_date) }}</td>
            <td class="description-cell">
              <span class="description-text">{{ transaction.description }}</span>
              <span v-if="transaction.notes" class="notes">{{ transaction.notes }}</span>
            </td>
            <td class="merchant-cell">{{ transaction.merchant_name || '-' }}</td>
            <td class="category-cell">
              <span v-if="transaction.category" class="category-badge">
                {{ transaction.category.icon }} {{ transaction.category.name }}
              </span>
              <span v-else class="uncategorized">Uncategorized</span>
            </td>
            <td :class="['amount-cell', transaction.transaction_type]">
              {{ formatAmount(transaction.amount, transaction.transaction_type) }}
            </td>
            <td class="balance-cell">{{ formatCurrency(transaction.running_balance) }}</td>
            <td class="actions-cell">
              <button
                class="action-btn edit-btn"
                @click="handleEdit(transaction)"
                title="Edit transaction"
              >
                ✏️
              </button>
              <button
                class="action-btn delete-btn"
                @click="handleDelete(transaction)"
                title="Delete transaction"
              >
                🗑️
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div v-if="pagination.totalPages > 1" class="pagination">
        <button
          class="page-btn"
          :disabled="pagination.currentPage === 1"
          @click="goToPage(pagination.currentPage - 1)"
        >
          ← Previous
        </button>

        <span class="page-info">
          Page {{ pagination.currentPage }} of {{ pagination.totalPages }}
          ({{ pagination.totalItems }} transactions)
        </span>

        <button
          class="page-btn"
          :disabled="pagination.currentPage === pagination.totalPages"
          @click="goToPage(pagination.currentPage + 1)"
        >
          Next →
        </button>
      </div>
    </div>

    <!-- Edit Modal -->
    <div v-if="editingTransaction" class="modal-overlay" @click="closeEditModal">
      <div class="modal-content" @click.stop>
        <h3>Edit Transaction</h3>
        <div class="form-group">
          <label>Category</label>
          <select v-model="editForm.categoryId">
            <option :value="null">Uncategorized</option>
            <option v-for="category in categories" :key="category.id" :value="category.id">
              {{ category.icon }} {{ category.name }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>Notes</label>
          <textarea v-model="editForm.notes" placeholder="Add notes..."></textarea>
        </div>
        <div class="modal-actions">
          <button class="cancel-btn" @click="closeEditModal">Cancel</button>
          <button class="save-btn" @click="saveEdit">Save Changes</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { format, parseISO } from 'date-fns'
import { useBankAccountsStore } from '@/stores/bankAccounts'
import { useCategoriesStore } from '@/stores/categories'

const props = defineProps({
  accountId: {
    type: Number,
    required: true
  }
})

const bankStore = useBankAccountsStore()
const categoriesStore = useCategoriesStore()
const { categories } = storeToRefs(categoriesStore)

const transactions = ref([])
const loading = ref(false)
const error = ref(null)
const pagination = ref({
  currentPage: 1,
  totalPages: 1,
  totalItems: 0,
  perPage: 20
})

const filters = ref({
  search: '',
  transactionType: '',
  categoryId: '',
  sortBy: '-date'
})

const editingTransaction = ref(null)
const editForm = ref({
  categoryId: null,
  notes: ''
})

const hasActiveFilters = computed(() => {
  return filters.value.search || filters.value.transactionType || filters.value.categoryId
})

function formatDate(dateString) {
  try {
    return format(parseISO(dateString), 'MMM dd, yyyy')
  } catch {
    return dateString
  }
}

function formatCurrency(value) {
  return `₹${Math.abs(value || 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })}`
}

function formatAmount(amount, type) {
  const formatted = formatCurrency(amount)
  return type === 'credit' ? `+${formatted}` : `-${formatted}`
}

async function loadTransactions() {
  loading.value = true
  error.value = null

  try {
    const params = {
      page: pagination.value.currentPage,
      per_page: pagination.value.perPage,
      sort_by: filters.value.sortBy
    }

    if (filters.value.search) params.search = filters.value.search
    if (filters.value.transactionType) params.transaction_type = filters.value.transactionType
    if (filters.value.categoryId) params.category_id = filters.value.categoryId

    const response = await bankStore.fetchTransactions(props.accountId, params)

    transactions.value = response.transactions
    pagination.value = {
      currentPage: response.page,
      totalPages: response.pages,
      totalItems: response.total,
      perPage: response.per_page
    }
  } catch (err) {
    error.value = err.response?.data?.error || 'Failed to load transactions'
    console.error('Error loading transactions:', err)
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  pagination.value.currentPage = 1
  loadTransactions()
}

function goToPage(page) {
  pagination.value.currentPage = page
  loadTransactions()
}

function refreshTransactions() {
  loadTransactions()
}

function handleEdit(transaction) {
  editingTransaction.value = transaction
  editForm.value = {
    categoryId: transaction.category?.id || null,
    notes: transaction.notes || ''
  }
}

function closeEditModal() {
  editingTransaction.value = null
  editForm.value = {
    categoryId: null,
    notes: ''
  }
}

async function saveEdit() {
  if (!editingTransaction.value) return

  try {
    await bankStore.updateTransaction(editingTransaction.value.id, {
      category_id: editForm.value.categoryId,
      notes: editForm.value.notes
    })

    closeEditModal()
    await loadTransactions()
  } catch (err) {
    error.value = err.response?.data?.error || 'Failed to update transaction'
    console.error('Error updating transaction:', err)
  }
}

async function handleDelete(transaction) {
  if (!confirm(`Delete transaction: ${transaction.description}?`)) return

  try {
    await bankStore.deleteTransaction(transaction.id)
    await loadTransactions()
  } catch (err) {
    error.value = err.response?.data?.error || 'Failed to delete transaction'
    console.error('Error deleting transaction:', err)
  }
}

watch(() => props.accountId, () => {
  pagination.value.currentPage = 1
  loadTransactions()
}, { immediate: true })

onMounted(() => {
  categoriesStore.fetchCategories()
  loadTransactions()
})
</script>

<style scoped>
.transactions-list {
  padding: 20px;
}

.filters-bar {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.search-box {
  margin-bottom: 16px;
}

.search-box input {
  width: 100%;
  padding: 10px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
}

.search-box input:focus {
  outline: none;
  border-color: #3b82f6;
}

.filter-group {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.filter-group select {
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  cursor: pointer;
}

.filter-group select:focus {
  outline: none;
  border-color: #3b82f6;
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
  border: 4px solid #f3f4f6;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state p {
  color: #ef4444;
  margin-bottom: 16px;
}

.retry-btn {
  padding: 10px 24px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
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
  margin: 0;
  color: #6b7280;
}

.table-container {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.transactions-table {
  width: 100%;
  border-collapse: collapse;
}

.transactions-table thead {
  background: #f9fafb;
  border-bottom: 2px solid #e5e7eb;
}

.transactions-table th {
  padding: 12px 16px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.transactions-table td {
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
  font-size: 14px;
}

.transactions-table tbody tr:hover {
  background: #f9fafb;
}

.date-cell {
  white-space: nowrap;
  color: #6b7280;
}

.description-cell {
  max-width: 300px;
}

.description-text {
  display: block;
  font-weight: 500;
  color: #111827;
}

.notes {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-top: 4px;
}

.merchant-cell {
  color: #6b7280;
}

.category-badge {
  display: inline-block;
  padding: 4px 10px;
  background: #eff6ff;
  color: #3b82f6;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.uncategorized {
  color: #9ca3af;
  font-size: 12px;
}

.amount-cell {
  font-weight: 600;
  white-space: nowrap;
}

.amount-cell.credit {
  color: #10b981;
}

.amount-cell.debit {
  color: #ef4444;
}

.balance-cell {
  font-weight: 500;
  color: #111827;
  white-space: nowrap;
}

.actions-cell {
  white-space: nowrap;
}

.action-btn {
  padding: 6px 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.action-btn:hover {
  opacity: 1;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-top: 1px solid #e5e7eb;
}

.page-btn {
  padding: 8px 16px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.page-btn:hover:not(:disabled) {
  border-color: #3b82f6;
  color: #3b82f6;
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  font-size: 14px;
  color: #6b7280;
}

/* Modal Styles */
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
}

.modal-content {
  background: white;
  border-radius: 12px;
  padding: 24px;
  width: 90%;
  max-width: 500px;
}

.modal-content h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #111827;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
}

.form-group textarea {
  min-height: 80px;
  resize: vertical;
  font-family: inherit;
}

.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #3b82f6;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
}

.cancel-btn,
.save-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-btn {
  background: #f3f4f6;
  color: #374151;
}

.cancel-btn:hover {
  background: #e5e7eb;
}

.save-btn {
  background: #3b82f6;
  color: white;
}

.save-btn:hover {
  background: #2563eb;
}

/* Responsive */
@media (max-width: 768px) {
  .transactions-list {
    padding: 0;
  }

  .filters-bar {
    border-radius: 0;
  }

  .table-container {
    border-radius: 0;
    overflow-x: auto;
  }

  .transactions-table {
    min-width: 800px;
  }

  .filter-group {
    grid-template-columns: 1fr;
  }
}
</style>
