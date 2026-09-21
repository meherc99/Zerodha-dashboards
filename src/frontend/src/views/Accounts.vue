<template>
  <div class="accounts-page">
    <div class="page-header">
      <h1>Account Management</h1>
      <button type="button" @click="showAddModal = true" class="add-btn">+ Add Account</button>
    </div>

    <LoadingSpinner v-if="accountsStore.loading && !accountsStore.accounts.length" />

    <div v-else class="accounts-grid">
      <div v-for="account in accountsStore.accounts" :key="account.id" class="account-card">
        <div v-if="account.needs_reauth" class="reauth-banner">
          <span>⚠️ Kite token expired</span>
          <button type="button" class="reauth-banner-btn" @click="openReconnectModal(account)">Re-authenticate →</button>
        </div>
        <div class="account-header">
          <h3>{{ account.account_name }}</h3>
          <span class="status-badge" :class="{ active: account.is_active, reauth: account.needs_reauth }">
            {{ account.needs_reauth ? 'Needs Reauth' : account.is_active ? 'Active' : 'Inactive' }}
          </span>
        </div>
        <div class="account-details">
          <p><strong>Account ID:</strong> {{ account.id }}</p>
          <p v-if="!account.has_kite_credentials" class="no-kite-notice">
            <strong>Kite sync:</strong> Not configured
          </p>
          <p v-if="account.last_synced_at">
            <strong>Last Synced:</strong> {{ formatDate(account.last_synced_at) }}
          </p>
          <p v-else>
            <strong>Last Synced:</strong> Never
          </p>
        </div>
        <div class="account-actions">
          <button
            v-if="account.has_kite_credentials"
            @click="handleSync(account.id)"
            class="action-btn sync"
          >
            Sync Now
          </button>
          <button @click="toggleAccountStatus(account)" class="action-btn">
            {{ account.is_active ? 'Deactivate' : 'Activate' }}
          </button>
          <button
            v-if="account.has_kite_credentials"
            type="button"
            class="action-btn reconnect"
            @click="openReconnectModal(account)"
          >
            Reconnect
          </button>
          <button
            v-if="!account.has_kite_credentials"
            type="button"
            class="action-btn add-credentials"
            @click="openReconnectModal(account)"
          >
            Add Kite Credentials
          </button>
        </div>
      </div>

      <div v-if="accountsStore.accounts.length === 0" class="empty-state">
        <p>No accounts configured</p>
        <button @click="showAddModal = true" class="add-btn-large">
          Add Your First Account
        </button>
      </div>
    </div>

    <!-- Add Account Modal -->
    <div v-if="showAddModal" class="modal-overlay" @click="closeAddModal">
      <div
        class="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-account-title"
        @click.stop
      >
        <div class="modal-header">
          <h2 id="add-account-title">Add Zerodha Account</h2>
          <button type="button" aria-label="Close add-account dialog" @click="closeAddModal" class="close-btn">&times;</button>
        </div>
        <form @submit.prevent="handleAddAccount" class="modal-body">
          <div class="form-group">
            <label for="account-name">Account Name *</label>
            <input
              id="account-name"
              v-model="newAccount.account_name"
              type="text"
              autocomplete="off"
              placeholder="e.g., Family Member 1"
              required
            />
          </div>
          <p class="help-text kite-optional-note">
            Kite Connect credentials are optional — you can add them later to enable live sync.
            An account without credentials can still hold manually imported stocks and FD holdings.
          </p>
          <div class="form-group">
            <label for="api-key">API Key <span class="optional-label">(Optional)</span></label>
            <input
              id="api-key"
              v-model="newAccount.api_key"
              type="text"
              placeholder="Your Kite Connect API Key"
            />
          </div>
          <div class="form-group">
            <label for="api-secret">API Secret <span class="optional-label">(Optional)</span></label>
            <input
              id="api-secret"
              v-model="newAccount.api_secret"
              type="password"
              autocomplete="new-password"
              placeholder="Your Kite Connect API Secret"
            />
          </div>
          <div v-if="newAccount.api_key || newAccount.api_secret" class="helper-actions">
            <button
              type="button"
              class="secondary-btn"
              @click="handleOpenLoginUrl"
              :disabled="authLoading || !newAccount.api_key"
            >
              {{ authLoading ? 'Opening...' : 'Open Zerodha Login' }}
            </button>
          </div>
          <div v-if="newAccount.api_key || newAccount.api_secret" class="form-group">
            <label for="request-token">Request Token <span class="optional-label">(Required with API key/secret)</span></label>
            <input
              id="request-token"
              v-model="newAccount.request_token"
              type="password"
              autocomplete="off"
              placeholder="Paste the request_token from the Zerodha redirect URL"
            />
            <small>The request token is sent once to this app’s backend, which exchanges and encrypts the access token. The access token is never returned to browser JavaScript.</small>
          </div>
          <div class="modal-actions">
            <button type="button" @click="closeAddModal" class="cancel-btn">
              Cancel
            </button>
            <button type="submit" :disabled="accountsStore.loading" class="submit-btn">
              {{ accountsStore.loading ? 'Adding...' : 'Add Account' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="reconnectAccount" class="modal-overlay" @click="closeReconnectModal">
      <div
        class="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="reconnect-account-title"
        @click.stop
      >
        <div class="modal-header">
          <h2 id="reconnect-account-title">
            {{ reconnectAccount.has_kite_credentials ? 'Reconnect' : 'Add Kite Credentials \u2014' }} {{ reconnectAccount.account_name }}
          </h2>
          <button
            type="button"
            aria-label="Close reconnect dialog"
            class="close-btn"
            @click="closeReconnectModal"
          >
            &times;
          </button>
        </div>
        <form class="modal-body" @submit.prevent="handleReconnect">
          <p v-if="reconnectAccount.has_kite_credentials" class="reconnect-copy">
            Generate a fresh Kite request token, then update this existing
            account. The stored API key stays server-side and no duplicate
            account will be created.
          </p>
          <p v-else class="reconnect-copy">
            Enter your Kite Connect credentials to enable live sync for this account.
          </p>
          <template v-if="!reconnectAccount.has_kite_credentials">
            <div class="form-group">
              <label for="rc-api-key">API Key *</label>
              <input
                id="rc-api-key"
                v-model="reconnectForm.api_key"
                type="text"
                placeholder="Your Kite Connect API Key"
                required
              />
            </div>
            <div class="form-group">
              <label for="rc-api-secret">API Secret *</label>
              <input
                id="rc-api-secret"
                v-model="reconnectForm.api_secret"
                type="password"
                autocomplete="new-password"
                placeholder="Your Kite Connect API Secret"
                required
              />
            </div>
          </template>
          <div class="helper-actions">
            <button
              type="button"
              class="secondary-btn"
              :disabled="authLoading || (!reconnectAccount.has_kite_credentials && !reconnectForm.api_key)"
              @click="handleOpenReconnectLogin"
            >
              {{ authLoading ? 'Opening...' : 'Open Zerodha Login' }}
            </button>
          </div>
          <div class="form-group">
            <label for="reconnect-request-token">{{ reconnectAccount.has_kite_credentials ? 'Fresh Request Token *' : 'Request Token *' }}</label>
            <input
              id="reconnect-request-token"
              v-model="reconnectForm.request_token"
              type="password"
              autocomplete="off"
              placeholder="Paste the request_token from the Zerodha redirect URL"
              required
            />
            <small>
              The request token is submitted to update account
              #{{ reconnectAccount.id }}; the backend exchanges and encrypts
              the new access token.
            </small>
          </div>
          <div class="modal-actions">
            <button type="button" class="cancel-btn" @click="closeReconnectModal">
              Cancel
            </button>
            <button type="submit" class="submit-btn" :disabled="accountsStore.loading">
              {{ accountsStore.loading ? 'Saving...' : (reconnectAccount.has_kite_credentials ? 'Reconnect account' : 'Save credentials') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAccountsStore } from '@/stores/accounts'
import { useHoldingsStore } from '@/stores/holdings'
import { useUiStore } from '@/stores/ui'
import { format, parseISO } from 'date-fns'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { api } from '@/services/api'

const accountsStore = useAccountsStore()
const holdingsStore = useHoldingsStore()
const uiStore = useUiStore()
const authLoading = ref(false)

const showAddModal = ref(false)
const reconnectAccount = ref(null)
const reconnectForm = ref({
  api_key: '',
  api_secret: '',
  request_token: ''
})
const newAccount = ref({
  account_name: '',
  api_key: '',
  api_secret: '',
  request_token: ''
})

const formatDate = (dateStr) => {
  try {
    return format(parseISO(dateStr), 'PPpp')
  } catch {
    return dateStr
  }
}

const emptyAccountForm = () => ({
  account_name: '',
  api_key: '',
  api_secret: '',
  request_token: ''
})

const closeAddModal = () => {
  showAddModal.value = false
  newAccount.value = emptyAccountForm()
}

const openReconnectModal = account => {
  reconnectAccount.value = account
  reconnectForm.value = { api_key: '', api_secret: '', request_token: '' }
}

const closeReconnectModal = () => {
  reconnectAccount.value = null
  reconnectForm.value = { api_key: '', api_secret: '', request_token: '' }
}

const handleAddAccount = async () => {
  const { account_name, api_key, api_secret, request_token } = newAccount.value
  const hasAny = api_key || api_secret || request_token
  const hasAll = api_key && api_secret && request_token
  if (hasAny && !hasAll) {
    uiStore.addNotification({
      type: 'error',
      message: 'Provide all three Kite fields together (API key, API secret, and request token), or leave all three blank.'
    })
    return
  }
  const payload = { account_name }
  if (hasAll) {
    payload.api_key = api_key
    payload.api_secret = api_secret
    payload.request_token = request_token
  }
  try {
    await accountsStore.createAccount(payload)
    uiStore.addNotification({
      type: 'success',
      message: 'Account added successfully!'
    })
    closeAddModal()
  } catch (error) {
    uiStore.addNotification({
      type: 'error',
      message: accountsStore.error || 'Failed to add account'
    })
  }
}

const openTrustedKiteLogin = async loadLoginUrl => {
  let popup = null

  try {
    authLoading.value = true
    popup = window.open('about:blank', '_blank')
    if (popup) popup.opener = null

    const response = await loadLoginUrl()
    const loginUrl = new URL(response.data.login_url)
    const isTrustedKiteUrl = loginUrl.protocol === 'https:' && loginUrl.hostname === 'kite.zerodha.com'
    if (!isTrustedKiteUrl) {
      throw new Error('The API returned an untrusted login URL.')
    }

    if (popup) {
      popup.location.replace(loginUrl.href)
    } else {
      window.location.assign(loginUrl.href)
    }

    uiStore.addNotification({
      type: 'success',
      message: 'Zerodha login opened successfully.'
    })
  } catch (error) {
    if (popup) {
      popup.close()
    }
    uiStore.addNotification({
      type: 'error',
      message: error.response?.data?.error || 'Failed to open Zerodha login'
    })
  } finally {
    authLoading.value = false
  }
}

const handleOpenLoginUrl = () => {
  return openTrustedKiteLogin(
    () => api.getLoginUrl({ api_key: newAccount.value.api_key })
  )
}

const handleOpenReconnectLogin = () => {
  if (!reconnectAccount.value) return
  if (reconnectAccount.value.has_kite_credentials) {
    return openTrustedKiteLogin(
      () => api.getAccountLoginUrl(reconnectAccount.value.id)
    )
  }
  // No stored credentials — use the freshly entered api_key to build the URL
  return openTrustedKiteLogin(
    () => api.getLoginUrl({ api_key: reconnectForm.value.api_key })
  )
}

const handleReconnect = async () => {
  if (!reconnectAccount.value) return
  try {
    const payload = { request_token: reconnectForm.value.request_token }
    if (!reconnectAccount.value.has_kite_credentials) {
      payload.api_key = reconnectForm.value.api_key
      payload.api_secret = reconnectForm.value.api_secret
    }
    await accountsStore.updateAccount(reconnectAccount.value.id, payload)
    uiStore.addNotification({
      type: 'success',
      message: reconnectAccount.value.has_kite_credentials
        ? `${reconnectAccount.value.account_name} reconnected successfully.`
        : `Kite credentials saved for ${reconnectAccount.value.account_name}.`
    })
    closeReconnectModal()
  } catch {
    uiStore.addNotification({
      type: 'error',
      message: accountsStore.error || 'Failed to update account'
    })
  }
}

const handleSync = async (accountId) => {
  try {
    const result = await holdingsStore.syncHoldings(accountId)
    if (!result) return
    await accountsStore.fetchAccounts() // Refresh to update last_synced_at / needs_reauth
    // Auto-open reconnect modal if this account's token expired
    if (result.reauth_required?.length) {
      const account = accountsStore.accounts.find(a => result.reauth_required.includes(a.id))
      if (account) {
        openReconnectModal(account)
        return
      }
    }
    uiStore.addNotification({
      type: 'success',
      message: 'Account synced successfully!'
    })
  } catch (error) {
    // Always refresh so needs_reauth banner appears if token expired
    await accountsStore.fetchAccounts()
    // If the account now needs reauth, open the reconnect modal
    if (accountId) {
      const account = accountsStore.accounts.find(a => a.id === accountId)
      if (account?.needs_reauth) {
        openReconnectModal(account)
        return
      }
    } else {
      const reauthAccount = accountsStore.accounts.find(a => a.needs_reauth)
      if (reauthAccount) {
        openReconnectModal(reauthAccount)
        return
      }
    }
    uiStore.addNotification({
      type: 'error',
      message: holdingsStore.error || 'Failed to sync account'
    })
  }
}

const toggleAccountStatus = async (account) => {
  try {
    await accountsStore.updateAccount(account.id, {
      is_active: !account.is_active
    })
    uiStore.addNotification({
      type: 'success',
      message: `Account ${account.is_active ? 'deactivated' : 'activated'} successfully!`
    })
  } catch (error) {
    uiStore.addNotification({
      type: 'error',
      message: 'Failed to update account status'
    })
  }
}

// Load accounts on mount; auto-open reconnect modal if ?reauth=<id> is set
const route = useRoute()
onMounted(async () => {
  await accountsStore.fetchAccounts()
  const reauthId = route.query.reauth ? Number(route.query.reauth) : null
  if (reauthId) {
    const account = accountsStore.accounts.find(a => a.id === reauthId)
    if (account) openReconnectModal(account)
  }
})
</script>

<style scoped>
.accounts-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.page-header h1 {
  margin: 0;
  font-size: 1.9rem;
  color: var(--color-text);
  font-weight: 760;
  letter-spacing: -0.03em;
}

.add-btn {
  padding: 10px 20px;
  background: linear-gradient(135deg, #3d7eff, #5b6ef5);
  color: #fff;
  border: 1px solid var(--color-primary);
  border-radius: 10px;
  font-size: 0.875rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s;
  box-shadow: 0 0 18px rgba(61, 126, 255, 0.22);
}

.add-btn:hover {
  background: linear-gradient(135deg, #5090ff, #7280ff);
  box-shadow: 0 0 26px rgba(61, 126, 255, 0.38);
}

.accounts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.account-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow-card);
  transition: border-color 180ms ease, box-shadow 180ms ease;
}

.account-card:hover {
  border-color: var(--color-border-strong);
}

.reauth-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--color-warning-soft);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-left: 3px solid var(--color-warning);
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 14px;
  font-size: 0.8rem;
  color: var(--color-warning);
  font-weight: 600;
}

.reauth-banner-btn {
  background: var(--color-warning);
  color: #000;
  border: none;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 0.75rem;
  font-weight: 700;
  cursor: pointer;
}

.reauth-banner-btn:hover {
  filter: brightness(1.1);
}

.status-badge.reauth {
  background: var(--color-warning-soft);
  border-color: rgba(245, 158, 11, 0.3);
  color: var(--color-warning);
}

.account-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.account-header h3 {
  margin: 0;
  font-size: 1.05rem;
  color: var(--color-text);
  font-weight: 700;
  letter-spacing: -0.02em;
}

.status-badge {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  background: var(--color-surface-strong);
  border: 1px solid var(--color-border-strong);
  color: var(--color-text-soft);
}

.status-badge.active {
  background: var(--color-positive-soft);
  border-color: rgba(13, 217, 142, 0.25);
  color: var(--color-positive);
}

.account-details {
  margin-bottom: 15px;
}

.account-details p {
  margin: 8px 0;
  font-size: 0.83rem;
  color: var(--color-text-soft);
}

.account-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  flex: 1;
  padding: 8px 14px;
  border: 1px solid var(--color-border-strong);
  background: var(--color-surface-strong);
  color: var(--color-text-soft);
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 650;
  cursor: pointer;
  transition: all 0.18s;
}

