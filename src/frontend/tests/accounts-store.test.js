import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const api = vi.hoisted(() => ({
  updateAccount: vi.fn()
}))

vi.mock('@/services/api', () => ({ api }))

import { useAccountsStore } from '@/stores/accounts'

describe('existing account reconnect', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('updates the same account with only the fresh request token', async () => {
    const refreshedAccount = {
      id: 12,
      account_name: 'Asha',
      is_active: true
    }
    api.updateAccount.mockResolvedValue({ data: refreshedAccount })
    const store = useAccountsStore()
    store.accounts = [{
      id: 12,
      account_name: 'Asha',
      is_active: true,
      last_synced_at: null
    }]

    await expect(
      store.reconnectAccount(12, 'fresh-request-token')
    ).resolves.toEqual(refreshedAccount)

    expect(api.updateAccount).toHaveBeenCalledWith(12, {
      request_token: 'fresh-request-token'
    })
    expect(store.accounts).toEqual([refreshedAccount])
  })
})
