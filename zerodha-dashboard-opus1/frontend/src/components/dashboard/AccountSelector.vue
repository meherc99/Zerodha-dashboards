<template>
  <div class="account-selector">
    <label for="account">Account:</label>
    <select
      id="account"
      :value="modelValue"
      @change="$emit('update:modelValue', $event.target.value)"
      class="account-select"
    >
      <option :value="null">All Accounts (Aggregated)</option>
      <option
        v-for="account in accounts"
        :key="account.id"
        :value="account.id"
      >
        {{ account.account_name }}
      </option>
    </select>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: [Number, null],
    default: null
  },
  accounts: {
    type: Array,
    required: true
  }
})

defineEmits(['update:modelValue'])
</script>

<style scoped>
.account-selector {
  display: flex;
  align-items: center;
  gap: 12px;
}

label {
  font-weight: 600;
  color: #374151;
  font-size: 14px;
}

.account-select {
  padding: 8px 16px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 200px;
}

.account-select:hover {
  border-color: #3b82f6;
}

.account-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}
</style>
