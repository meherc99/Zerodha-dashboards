<template>
  <component
    :is="onClick ? 'button' : 'article'"
    class="data-card"
    :class="[tone, { clickable: onClick }]"
    :type="onClick ? 'button' : undefined"
    @click="onClick?.()"
  >
    <div class="card-header">
      <h3>{{ title }}</h3>
      <span v-if="icon" class="card-icon" aria-hidden="true">{{ icon }}</span>
    </div>
    <div class="card-body">
      <div class="value" :class="valueClass">{{ formattedValue }}</div>
      <div v-if="change !== undefined" class="change" :class="changeClass">
        <span class="change-icon">{{ changeIcon }}</span>
        <span>{{ Math.abs(change).toFixed(2) }}%</span>
      </div>
      <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
    </div>
  </component>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [Number, String],
    required: true
  },
  change: {
    type: Number,
    default: undefined
  },
  subtitle: {
    type: String,
    default: ''
  },
  format: {
    type: String,
    default: 'currency' // 'currency', 'number', 'text'
  },
  currency: {
    type: String,
    default: 'INR'
  },
  onClick: {
    type: Function,
    default: null
  },
  icon: {
    type: String,
    default: ''
  },
  tone: {
    type: String,
    default: 'neutral',
    validator: value => ['neutral', 'primary', 'positive', 'violet'].includes(value)
  }
})

const formattedValue = computed(() => {
  if (props.format === 'currency') {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: props.currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(Number(props.value) || 0)
  } else if (props.format === 'number') {
    return (Number(props.value) || 0).toLocaleString('en-IN')
  }
  return props.value
})

const valueClass = computed(() => {
  if (props.change === undefined) return ''
  return props.change >= 0 ? 'positive' : 'negative'
})

const changeClass = computed(() => {
  if (props.change === undefined) return ''
  return props.change >= 0 ? 'positive' : 'negative'
})

const changeIcon = computed(() => {
  if (props.change === undefined) return ''
  return props.change >= 0 ? '↑' : '↓'
})
</script>

<style scoped>
.data-card {
  position: relative;
  min-width: 0;
  padding: 18px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
  text-align: left;
  transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
}

.data-card::after {
  position: absolute;
  width: 82px;
  height: 82px;
  top: -38px;
  right: -32px;
  border-radius: 50%;
  background: var(--card-accent, #edf2f7);
  content: "";
  opacity: 0.55;
}

.data-card.primary {
  --card-accent: #dce7ff;
}

.data-card.positive {
  --card-accent: #d5f3e7;
}

.data-card.violet {
  --card-accent: #e8defe;
}

.data-card.clickable {
  cursor: pointer;
}

.data-card.clickable:hover {
  border-color: var(--color-border-strong);
  box-shadow: 0 9px 24px rgba(21, 34, 56, 0.08);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.card-header h3 {
  margin: 0;
  color: var(--color-text-soft);
  font-size: 0.69rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.card-icon {
  position: relative;
  z-index: 1;
  display: grid;
  width: 27px;
  height: 27px;
  flex: 0 0 27px;
  place-items: center;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.85);
  color: var(--color-primary-dark);
  font-size: 0.63rem;
  font-weight: 850;
}

.card-body {
  margin-top: 13px;
}

.value {
  overflow: hidden;
  color: var(--color-text);
  font-size: clamp(1.35rem, 2.2vw, 1.78rem);
  font-variant-numeric: tabular-nums;
  font-weight: 780;
  letter-spacing: -0.035em;
  line-height: 1.15;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.value.positive {
  color: var(--color-positive);
}

.value.negative {
  color: var(--color-negative);
}

.change {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  font-size: 0.75rem;
  font-weight: 750;
}

.change.positive {
  color: var(--color-positive);
}

.change.negative {
  color: var(--color-negative);
}

.change-icon {
  font-size: 16px;
}

.subtitle {
  margin: 7px 0 0;
  overflow: hidden;
  color: var(--color-text-faint);
  font-size: 0.7rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
