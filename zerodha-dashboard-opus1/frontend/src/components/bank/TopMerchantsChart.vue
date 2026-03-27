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

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
)

const props = defineProps({
  data: {
    type: Array,
    required: true,
    default: () => []
  },
  title: {
    type: String,
    default: 'Top Merchants'
  }
})

const chartData = computed(() => {
  const labels = props.data.map(d => d.merchant || 'Unknown')
  const values = props.data.map(d => Math.abs(d.total_spent || 0))

  return {
    labels,
    datasets: [{
      label: 'Total Spent',
      data: values,
      backgroundColor: 'rgba(59, 130, 246, 0.8)',
      borderColor: '#3b82f6',
      borderWidth: 1,
      borderRadius: 4
    }]
  }
})

const chartOptions = {
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false
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
          const merchant = context.label
          const amount = context.parsed.x
          // Get transaction count from data
          const dataPoint = props.data[context.dataIndex]
          const count = dataPoint?.transaction_count || 0
          return [
            `Amount: ₹${amount.toLocaleString('en-IN', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2
            })}`,
            `Transactions: ${count}`
          ]
        }
      }
    }
  },
  scales: {
    x: {
      beginAtZero: true,
      grid: {
        color: 'rgba(0, 0, 0, 0.05)'
      },
      ticks: {
        callback: (value) => `₹${(value / 1000).toFixed(0)}k`,
        font: {
          size: 11
        }
      }
    },
    y: {
      grid: {
        display: false
      },
      ticks: {
        font: {
          size: 11
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
