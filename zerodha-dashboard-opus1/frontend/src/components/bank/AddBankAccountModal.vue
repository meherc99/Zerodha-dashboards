<template>
  <div v-if="isOpen" class="modal-overlay" @click="handleClose">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>Add Bank Account</h2>
        <button class="close-btn" @click="handleClose">×</button>
      </div>

      <form @submit.prevent="handleSubmit" class="modal-body">
        <!-- Bank Name -->
        <div class="form-group">
          <label for="bank-name">Bank Name <span class="required">*</span></label>
          <input
            id="bank-name"
            v-model="form.bankName"
            type="text"
            placeholder="e.g., HDFC Bank, ICICI Bank, SBI"
            required
            :disabled="loading"
          />
          <span v-if="errors.bankName" class="error-text">{{ errors.bankName }}</span>
        </div>

        <!-- Account Number -->
        <div class="form-group">
          <label for="account-number">Account Number <span class="required">*</span></label>
          <input
            id="account-number"
            v-model="form.accountNumber"
            type="text"
            placeholder="Enter account number"
            required
            :disabled="loading"
          />
          <span v-if="errors.accountNumber" class="error-text">{{ errors.accountNumber }}</span>
        </div>

        <!-- Account Type -->
        <div class="form-group">
          <label for="account-type">Account Type <span class="required">*</span></label>
          <select
            id="account-type"
            v-model="form.accountType"
            required
            :disabled="loading"
          >
            <option value="">Select account type</option>
            <option value="savings">Savings Account</option>
            <option value="current">Current Account</option>
            <option value="credit">Credit Card</option>
          </select>
          <span v-if="errors.accountType" class="error-text">{{ errors.accountType }}</span>
        </div>

        <!-- Current Balance -->
        <div class="form-group">
          <label for="current-balance">Current Balance (Optional)</label>
          <div class="input-with-prefix">
            <span class="prefix">₹</span>
            <input
              id="current-balance"
              v-model.number="form.currentBalance"
              type="number"
              step="0.01"
              placeholder="0.00"
              :disabled="loading"
            />
          </div>
          <p class="help-text">Leave blank if you'll upload a statement first</p>
        </div>

        <!-- Currency -->
        <div class="form-group">
          <label for="currency">Currency</label>
          <select
            id="currency"
            v-model="form.currency"
            :disabled="loading"
          >
            <option value="INR">INR (₹)</option>
            <option value="USD">USD ($)</option>
            <option value="EUR">EUR (€)</option>
            <option value="GBP">GBP (£)</option>
          </select>
        </div>

        <!-- Error Message -->
        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <!-- Actions -->
        <div class="modal-actions">
          <button
            type="button"
            class="cancel-btn"
            @click="handleClose"
            :disabled="loading"
          >
            Cancel
          </button>
          <button
            type="submit"
            class="submit-btn"
            :disabled="loading"
          >
            <span v-if="loading" class="spinner-small"></span>
            <span v-else>Add Account</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useBankAccountsStore } from '@/stores/bankAccounts'

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  }
})

const emit = defineEmits(['close', 'success'])

const bankStore = useBankAccountsStore()

const form = ref({
  bankName: '',
  accountNumber: '',
  accountType: '',
  currentBalance: null,
  currency: 'INR'
})

const errors = ref({})
const error = ref(null)
const loading = ref(false)

function validateForm() {
  errors.value = {}
  let isValid = true

  if (!form.value.bankName || form.value.bankName.trim().length < 2) {
    errors.value.bankName = 'Bank name must be at least 2 characters'
    isValid = false
  }

  if (!form.value.accountNumber || form.value.accountNumber.trim().length < 4) {
    errors.value.accountNumber = 'Account number must be at least 4 characters'
    isValid = false
  }

  if (!form.value.accountType) {
    errors.value.accountType = 'Please select an account type'
    isValid = false
  }

  return isValid
}

async function handleSubmit() {
  error.value = null

  if (!validateForm()) {
    return
  }

  loading.value = true

  try {
    const data = {
      bank_name: form.value.bankName.trim(),
      account_number: form.value.accountNumber.trim(),
      account_type: form.value.accountType,
      currency: form.value.currency
    }

    // Only include balance if provided
    if (form.value.currentBalance !== null && form.value.currentBalance !== '') {
      data.current_balance = parseFloat(form.value.currentBalance)
    }

    await bankStore.createBankAccount(data)

    // Success - emit event and close
    emit('success')
    handleClose()
    resetForm()
  } catch (err) {
    error.value = err.response?.data?.error || 'Failed to add bank account. Please try again.'
    console.error('Error adding bank account:', err)
  } finally {
    loading.value = false
  }
}

function handleClose() {
  if (!loading.value) {
    emit('close')
  }
}

function resetForm() {
  form.value = {
    bankName: '',
    accountNumber: '',
    accountType: '',
    currentBalance: null,
    currency: 'INR'
  }
  errors.value = {}
  error.value = null
}

// Reset form when modal opens
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    resetForm()
  }
})
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
  border-radius: 12px;
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 24px 16px 24px;
  border-bottom: 1px solid #e5e7eb;
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
  font-size: 32px;
  line-height: 1;
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

.close-btn:hover {
  background: #f3f4f6;
  color: #111827;
}

.modal-body {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.required {
  color: #ef4444;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  transition: all 0.2s;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-group input:disabled,
.form-group select:disabled {
  background: #f9fafb;
  cursor: not-allowed;
}

.input-with-prefix {
  position: relative;
  display: flex;
  align-items: center;
}

.prefix {
  position: absolute;
  left: 12px;
  font-weight: 500;
  color: #6b7280;
  pointer-events: none;
}

.input-with-prefix input {
  padding-left: 28px;
}

.help-text {
  margin: 6px 0 0 0;
  font-size: 12px;
  color: #6b7280;
}

.error-text {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: #ef4444;
}

.error-message {
  padding: 12px 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  color: #991b1b;
  font-size: 14px;
  margin-bottom: 20px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #e5e7eb;
}

.cancel-btn,
.submit-btn {
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

.cancel-btn:hover:not(:disabled) {
  background: #e5e7eb;
}

.cancel-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.submit-btn {
  background: #3b82f6;
  color: white;
  min-width: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.submit-btn:hover:not(:disabled) {
  background: #2563eb;
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 640px) {
  .modal-overlay {
    padding: 0;
  }

  .modal-content {
    max-height: 100vh;
    border-radius: 0;
  }

  .modal-header {
    padding: 20px 20px 16px 20px;
  }

  .modal-body {
    padding: 20px;
  }

  .modal-actions {
    flex-direction: column-reverse;
  }

  .cancel-btn,
  .submit-btn {
    width: 100%;
  }
}
</style>
