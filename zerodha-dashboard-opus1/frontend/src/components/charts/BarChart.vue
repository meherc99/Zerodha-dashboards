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
  }
})

const chartData = computed(() => ({
  labels: props.data.labels || [],
  datasets: [{
    label: props.data.label || 'Value',
    data: props.data.values || [],
    backgroundColor: props.data.colors || '#36A2EB',
    borderRadius: 4,
  }]
}))

const chartOptions = {
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
          const value = context.parsed.y || context.parsed.x
          return `₹${value.toLocaleString('en-IN')}`
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
      beginAtZero: true,
      ticks: {
        callback: (value) => `₹${value.toLocaleString('en-IN')}`
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
