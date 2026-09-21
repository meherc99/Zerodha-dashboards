<template>
  <div class="loading-spinner">
    <div class="spinner"></div>
    <p v-if="message">{{ message }}</p>
  </div>
</template>

<script setup>
defineProps({
  message: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 20px;
  gap: 14px;
}

.spinner {
  position: relative;
  width: 38px;
  height: 38px;
}

.spinner::before,
.spinner::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
}

.spinner::before {
  border: 3px solid var(--color-border-strong);
}

.spinner::after {
  border: 3px solid transparent;
  border-top-color: var(--color-primary);
  box-shadow: 0 0 14px rgba(61, 126, 255, 0.4);
  animation: spin 900ms linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

p {
  margin: 0;
  color: var(--color-text-soft);
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}
</style>
