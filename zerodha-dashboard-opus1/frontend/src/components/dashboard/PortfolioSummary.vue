<template>
  <div class="portfolio-summary">
    <DataCard
      :title="valueTitle"
      :value="summary?.current_value || 0"
      format="currency"
      :currency="currency"
      icon="₹"
      tone="primary"
      :subtitle="dayChangeSubtitle"
    />
    <DataCard
      title="Invested"
      :value="summary?.total_investment || 0"
      format="currency"
      :currency="currency"
      icon="IV"
      subtitle="Capital invested"
    />
    <DataCard
      :title="returnTitle"
      :value="summary?.total_pnl || 0"
      :change="summary?.total_pnl_percentage || 0"
      format="currency"
      :currency="currency"
      icon="↗"
      :tone="(summary?.total_pnl || 0) >= 0 ? 'positive' : 'neutral'"
    />
    <DataCard
      title="Holdings"
      :value="summary?.total_holdings || 0"
      format="number"
      icon="#"
      tone="violet"
      subtitle="Total positions"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import DataCard from '@/components/common/DataCard.vue'

const props = defineProps({
  summary: {
    type: Object,
    default: null
  },
  currency: {
    type: String,
    default: 'INR'
  },
  valueTitle: {
    type: String,
    default: 'Total Value'
  },
  valueSubtitle: {
    type: String,
    default: 'Current market value'
  },
  returnTitle: {
    type: String,
    default: 'Overall return'
  }
})

const dayChangeSubtitle = computed(() => {
  const value = Number(props.summary?.day_change || 0)
  if (!value) return props.valueSubtitle
  const formatted = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: props.currency,
    maximumFractionDigits: 0
  }).format(Math.abs(value))
  return `${value >= 0 ? '+' : '−'}${formatted} today`
})
</script>

<style scoped>
.portfolio-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

@media (max-width: 1120px) {
  .portfolio-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 540px) {
  .portfolio-summary {
    grid-template-columns: 1fr;
  }
}
</style>
