<template>
  <section class="chart-panel" :aria-labelledby="headingId">
    <div class="chart-heading">
      <div>
        <h2 :id="headingId">{{ title }}</h2>
        <p v-if="subtitle">{{ subtitle }}</p>
      </div>
      <slot name="action"></slot>
    </div>
    <div v-if="hasData" class="chart-content">
      <slot></slot>
    </div>
    <div v-else class="chart-empty">
      <span aria-hidden="true">—</span>
      <strong>{{ emptyTitle }}</strong>
      <p>{{ emptyMessage }}</p>
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true
  },
  subtitle: {
    type: String,
    default: ''
  },
  hasData: {
    type: Boolean,
    default: false
  },
  emptyTitle: {
    type: String,
    default: 'No data available'
  },
  emptyMessage: {
    type: String,
    default: 'This visualization will appear after portfolio data is available.'
  }
})

const headingId = `chart-${Math.random().toString(36).slice(2, 9)}`
</script>

<style scoped>
.chart-panel {
  min-width: 0;
  padding: 19px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.chart-heading {
  display: flex;
  min-height: 43px;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 13px;
}

.chart-heading h2 {
  margin: 0;
  color: var(--color-text);
  font-size: 0.96rem;
  letter-spacing: -0.015em;
}

.chart-heading p {
  margin: 3px 0 0;
  color: var(--color-text-faint);
  font-size: 0.72rem;
}

.chart-content {
  min-height: 280px;
}

.chart-empty {
  display: flex;
  min-height: 280px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  padding: 30px;
  border-radius: 10px;
  background: var(--color-surface-subtle);
  text-align: center;
}

.chart-empty > span {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 50%;
  background: var(--color-surface-strong);
  color: var(--color-text-faint);
}

.chart-empty strong {
  margin-top: 10px;
  font-size: 0.85rem;
}

.chart-empty p {
  max-width: 330px;
  margin: 3px 0 0;
  color: var(--color-text-faint);
  font-size: 0.73rem;
}

@media (max-width: 560px) {
  .chart-panel {
    padding: 15px;
  }

  .chart-content,
  .chart-empty {
    min-height: 240px;
  }
}
</style>
