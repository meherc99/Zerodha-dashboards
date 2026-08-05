<template>
  <div class="chart-container">
    <Bar :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

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
  horizontal: {
    type: Boolean,
    default: false
  },
  currency: {
    type: String,
    default: 'INR'
  }
})

const chartData = computed(() => ({
  labels: props.data.labels || [],
  datasets: [{
    label: props.data.label || 'Value',
    data: props.data.values || [],
    backgroundColor: props.data.colors || '#4f7df3',
    borderRadius: 6,
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
  indexAxis: props.horizontal ? 'y' : 'x',
  plugins: {
    legend: {
      display: false
    },
    title: {
      display: !!props.title,
      text: props.title,
      font: {
        size: 14,
        weight: 'bold'
      }
    },
    tooltip: {
      callbacks: {
        label: (context) => {
          return moneyFormatter.value.format(Number(context.raw || 0))
        }
      }
    }
  },
  scales: props.horizontal
    ? {
        x: {
          beginAtZero: true,
          grid: { color: 'rgba(203, 213, 225, 0.35)' },
          ticks: { callback: value => moneyFormatter.value.format(value) }
        },
        y: {
          grid: { display: false },
          ticks: { color: '#5f6f82' }
        }
      }
    : {
        x: {
          grid: { display: false },
          ticks: { color: '#5f6f82' }
        },
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(203, 213, 225, 0.35)' },
          ticks: { callback: value => moneyFormatter.value.format(value) }
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