.action-btn:hover {
  border-color: var(--color-border-glow);
  color: var(--color-text);
}

.action-btn.sync {
  background: linear-gradient(135deg, #3d7eff, #5b6ef5);
  color: #fff;
  border-color: var(--color-primary);
  box-shadow: 0 0 14px rgba(61, 126, 255, 0.2);
}

.action-btn.sync:hover {
  background: linear-gradient(135deg, #5090ff, #7280ff);
  box-shadow: 0 0 22px rgba(61, 126, 255, 0.35);
}

.action-btn.reconnect {
  border-color: rgba(61, 126, 255, 0.3);
  color: var(--color-primary-dark);
}

.action-btn.reconnect:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.action-btn.add-credentials {
  border-color: rgba(245, 158, 11, 0.3);
  color: var(--color-warning);
  background: var(--color-warning-soft);
}

.no-kite-notice {
  color: var(--color-text-soft);
  font-size: 0.75rem;
}

.optional-label {
  font-weight: 400;
  color: var(--color-text-soft);
  font-size: 0.85em;
}

.kite-optional-note {
  font-size: 13px;
  color: var(--color-text-soft);
  line-height: 1.5;
  margin: 0 0 12px;
  padding: 10px 12px;
  background: var(--color-positive-soft);
  border-left: 3px solid #22c55e;
  border-radius: 4px;
}

.reconnect-copy {
  margin: 0 0 18px;
  color: var(--color-text-soft);
  font-size: 13px;
  line-height: 1.5;
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-faint);
}

.add-btn-large {
  margin-top: 20px;
  padding: 12px 24px;
  background: #10b981;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--color-surface);
  border-radius: 8px;
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  margin: 20px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border: 1px solid var(--color-border);
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 28px;
  cursor: pointer;
  color: var(--color-text-soft);
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: var(--color-text);
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: var(--color-text-soft);
  font-size: 14px;
}

.form-group input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border-strong);
  border-radius: 6px;
  font-size: 14px;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.helper-actions {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.secondary-btn {
  flex: 1;
  padding: 10px 14px;
  border-radius: 6px;
  border: 1px solid var(--color-border-strong);
  background: var(--color-surface-subtle);
  color: var(--color-text);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.secondary-btn:hover:not(:disabled) {
  background: var(--color-primary-soft);
  border-color: #c7d2fe;
}

.secondary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-group small {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-text-soft);
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 30px;
}

.cancel-btn,
.submit-btn {
  flex: 1;
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-btn {
  background: var(--color-surface);
  border: 1px solid var(--color-border-strong);
  color: var(--color-text-soft);
}

.cancel-btn:hover {
  background: var(--color-surface-subtle);
}

.submit-btn {
  background: #10b981;
  border: none;
  color: white;
}

.submit-btn:hover:not(:disabled) {
  background: #059669;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
