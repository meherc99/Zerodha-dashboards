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
    backgroundColor: props.data.colors || '#3d7eff',
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
    tooltip: {
      backgroundColor: '#060c18',
      borderColor: '#162438',
      borderWidth: 1,
      titleColor: '#dde8f7',
      bodyColor: '#6a94b8',
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
          grid: { color: 'rgba(42, 53, 72, 0.8)' },
          ticks: { color: '#3a5a78', callback: value => moneyFormatter.value.format(value) }
        },
        y: {
          grid: { display: false },
          ticks: { color: '#6a94b8' }
        }
      }
    : {
        x: {
          grid: { display: false },
          ticks: { color: '#6a94b8' }
        },
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(42, 53, 72, 0.8)' },
          ticks: { color: '#3a5a78', callback: value => moneyFormatter.value.format(value) }
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
