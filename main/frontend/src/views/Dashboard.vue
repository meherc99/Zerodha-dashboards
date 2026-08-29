<template>
  <div class="dashboard-layout">
    <header class="dashboard-header">
      <div class="header-copy">
        <p class="eyebrow">{{ scopeEyebrow }}</p>
        <h1>{{ scopeTitle }}</h1>
        <div class="freshness-row">
          <span
            class="status-chip"
            :class="freshnessClass"
          >
            {{ freshnessLabel }}
          </span>
          <span v-if="isDemoMode" class="status-chip demo">Demo data</span>
          <span v-if="accountSyncLabel" class="sync-detail">{{ accountSyncLabel }}</span>
        </div>
      </div>
      <div class="header-actions">
        <AccountSelector
          v-model="selectedAccount"
          :accounts="accountsStore.activeAccounts"
          :loading="accountsStore.loading || holdingsStore.loading"
        />
        <button
          type="button"
          class="primary-button sync-btn"
          :disabled="holdingsStore.loading || accountsStore.loading"
          @click="handleSync"
        >
          <span class="sync-icon" :class="{ spinning: holdingsStore.loading }" aria-hidden="true">↻</span>
          <span>{{ holdingsStore.loading ? 'Updating…' : 'Sync portfolio' }}</span>
        </button>
      </div>
    </header>

    <div class="dashboard-body">
      <Sidebar />
      <main class="dashboard-main">
        <div
          v-if="combinedError && hasPortfolioData"
          class="error-banner"
          role="alert"
        >
          <div>
            <strong>Some portfolio data could not be refreshed.</strong>
            <span>{{ combinedError }} Showing the last available data.</span>
          </div>
          <button type="button" class="secondary-button" @click="loadData">Try again</button>
        </div>

        <LoadingSpinner
          v-if="initialLoading"
          class="initial-loader"
          message="Loading your portfolio…"
        />

        <div v-else-if="combinedError && !hasPortfolioData" class="state-wrap">
          <section class="state-panel" role="alert">
            <span class="state-symbol error" aria-hidden="true">!</span>
            <h2>We couldn’t load this portfolio</h2>
            <p>{{ combinedError }}</p>
            <div class="state-actions">
              <button type="button" class="primary-button" @click="loadData">Try again</button>
              <router-link to="/accounts" class="secondary-button">Check accounts</router-link>
            </div>
          </section>
        </div>

        <router-view v-else />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useHoldingsStore } from '@/stores/holdings'
import { useAccountsStore } from '@/stores/accounts'
import { useUiStore } from '@/stores/ui'
import { format, formatDistanceToNowStrict } from 'date-fns'

import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import AccountSelector from '@/components/dashboard/AccountSelector.vue'
import Sidebar from '@/components/dashboard/Sidebar.vue'

const holdingsStore = useHoldingsStore()
const router = useRouter()
const accountsStore = useAccountsStore()
const uiStore = useUiStore()

const selectedAccount = computed({
  get: () => accountsStore.currentAccount,
  set: accountId => accountsStore.setCurrentAccount(accountId || null)
})
const hasLoaded = ref(false)
const scopeInitialized = ref(false)
const isDemoMode = import.meta.env.VITE_DEMO_MODE === 'true'

const selectedAccountRecord = computed(() => {
  return accountsStore.accounts.find(account => Number(account.id) === Number(selectedAccount.value))
})

const scopeEyebrow = computed(() => selectedAccount.value ? 'Individual portfolio' : 'Consolidated household')
const scopeTitle = computed(() => selectedAccountRecord.value?.account_name || 'Family portfolio')
const hasPortfolioData = computed(() => holdingsStore.holdings.length > 0 || Boolean(holdingsStore.summary))
const initialLoading = computed(() => !hasLoaded.value && (holdingsStore.loading || accountsStore.loading))
const combinedError = computed(() => (
  holdingsStore.error
  || accountsStore.error
  || holdingsStore.analyticsError
))

const freshnessAgeMinutes = computed(() => {
  if (!holdingsStore.lastUpdated) return null
  return (Date.now() - new Date(holdingsStore.lastUpdated).getTime()) / 60000
})

const freshnessLabel = computed(() => {
  if (!holdingsStore.lastUpdated) return 'Not loaded yet'
  return `Loaded ${formatDistanceToNowStrict(new Date(holdingsStore.lastUpdated), { addSuffix: true })}`
})

const freshnessClass = computed(() => {
  if (!holdingsStore.lastUpdated) return ''
  return freshnessAgeMinutes.value > 30 ? 'stale' : 'live'
})

