<template>
  <div class="heatmap-container">
    <div class="heatmap-grid">
      <div
        v-for="item in sortedData"
        :key="item.symbol"
        class="heatmap-cell"
        :class="getCellClass(item.value)"
        :style="{ flex: getCellSize(item.value) }"
      >
        <div class="cell-content">
          <div class="symbol">{{ item.symbol }}</div>
          <div class="value">{{ formatValue(item.value) }}%</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: {
    type: Array,
    required: true,
    default: () => []
  }
})

const sortedData = computed(() => {
  return [...props.data].sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
})

const getCellClass = (value) => {
  if (value > 5) return 'gain-high'
  if (value > 0) return 'gain-low'
  if (value < -5) return 'loss-high'
  if (value < 0) return 'loss-low'
  return 'neutral'
}

const getCellSize = (value) => {
  const absValue = Math.abs(value)
  return Math.max(absValue * 2, 5)
}

const formatValue = (value) => {
  return value >= 0 ? `+${value.toFixed(2)}` : value.toFixed(2)
}
</script>

<style scoped>
.heatmap-container {
  width: 100%;
  height: 300px;
  overflow: auto;
}

.heatmap-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 10px;
}

.heatmap-cell {
  min-width: 80px;
  min-height: 60px;
  padding: 8px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  cursor: pointer;
}

.heatmap-cell:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.cell-content {
  text-align: center;
  color: white;
}

.symbol {
  font-size: 12px;
  font-weight: bold;
  margin-bottom: 4px;
}

.value {
  font-size: 14px;
}

.gain-high {
  background-color: #10b981;
}

.gain-low {
  background-color: #6ee7b7;
}

.neutral {
  background-color: #94a3b8;
}

.loss-low {
  background-color: #fca5a5;
}

.loss-high {
  background-color: #ef4444;
}
</style>
