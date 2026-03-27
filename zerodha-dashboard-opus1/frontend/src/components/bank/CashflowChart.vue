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
import { format, parseISO } from 'date-fns'

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
    default: 'Weekly Cashflow'
  }
})

const chartData = computed(() => {
  const labels = props.data.map(d => {
    try {
      return `Week ${format(parseISO(d.week_start), 'MMM dd')}`
    } catch {
      return d.week_start || 'Unknown'
    }
  })
  const credits = props.data.map(d => Math.abs(d.total_credit || 0))
  const debits = props.data.map(d => Math.abs(d.total_debit || 0))

  return {
    labels,
    datasets: [
      {
        label: 'Income',
        data: credits,
        backgroundColor: 'rgba(16, 185, 129, 0.8)',
        borderColor: '#10b981',
        borderWidth: 1,
        borderRadius: 4
      },
      {
        label: 'Expenses',
        data: debits,
        backgroundColor: 'rgba(239, 68, 68, 0.8)',
        borderColor: '#ef4444',
        borderWidth: 1,
        borderRadius: 4
      }
    ]
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
      position: 'top',
      labels: {
        boxWidth: 12,
        padding: 12,
        font: {
          size: 11
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
          return `${context.dataset.label}: ₹${context.parsed.y.toLocaleString('en-IN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
          })}`
        },
        footer: (tooltipItems) => {
          const income = tooltipItems[0]?.parsed.y || 0
          const expense = tooltipItems[1]?.parsed.y || 0
          const net = income - expense
          return `Net: ₹${net.toLocaleString('en-IN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
          })}`
        }
      }
    }
  },
  scales: {
    x: {
      grid: {
        display: false
      },
      ticks: {
        font: {
          size: 11
        }
      }
    },
    y: {
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
