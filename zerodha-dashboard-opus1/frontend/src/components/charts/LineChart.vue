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
      borderColor: '#36A2EB',
      backgroundColor: 'rgba(54, 162, 235, 0.1)',
      fill: true,
      tension: 0.4,
      pointRadius: 3,
      pointHoverRadius: 6
    }]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false,
  },
  plugins: {
    legend: {
      display: true,
      position: 'top'
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
          return `Value: ₹${context.parsed.y.toLocaleString('en-IN')}`
        }
      }
    }
  },
  scales: {
    x: {
      grid: {
        display: false
      }
    },
    y: {
      beginAtZero: false,
      ticks: {
        callback: (value) => `₹${(value / 1000).toFixed(0)}k`
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
}
</style>
