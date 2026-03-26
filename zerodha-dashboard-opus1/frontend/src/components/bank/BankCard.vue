<template>
  <div
    class="bank-card"
    :class="{ 'selected': isSelected }"
    @click="handleSelect"
  >
    <div class="bank-header">
      <div class="bank-icon">
        <span class="icon">{{ bankIcon }}</span>
      </div>
      <div class="bank-info">
        <h3 class="bank-name">{{ bank.bank_name }}</h3>
        <p class="account-number">{{ formatAccountNumber(bank.account_number) }}</p>
      </div>
    </div>

    <div class="bank-balance">
      <span class="balance-label">Current Balance</span>
      <span class="balance-value">{{ formatCurrency(bank.balance) }}</span>
    </div>

    <div v-if="bank.monthly_change" class="bank-change" :class="changeClass">
      <span class="change-label">Monthly Change</span>
      <span class="change-value">
        {{ bank.monthly_change > 0 ? '+' : '' }}{{ formatCurrency(bank.monthly_change) }}
        ({{ formatPercentage(bank.monthly_change_percentage) }})
      </span>
    </div>

    <div class="bank-actions">
      <button
        class="upload-btn"
        @click.stop="$emit('upload', bank)"
      >
        Upload Statement
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  bank: {
    type: Object,
    required: true
  },
  isSelected: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['select', 'upload'])

const bankIcon = computed(() => {
  // Map bank names to icons
  const iconMap = {
    'HDFC': '🏦',
    'ICICI': '🏛️',
    'SBI': '🏢',
    'Axis': '💳',
    'Kotak': '🏪',
    'IDFC': '🏭',
    'Yes Bank': '💰',
  }

  // Check if bank name contains any of the known bank names
  for (const [bankName, icon] of Object.entries(iconMap)) {
    if (props.bank.bank_name.toUpperCase().includes(bankName.toUpperCase())) {
      return icon
    }
  }

  return '🏦' // Default icon
})

const changeClass = computed(() => {
  if (!props.bank.monthly_change) return ''
  return props.bank.monthly_change > 0 ? 'positive' : 'negative'
})

const formatCurrency = (value) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value || 0)
}

const formatPercentage = (value) => {
  if (!value) return '0%'
  return `${value.toFixed(2)}%`
}

const formatAccountNumber = (accountNumber) => {
  if (!accountNumber) return ''
  // Show only last 4 digits
  return `****${accountNumber.slice(-4)}`
}

const handleSelect = () => {
  emit('select', props.bank)
}
</script>

<style scoped>
.bank-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.bank-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.bank-card.selected {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

.bank-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.bank-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bank-icon .icon {
  font-size: 24px;
}

.bank-info {
  flex: 1;
}

.bank-name {
  margin: 0 0 4px 0;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.account-number {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
  font-family: 'Courier New', monospace;
}

.bank-balance {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px 0;
  border-top: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 16px;
}

.balance-label {
  font-size: 12px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.balance-value {
  font-size: 28px;
  font-weight: 700;
  color: #111827;
}

.bank-change {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 16px;
}

.change-label {
  font-size: 12px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.change-value {
  font-size: 14px;
  font-weight: 600;
}

.bank-change.positive .change-value {
  color: #10b981;
}

.bank-change.negative .change-value {
  color: #ef4444;
}

.bank-actions {
  display: flex;
  gap: 10px;
}

.upload-btn {
  flex: 1;
  padding: 10px 16px;
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-btn:hover {
  background: #e5e7eb;
  border-color: #d1d5db;
}

@media (max-width: 768px) {
  .bank-card {
    padding: 20px;
  }

  .bank-name {
    font-size: 16px;
  }

  .balance-value {
    font-size: 24px;
  }
}
</style>
