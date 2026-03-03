<template>
  <div class="data-card" :class="{ clickable: onClick }">
    <div class="card-header">
      <h3>{{ title }}</h3>
    </div>
    <div class="card-body">
      <div class="value" :class="valueClass">{{ formattedValue }}</div>
      <div v-if="change !== undefined" class="change" :class="changeClass">
        <span class="change-icon">{{ changeIcon }}</span>
        <span>{{ Math.abs(change).toFixed(2) }}%</span>
      </div>
      <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
    </div>
  </div>
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
  onClick: {
    type: Function,
    default: null
  }
})

const formattedValue = computed(() => {
  if (props.format === 'currency') {
    return `₹${Number(props.value).toLocaleString('en-IN')}`
  } else if (props.format === 'number') {
    return Number(props.value).toLocaleString('en-IN')
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
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.data-card.clickable {
  cursor: pointer;
}

.data-card.clickable:hover {
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.card-header h3 {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-body {
  margin-top: 12px;
}

.value {
  font-size: 28px;
  font-weight: bold;
  color: #111827;
}

.value.positive {
  color: #10b981;
}

.value.negative {
  color: #ef4444;
}

.change {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  font-size: 14px;
  font-weight: 600;
}

.change.positive {
  color: #10b981;
}

.change.negative {
  color: #ef4444;
}

.change-icon {
  font-size: 16px;
}

.subtitle {
  margin-top: 8px;
  font-size: 12px;
  color: #9ca3af;
}
</style>
