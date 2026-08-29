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
/* ─── Base card ─────────────────────────────────── */
.data-card {
  position: relative;
  min-width: 0;
  padding: 20px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  text-align: left;
  transition: border-color 200ms ease, box-shadow 200ms ease, transform 200ms ease;
}

/* top-edge glow line */
.data-card::before {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  background: var(--card-top-line, linear-gradient(90deg, transparent, rgba(61, 126, 255, 0.4), transparent));
  content: "";
  opacity: 0.7;
}

/* subtle radial highlight */
.data-card::after {
  position: absolute;
  width: 100px;
  height: 100px;
  top: -40px;
  right: -28px;
  border-radius: 50%;
  background: var(--card-accent, rgba(61, 126, 255, 0.07));
  content: "";
  pointer-events: none;
  filter: blur(18px);
}

/* ─── Tone variants ──────────────────────────────── */
.data-card.primary {
  --card-accent:    rgba(61, 126, 255, 0.14);
  --card-top-line: linear-gradient(90deg, transparent, rgba(61, 126, 255, 0.6), transparent);
  border-color: rgba(61, 126, 255, 0.22);
}

.data-card.positive {
  --card-accent:    rgba(13, 217, 142, 0.14);
  --card-top-line: linear-gradient(90deg, transparent, rgba(13, 217, 142, 0.55), transparent);
  border-color: rgba(13, 217, 142, 0.2);
}

.data-card.violet {
  --card-accent:    rgba(167, 139, 250, 0.14);
  --card-top-line: linear-gradient(90deg, transparent, rgba(167, 139, 250, 0.55), transparent);
  border-color: rgba(167, 139, 250, 0.22);
}

/* ─── Interactive ────────────────────────────────── */
.data-card.clickable {
  cursor: pointer;
}

.data-card.clickable:hover {
  border-color: var(--color-border-glow);
  box-shadow: var(--shadow-card), var(--shadow-glow);
  transform: translateY(-2px);
}

/* ─── Inner layout ───────────────────────────────── */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.card-header h3 {
  margin: 0;
  color: var(--color-text-soft);
  font-size: 0.67rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.card-icon {
  position: relative;
  z-index: 1;
  display: grid;
  width: 26px;
  height: 26px;
  flex: 0 0 26px;
  place-items: center;
  border: 1px solid var(--color-border-strong);
  border-radius: 8px;
  background: var(--color-surface-strong);
  color: var(--color-primary-dark);
  font-size: 0.62rem;
  font-weight: 850;
  transition: box-shadow 200ms ease;
}

.data-card.primary .card-icon {
  border-color: rgba(61, 126, 255, 0.35);
  background: rgba(61, 126, 255, 0.12);
  color: var(--color-primary-dark);
}

.data-card.positive .card-icon {
  border-color: rgba(13, 217, 142, 0.3);
  background: rgba(13, 217, 142, 0.1);
  color: var(--color-positive);
}

.card-body {
  margin-top: 14px;
}

/* ─── Value display ──────────────────────────────── */
.value {
  overflow: hidden;
  color: var(--color-text);
  font-size: clamp(1.3rem, 2.2vw, 1.72rem);
  font-variant-numeric: tabular-nums;
  font-weight: 760;
  letter-spacing: -0.04em;
  line-height: 1.15;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.value.positive { color: var(--color-positive); }
.value.negative { color: var(--color-negative); }

/* ─── Change badge ───────────────────────────────── */
.change {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 750;
}

.change.positive {
  color: var(--color-positive);
  background: var(--color-positive-soft);
}

.change.negative {
  color: var(--color-negative);
  background: var(--color-negative-soft);
}

.change-icon {
  font-size: 13px;
  line-height: 1;
}

/* ─── Subtitle ───────────────────────────────────── */
.subtitle {
  margin: 8px 0 0;
  overflow: hidden;
  color: var(--color-text-faint);
  font-size: 0.68rem;
  text-overflow: ellipsis;
  white-space: nowrap;
  letter-spacing: 0.02em;
}
</style>
