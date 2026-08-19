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
          <p v-if="account.last_synced_at">
            <strong>Last Synced:</strong> {{ formatDate(account.last_synced_at) }}
          </p>
          <p v-else>
            <strong>Last Synced:</strong> Never
          </p>
        </div>
        <div class="account-actions">
          <button @click="handleSync(account.id)" class="action-btn sync">
            Sync Now
          </button>
          <button @click="toggleAccountStatus(account)" class="action-btn">
            {{ account.is_active ? 'Deactivate' : 'Activate' }}
          </button>
          <button
            type="button"
            class="action-btn reconnect"
            @click="openReconnectModal(account)"
          >
            Reconnect
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
          <div class="form-group">
            <label for="api-key">API Key *</label>
            <input
              id="api-key"
              v-model="newAccount.api_key"
              type="text"
              placeholder="Your Kite Connect API Key"
              required
            />
          </div>
          <div class="form-group">
            <label for="api-secret">API Secret *</label>
            <input
              id="api-secret"
              v-model="newAccount.api_secret"
              type="password"
              autocomplete="new-password"
              placeholder="Your Kite Connect API Secret"
              required
            />
          </div>
          <div class="helper-actions">
            <button
              type="button"
              class="secondary-btn"
              @click="handleOpenLoginUrl"
              :disabled="authLoading || !newAccount.api_key"
            >
              {{ authLoading ? 'Opening...' : 'Open Zerodha Login' }}
            </button>
          </div>
          <div class="form-group">
            <label for="request-token">Request Token *</label>
            <input
              id="request-token"
              v-model="newAccount.request_token"
              type="password"
              autocomplete="off"
              placeholder="Paste the request_token from the Zerodha redirect URL"
              required
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
            Reconnect {{ reconnectAccount.account_name }}
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
          <p class="reconnect-copy">
            Generate a fresh Kite request token, then update this existing
            account. The stored API key stays server-side and no duplicate
            account will be created.
          </p>
          <div class="helper-actions">
            <button
              type="button"
              class="secondary-btn"
              :disabled="authLoading"
              @click="handleOpenReconnectLogin"
            >
              {{ authLoading ? 'Opening...' : 'Open Zerodha Login' }}
            </button>
          </div>
          <div class="form-group">
            <label for="reconnect-request-token">Fresh Request Token *</label>
            <input
              id="reconnect-request-token"
              v-model="reconnectForm.request_token"
              type="password"
              autocomplete="off"
              placeholder="Paste the fresh request_token"
              required
            />
            <small>
              Only the fresh request token is submitted to update account
              #{{ reconnectAccount.id }}; the backend exchanges and encrypts
              the new access token.
            </small>
          </div>
          <div class="modal-actions">
            <button type="button" class="cancel-btn" @click="closeReconnectModal">
              Cancel
            </button>
            <button type="submit" class="submit-btn" :disabled="accountsStore.loading">
              {{ accountsStore.loading ? 'Reconnecting...' : 'Reconnect account' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
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
  reconnectForm.value = { request_token: '' }
}

const closeReconnectModal = () => {
  reconnectAccount.value = null
  reconnectForm.value = { request_token: '' }
}

const handleAddAccount = async () => {
  try {
    await accountsStore.createAccount(newAccount.value)
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
  return openTrustedKiteLogin(
    () => api.getAccountLoginUrl(reconnectAccount.value.id)
  )
}

const handleReconnect = async () => {
  if (!reconnectAccount.value) return
  try {
    await accountsStore.reconnectAccount(
      reconnectAccount.value.id,
      reconnectForm.value.request_token
    )
    uiStore.addNotification({
      type: 'success',
      message: `${reconnectAccount.value.account_name} reconnected successfully.`
    })
    closeReconnectModal()
  } catch {
    uiStore.addNotification({
      type: 'error',
      message: accountsStore.error || 'Failed to reconnect account'
    })
  }
}

const handleSync = async (accountId) => {
  try {
    const result = await holdingsStore.syncHoldings(accountId)
    if (!result) return
    await accountsStore.fetchAccounts() // Refresh to update last_synced_at
    uiStore.addNotification({
      type: 'success',
      message: 'Account synced successfully!'
    })
  } catch (error) {
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

// Load accounts on mount
accountsStore.fetchAccounts()
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
  font-size: 32px;
  color: #111827;
}

.add-btn {
  padding: 10px 20px;
  background: #10b981;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.add-btn:hover {
  background: #059669;
}

.accounts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.account-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.reauth-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 6px;
  padding: 8px 12px;
  margin-bottom: 14px;
  font-size: 13px;
  color: #9a3412;
  font-weight: 500;
}

.reauth-banner-btn {
  background: #ea580c;
  color: white;
  border: none;
  border-radius: 5px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.reauth-banner-btn:hover {
  background: #c2410c;
}

.status-badge.reauth {
  background: #fff7ed;
  color: #9a3412;
}

.account-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.account-header h3 {
  margin: 0;
  font-size: 18px;
  color: #111827;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  background: #f3f4f6;
  color: #6b7280;
}

.status-badge.active {
  background: #d1fae5;
  color: #065f46;
}

.account-details {
  margin-bottom: 15px;
}

.account-details p {
  margin: 8px 0;
  font-size: 14px;
  color: #6b7280;
}

.account-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  flex: 1;
  padding: 8px 16px;
  border: 1px solid #d1d5db;
  background: white;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #f9fafb;
}

.action-btn.sync {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.action-btn.sync:hover {
  background: #2563eb;
}

.action-btn.reconnect {
  border-color: #c7d2fe;
  color: #4338ca;
}

.reconnect-copy {
  margin: 0 0 18px;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.5;
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 20px;
  color: #9ca3af;
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
  background: white;
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
  border-bottom: 1px solid #e5e7eb;
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
  color: #6b7280;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #111827;
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
  color: #374151;
  font-size: 14px;
}

.form-group input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.form-group input:focus {
  outline: none;
  border-color: #3b82f6;
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
  border: 1px solid #d1d5db;
  background: #f9fafb;
  color: #111827;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.secondary-btn:hover:not(:disabled) {
  background: #eef2ff;
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
  color: #6b7280;
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
  background: white;
  border: 1px solid #d1d5db;
  color: #374151;
}

.cancel-btn:hover {
  background: #f9fafb;
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
