<template>
  <fieldset class="account-selector" :disabled="loading">
    <legend>Portfolio scope</legend>
    <div class="scope-toggle" aria-label="Choose family or individual portfolio">
      <button
        type="button"
        class="scope-option"
        :class="{ active: isFamilyView && !showMemberPicker }"
        :aria-pressed="isFamilyView && !showMemberPicker"
        @click="selectFamily"
      >
        Family
      </button>
      <button
        type="button"
        class="scope-option"
        :class="{ active: showMemberPicker }"
        :aria-pressed="showMemberPicker"
        :disabled="!accounts.length"
        @click="selectMember"
      >
        Member
      </button>
    </div>
    <label v-if="showMemberPicker" class="member-select-label">
      <span class="sr-only">Family member account</span>
      <select
        ref="memberSelect"
        class="member-select"
        :value="isFamilyView ? '' : modelValue"
        aria-label="Family member account"
        @change="selectAccount"
      >
        <option value="" disabled>Choose a family member</option>
        <option
          v-for="account in accounts"
          :key="account.id"
          :value="account.id"
        >
          {{ account.account_name || `Account ${account.id}` }}
        </option>
      </select>
    </label>
  </fieldset>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: [Number, String],
    default: null
  },
  accounts: {
    type: Array,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])
const memberSelect = ref(null)
const showMemberPicker = ref(props.modelValue !== null && props.modelValue !== '')

const isFamilyView = computed(() => props.modelValue === null || props.modelValue === '')

watch(() => props.modelValue, value => {
  showMemberPicker.value = value !== null && value !== ''
})

const selectFamily = () => {
  showMemberPicker.value = false
  emit('update:modelValue', null)
}

const selectMember = async () => {
  showMemberPicker.value = true
  await nextTick()
  memberSelect.value?.focus()
}

const selectAccount = (event) => {
  emit('update:modelValue', Number(event.target.value))
}
</script>

<style scoped>
.account-selector {
  min-width: 0;
  margin: 0;
  padding: 0;
  border: 0;
}

.account-selector legend {
  margin-bottom: 5px;
  color: var(--color-text-faint);
  font-size: 0.68rem;
  font-weight: 750;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.account-selector,
.scope-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
}

.scope-toggle {
  padding: 3px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-surface-strong);
}

.scope-option {
  min-height: 32px;
  padding: 5px 10px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--color-text-soft);
  font-size: 0.78rem;
  font-weight: 750;
}

.scope-option.active {
  background: var(--color-surface);
  box-shadow: 0 1px 3px rgba(21, 34, 56, 0.11);
  color: var(--color-primary-dark);
}

.member-select {
  width: min(190px, 32vw);
  min-height: 40px;
  padding: 7px 34px 7px 11px;
  overflow: hidden;
  border: 1px solid var(--color-border-strong);
  border-radius: 10px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 0.82rem;
  font-weight: 650;
  text-overflow: ellipsis;
}

@media (max-width: 620px) {
  .account-selector {
    width: 100%;
    flex-wrap: wrap;
  }

  .scope-toggle {
    flex: 1;
  }

  .scope-option {
    flex: 1;
  }

  .member-select-label {
    width: 100%;
  }

  .member-select {
    width: 100%;
  }
}
</style>
