<template>
  <div class="chart-container">
    <Pie :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Pie } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(ArcElement, Tooltip, Legend)

const props = defineProps({
  data: {
    type: Object,
    required: true,
    default: () => ({ labels: [], values: [] })
  },
  title: {
    type: String,
    default: ''
  },
  currency: {
    type: String,
    default: 'INR'
  }
})

const OPUS_COLORS = [
  '#3d7eff', '#8b5cf6', '#ec4899', '#ef4444', '#f97316',
  '#f59e0b', '#10b981', '#06b6d4', '#3b82f6', '#14b8a6',
  '#a855f7', '#e879f9', '#fb7185', '#fbbf24', '#34d399',
  '#22d3ee', '#60a5fa', '#c084fc',
]

const chartData = computed(() => ({
  labels: props.data.labels || [],
  datasets: [{
    data: props.data.values || [],
    backgroundColor: props.data.colors || OPUS_COLORS,
    borderWidth: 1,
    borderColor: '#0b1628',
    hoverOffset: 14,
  }]
}))

const moneyFormatter = computed(() => new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: props.currency,
  maximumFractionDigits: 0
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: { animateScale: true },
  plugins: {
    legend: {
      position: 'right',
      labels: {
        boxWidth: 11,
        padding: 12,
        color: '#6a94b8',
        font: { size: 11 }
      }
    },
    tooltip: {
      backgroundColor: '#060c18',
      borderColor: '#162438',
      borderWidth: 1,
      titleColor: '#dde8f7',
      bodyColor: '#6a94b8',
      callbacks: {
        label: (context) => {
          const label = context.label || ''
          const value = context.parsed || 0
          const total = context.dataset.data.reduce((a, b) => a + b, 0)
          const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0'
          return `${label}: ${moneyFormatter.value.format(value)} (${percentage}%)`
        }
      }
    }
  }
}))
</script>

<style scoped>
.chart-container {
  position: relative;
  height: 300px;
  width: 100%;
}
</style>
