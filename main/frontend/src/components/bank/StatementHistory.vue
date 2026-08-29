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
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
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
  color: var(--color-text-soft);
  font-size: 0.8rem;
}

.refresh-btn,
.primary-action,
.delete-action {
  padding: 7px 11px;
  border-radius: 8px;
  background: var(--color-surface-strong);
  font-size: 0.75rem;
  font-weight: 650;
  cursor: pointer;
  transition: border-color 150ms, background 150ms;
}

.refresh-btn {
  border: 1px solid var(--color-border-strong);
  color: var(--color-text-soft);
}

.refresh-btn:hover {
  border-color: var(--color-border-glow);
  color: var(--color-text);
}

.statement-list {
  margin: 17px 0 0;
  padding: 0;
  border-top: 1px solid var(--color-border);
  list-style: none;
}

.statement-list li {
  gap: 12px;
  padding: 13px 0;
  border-bottom: 1px solid var(--color-border);
}

.statement-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
}

.statement-copy strong {
  font-size: 0.82rem;
  color: var(--color-text);
}

.statement-copy span,
.statement-copy small {
  margin-top: 2px;
  color: var(--color-text-soft);
  font-size: 0.7rem;
}

.statement-copy small {
  color: var(--color-negative);
}

.statement-status {
  padding: 3px 7px;
  border-radius: 999px;
  background: var(--color-surface-strong);
  color: var(--color-text-soft);
  font-size: 0.68rem;
  font-weight: 700;
  border: 1px solid var(--color-border-strong);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.statement-status.review,
.statement-status.approved {
  background: var(--color-positive-soft);
  border-color: rgba(13, 217, 142, 0.25);
  color: var(--color-positive);
}

.statement-status.failed {
  background: var(--color-negative-soft);
  border-color: rgba(255, 69, 96, 0.25);
  color: var(--color-negative);
}

.statement-actions {
  gap: 7px;
}

.primary-action {
  border: 1px solid rgba(61, 126, 255, 0.3);
  color: var(--color-primary-dark);
}

.primary-action:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.delete-action {
  border: 1px solid rgba(255, 69, 96, 0.3);
  color: var(--color-negative);
}

.delete-action:hover {
  border-color: var(--color-negative);
  background: var(--color-negative-soft);
}

.statement-error {
  color: var(--color-negative);
  font-size: 0.8rem;
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