const accountSyncLabel = computed(() => {
  const syncDate = selectedAccountRecord.value?.last_synced_at
  if (!syncDate) return ''
  try {
    return `Broker sync ${format(new Date(syncDate), 'd MMM, h:mm a')}`
  } catch {
    return ''
  }
})

const handleSync = async () => {
  const accountId = selectedAccount.value || null
  try {
    const result = await holdingsStore.syncHoldings(accountId)
    if (!result || (selectedAccount.value || null) !== accountId) return

    const analyticsResults = await Promise.allSettled([
      holdingsStore.fetchSectorBreakdown(accountId),
      holdingsStore.fetchPortfolioHistory(accountId, 30)
    ])
    holdingsStore.analyticsError = analyticsResults.some(
      analyticsResult => analyticsResult.status === 'rejected'
    )
      ? 'Portfolio analytics are temporarily unavailable.'
      : null
    uiStore.addNotification({
      type: 'success',
      message: 'Portfolio synced successfully.'
    })
  } catch (error) {
    // Refresh accounts so needs_reauth is up-to-date
    await accountsStore.fetchAccounts()
    // If a token expired, navigate to Accounts page and auto-open reconnect
    const reauthAccount = accountsStore.accounts.find(a => a.needs_reauth)
    if (reauthAccount) {
      router.push({ path: '/accounts', query: { reauth: reauthAccount.id } })
      return
    }
    uiStore.addNotification({
      type: 'error',
      message: holdingsStore.error || 'Failed to sync portfolio.'
    })
  }
}

const loadData = async () => {
  const accountId = selectedAccount.value || null

  try {
    const result = await holdingsStore.loadPortfolio(accountId, 30)
    if (!result.stale) {
      hasLoaded.value = true
    }
  } catch {
    // The store exposes a sanitized user-facing error and the template owns recovery.
    hasLoaded.value = true
  }
}

watch(selectedAccount, (accountId) => {
  if (!scopeInitialized.value) return
  hasLoaded.value = false
  loadData()
})

onMounted(async () => {
  await accountsStore.fetchAccounts()
  if (
    selectedAccount.value
    && !accountsStore.activeAccounts.some(
      account => Number(account.id) === Number(selectedAccount.value)
    )
  ) {
    selectedAccount.value = null
  }
  scopeInitialized.value = true
  await loadData()
})
</script>

<style scoped>
.dashboard-layout {
  min-height: calc(100vh - 64px);
}

.dashboard-header {
  display: flex;
  min-height: 110px;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 20px 28px;
  border-bottom: 1px solid var(--color-border);
  background: rgba(4, 12, 24, 0.60);
  backdrop-filter: blur(12px);
}

.dashboard-header h1 {
  margin: 0;
  color: var(--color-text);
  font-size: clamp(1.45rem, 2.8vw, 2rem);
  letter-spacing: -0.035em;
}

.freshness-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.sync-detail {
  color: var(--color-text-faint);
  font-size: 0.72rem;
}

.header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
}

.sync-btn {
  min-height: 42px;
  white-space: nowrap;
}

.sync-icon {
  font-size: 1.08rem;
  line-height: 1;
}

.sync-icon.spinning {
  animation: spin 850ms linear infinite;
}

.dashboard-body {
  display: flex;
  align-items: flex-start;
}

.dashboard-main {
  min-width: 0;
  flex: 1;
}

.error-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin: 18px 28px 0;
  padding: 13px 15px;
  border: 1px solid rgba(255, 69, 96, 0.28);
  border-left: 3px solid var(--color-negative);
  border-radius: 12px;
  background: var(--color-negative-soft);
  color: var(--color-negative);
}

.error-banner div {
  display: flex;
  flex-direction: column;
  font-size: 0.82rem;
}

.error-banner span {
  margin-top: 2px;
  color: var(--color-text-soft);
}

.error-banner .secondary-button {
  min-height: 36px;
}

.initial-loader {
  min-height: 55vh;
}

.state-wrap {
  padding: 28px;
}

.state-symbol {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 50%;
  background: var(--color-negative-soft);
  color: var(--color-negative);
  font-size: 1.2rem;
  font-weight: 850;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .dashboard-layout {
    min-height: calc(100vh - 58px);
  }

  .dashboard-header {
    flex-direction: column;
    align-items: stretch;
    padding: 17px 14px;
  }

  .header-actions {
    width: 100%;
    align-items: stretch;
    flex-direction: column;
  }

  .dashboard-body {
    flex-direction: column;
  }

  .sync-btn {
    width: 100%;
  }

  .error-banner {
    align-items: flex-start;
    flex-direction: column;
    margin: 14px 14px 0;
  }

  .state-wrap {
    padding: 18px 14px;
  }
}
</style>
