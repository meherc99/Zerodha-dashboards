<template>
  <div class="chart-container">
    <Doughnut :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(ArcElement, Tooltip, Legend)

const props = defineProps({
  data: {
    type: Array,
    required: true,
    default: () => []
  },
  title: {
    type: String,
    default: 'Spending by Category'
  }
})

const chartData = computed(() => {
  const labels = props.data.map(d => d.category || 'Uncategorized')
  const values = props.data.map(d => Math.abs(d.total || 0))

  return {
    labels,
    datasets: [{
      data: values,
      backgroundColor: [
        '#ef4444', // red
        '#f59e0b', // amber
        '#10b981', // green
        '#3b82f6', // blue
        '#8b5cf6', // violet
        '#ec4899', // pink
        '#14b8a6', // teal
        '#f97316', // orange
        '#6366f1', // indigo
        '#a855f7', // purple
        '#06b6d4', // cyan
        '#84cc16', // lime
        '#f43f5e', // rose
        '#eab308'  // yellow
      ],
      borderWidth: 2,
      borderColor: '#fff',
      hoverOffset: 8
    }]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '60%',
  plugins: {
    legend: {
      position: 'right',
      labels: {
        boxWidth: 12,
        padding: 12,
        font: {
          size: 11
        },
        generateLabels: (chart) => {
          const data = chart.data
          return data.labels.map((label, i) => {
            const value = data.datasets[0].data[i]
            const total = data.datasets[0].data.reduce((a, b) => a + b, 0)
            const percentage = ((value / total) * 100).toFixed(1)
            return {
              text: `${label} (${percentage}%)`,
              fillStyle: data.datasets[0].backgroundColor[i],
              hidden: false,
              index: i
            }
          })
        }
      }
    },
    title: {
      display: !!props.title,
      text: props.title,
      font: {
        size: 16,
        weight: 'bold'
      },
      padding: {
        bottom: 20
      }
    },
    tooltip: {
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      padding: 12,
      cornerRadius: 8,
      callbacks: {
        label: (context) => {
          const label = context.label || ''
          const value = context.parsed || 0
          const total = context.dataset.data.reduce((a, b) => a + b, 0)
          const percentage = ((value / total) * 100).toFixed(1)
          return `${label}: ₹${value.toLocaleString('en-IN')} (${percentage}%)`
        }
      }
    }
  }
}
</script>

<style scoped>
.chart-container {
  position: relative;
  height: 300px;
  width: 100%;
  background: white;
  border-radius: 8px;
  padding: 16px;
}
</style>
