<template>
  <section class="statements-panel" aria-labelledby="statement-history-title">
    <div class="panel-heading">
      <div>
        <h3 id="statement-history-title">Uploaded statements</h3>
        <p>Resume parsing, review parsed transactions, or discard an unfinished upload.</p>
      </div>
      <button
        type="button"
        class="refresh-btn"
        :disabled="statements.loading"
        @click="refresh"
      >
        Refresh
      </button>
    </div>

    <p v-if="statements.error" class="statement-error" role="alert">
      {{ statements.error }}
    </p>
    <p v-else-if="statements.loading && !statements.items.length" class="empty-copy">
      Loading statements…
    </p>
    <p v-else-if="!statements.items.length" class="empty-copy">
      No statements uploaded for this account.
    </p>

    <ul v-else class="statement-list">
      <li v-for="statement in statements.items" :key="statement.id">
        <div class="statement-copy">
          <strong>{{ statementLabel(statement) }}</strong>
          <span>Uploaded {{ formatDate(statement.upload_date || statement.created_at) }}</span>
          <small v-if="statement.error_message">{{ statement.error_message }}</small>
        </div>
        <span class="statement-status" :class="statement.status">
          {{ statusLabel(statement.status) }}
        </span>
        <div class="statement-actions">
          <button
            v-if="statement.status === 'review'"
            type="button"
            class="primary-action"
            @click="review(statement)"
          >
            Review
          </button>
          <button
            v-if="['uploaded', 'failed'].includes(statement.status)"
            type="button"
            class="primary-action"
            @click="resume(statement)"
          >
            Resume parsing
          </button>
          <button
            v-if="canDelete(statement)"
            type="button"
            class="delete-action"
            @click="discard(statement)"
          >
            {{ statement.status === 'deleting' ? 'Retry delete' : 'Delete' }}
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useBankAccountsStore } from '@/stores/bankAccounts'

const props = defineProps({
  account: {
    type: Object,
    required: true
  }
})

const bankStore = useBankAccountsStore()
const { statements } = storeToRefs(bankStore)

const refresh = () => bankStore.fetchStatements(props.account.id)

const review = statement => {
  bankStore.openReviewModal(
    statement.id,
    props.account.currency,
    props.account.id
  )
}

const resume = async statement => {
  try {
    await bankStore.retryStatementParse(statement.id, props.account.id)
  } catch {
    // Recovery state and a retryable error remain visible in the upload modal.
  }
}

const canDelete = statement => {
  return ['uploaded', 'review', 'failed', 'deleting'].includes(statement.status)
}

const discard = async statement => {
  if (!confirm('Delete this uploaded statement and its PDF? This cannot be undone.')) {
    return
  }
  try {
    await bankStore.discardStatement(statement.id, props.account.id)
  } catch {
    statements.value.error = 'Failed to delete statement'
  }
}

const statementLabel = statement => {
  if (statement.statement_period_start && statement.statement_period_end) {
    return `${statement.statement_period_start} – ${statement.statement_period_end}`
  }
  return `Statement #${statement.id}`
}

const statusLabel = status => ({
  uploaded: 'Ready to parse',
  parsing: 'Parsing',
  review: 'Ready for review',
  failed: 'Needs attention',
  approved: 'Approved',
  deleting: 'Deleting',
})[status] || status

const formatDate = value => {
  if (!value) return 'date unavailable'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'date unavailable'
  return new Intl.DateTimeFormat('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  }).format(date)
}

onMounted(refresh)
</script>

<style scoped>
.statements-panel {
  margin: 0 24px 24px;
  padding: 20px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
}

.panel-heading,
.statement-list li,
.statement-actions {
  display: flex;
  align-items: center;
}

.panel-heading {
  justify-content: space-between;
  gap: 16px;
}

.panel-heading h3,
.panel-heading p {
  margin: 0;
}

.panel-heading p,
.empty-copy {
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
}

.refresh-btn,
.primary-action,
.delete-action {
  padding: 7px 11px;
  border-radius: 7px;
  background: #fff;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
}

.refresh-btn {
  border: 1px solid #d1d5db;
  color: #374151;
}

.statement-list {
  margin: 17px 0 0;
  padding: 0;
  border-top: 1px solid #e5e7eb;
  list-style: none;
}

.statement-list li {
  gap: 12px;
  padding: 13px 0;
  border-bottom: 1px solid #f0f2f5;
}

.statement-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
}

.statement-copy strong {
  font-size: 13px;
}

.statement-copy span,
.statement-copy small {
  margin-top: 2px;
  color: #6b7280;
  font-size: 11px;
}

.statement-copy small {
  color: #b91c1c;
}

.statement-status {
  padding: 4px 7px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #4b5563;
  font-size: 11px;
  font-weight: 700;
}

.statement-status.review,
.statement-status.approved {
  background: #dcfce7;
  color: #166534;
}

.statement-status.failed {
  background: #fee2e2;
  color: #991b1b;
}

.statement-actions {
  gap: 7px;
}

.primary-action {
  border: 1px solid #bfdbfe;
  color: #1d4ed8;
}

.delete-action {
  border: 1px solid #fecaca;
  color: #b91c1c;
}

.statement-error {
  color: #b91c1c;
  font-size: 13px;
}

@media (max-width: 680px) {
  .statements-panel {
    margin: 0 14px 18px;
    padding: 15px;
  }

  .statement-list li {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .statement-copy {
    flex-basis: calc(100% - 120px);
  }

  .statement-actions {
    width: 100%;
  }
}
</style>
