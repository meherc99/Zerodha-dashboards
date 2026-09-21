<template>
  <div class="chart-container">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { format, parseISO } from 'date-fns'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const props = defineProps({
  data: {
    type: Array,
    required: true,
    default: () => []
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

const chartData = computed(() => {
  const dates = props.data.map(d => {
    try {
      return format(parseISO(d.date), 'MMM dd')
    } catch {
      return d.date
    }
  })
  const values = props.data.map(d => d.total_value || 0)

  return {
    labels: dates,
    datasets: [{
      label: 'Portfolio Value',
      data: values,
      borderColor: '#3d7eff',
      backgroundColor: 'rgba(99, 102, 241, 0.12)',
      fill: true,
      tension: 0.4,
      pointRadius: 3,
      pointHoverRadius: 6
    }]
  }
})

const moneyFormatter = computed(() => new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: props.currency,
  maximumFractionDigits: 0
}))

const compactMoneyFormatter = computed(() => new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: props.currency,
  notation: 'compact',
  maximumFractionDigits: 1
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false,
  },
  plugins: {
    legend: {
      display: true,
      position: 'top',
      labels: { color: '#6a94b8', font: { size: 11 } }
    },
    tooltip: {
      backgroundColor: '#060c18',
      borderColor: '#162438',
      borderWidth: 1,
      titleColor: '#dde8f7',
      bodyColor: '#6a94b8',
      callbacks: {
        label: (context) => {
          return `Value: ${moneyFormatter.value.format(context.parsed.y)}`
        }
      }
    }
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { color: '#3a5a78' }
    },
    y: {
      beginAtZero: false,
      grid: { color: 'rgba(42, 53, 72, 0.8)' },
      ticks: {
        color: '#3a5a78',
        callback: (value) => compactMoneyFormatter.value.format(value)
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
