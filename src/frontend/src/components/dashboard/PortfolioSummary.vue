<template>
  <div class="portfolio-summary">
    <DataCard
      :title="valueTitle"
      :value="summary?.current_value || 0"
      format="currency"
      :currency="currency"
      icon="₹"
      tone="primary"
      :subtitle="valueSubtitle"
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
      title="Day change"
      :value="summary?.day_change || 0"
      :change="summary?.day_change_percentage !== undefined ? Number(summary.day_change_percentage) : undefined"
      format="currency"
      :currency="currency"
      icon="~"
      :tone="(summary?.day_change || 0) >= 0 ? 'positive' : 'neutral'"
      subtitle="Today vs. previous close"
    />
  </div>
</template>

<script setup>
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
