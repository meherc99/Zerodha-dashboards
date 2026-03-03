<template>
  <div class="portfolio-summary">
    <DataCard
      title="Total Value"
      :value="summary?.current_value || 0"
      format="currency"
    />
    <DataCard
      title="Total P&L"
      :value="summary?.total_pnl || 0"
      :change="summary?.total_pnl_percentage || 0"
      format="currency"
    />
    <DataCard
      title="Day Change"
      :value="summary?.day_change || 0"
      format="currency"
    />
    <DataCard
      title="Holdings"
      :value="summary?.total_holdings || 0"
      format="number"
      subtitle="Total Positions"
    />
  </div>
</template>

<script setup>
import DataCard from '@/components/common/DataCard.vue'

defineProps({
  summary: {
    type: Object,
    default: null
  }
})
</script>

<style scoped>
.portfolio-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

@media (max-width: 768px) {
  .portfolio-summary {
    grid-template-columns: 1fr;
  }
}
</style>
