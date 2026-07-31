import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const api = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  defaults: {
    headers: {
      common: {}
    }
  }
}))

const resetApiSession = vi.hoisted(() => vi.fn())

vi.mock('@/services/api', () => ({
  default: api,
  resetApiSession
}))

import { useAuthStore } from '@/stores/auth'
import { useAccountsStore } from '@/stores/accounts'
import { useBankAccountsStore } from '@/stores/bankAccounts'
import { useCategoriesStore } from '@/stores/categories'
import { useHoldingsStore } from '@/stores/holdings'

describe('auth store lifecycle', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    sessionStorage.clear()
    api.get.mockReset()
    api.post.mockReset()
    api.defaults.headers.common = {}
    resetApiSession.mockReset()
  })

  it('finishes initialization unauthenticated when no token exists', async () => {
    const store = useAuthStore()

    await expect(store.initializeAuth()).resolves.toBe(false)

    expect(store.authReady).toBe(true)
    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
    expect(store.token).toBeNull()
    expect(api.get).not.toHaveBeenCalled()
    expect(api.defaults.headers.common.Authorization).toBeUndefined()
    expect(resetApiSession).toHaveBeenCalledOnce()
  })

  it('awaits token validation before marking a restored session authenticated', async () => {
    sessionStorage.setItem('token', 'valid-token')
    api.get.mockResolvedValue({
      data: { id: 7, email: 'owner@example.com', is_active: true }
    })
    const store = useAuthStore()

    await expect(store.initializeAuth()).resolves.toBe(true)

    expect(api.get).toHaveBeenCalledWith('/auth/me')
    expect(store.authReady).toBe(true)
    expect(store.isAuthenticated).toBe(true)
    expect(store.token).toBe('valid-token')
    expect(store.user.email).toBe('owner@example.com')
    expect(api.defaults.headers.common.Authorization).toBe('Bearer valid-token')
  })

  it('clears all client auth state when a restored token is rejected', async () => {
    sessionStorage.setItem('token', 'expired-token')
    api.get.mockRejectedValue({ response: { status: 401 } })
    const store = useAuthStore()

    await expect(store.initializeAuth()).resolves.toBe(false)

    expect(store.authReady).toBe(true)
    expect(store.isAuthenticated).toBe(false)
    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
    expect(sessionStorage.getItem('token')).toBeNull()
    expect(api.defaults.headers.common.Authorization).toBeUndefined()
  })

  it('stores a successful login consistently in state, storage, and headers', async () => {
    api.post.mockResolvedValue({
      data: {
        access_token: 'new-token',
        user: { id: 9, email: 'new@example.com' }
      }
    })
    const store = useAuthStore()

    await store.login('new@example.com', 'correct horse battery staple')

    expect(api.post).toHaveBeenCalledWith('/auth/login', {
      email: 'new@example.com',
      password: 'correct horse battery staple'
    })
    expect(store.isAuthenticated).toBe(true)
    expect(store.authReady).toBe(true)
    expect(store.token).toBe('new-token')
    expect(sessionStorage.getItem('token')).toBe('new-token')
    expect(localStorage.getItem('token')).toBeNull()
    expect(api.defaults.headers.common.Authorization).toBe('Bearer new-token')
    expect(resetApiSession).toHaveBeenCalledOnce()
  })

  it('clears the session even when the remote logout request fails', async () => {
    sessionStorage.setItem('token', 'live-token')
    const store = useAuthStore()
    store.setAuth({
      access_token: 'live-token',
      user: { id: 1, email: 'owner@example.com' }
    })
    api.post.mockRejectedValue(new Error('network unavailable'))

    await expect(store.logout()).resolves.toBeUndefined()

    expect(api.post).toHaveBeenCalledWith('/auth/logout')
    expect(store.isAuthenticated).toBe(false)
    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
    expect(sessionStorage.getItem('token')).toBeNull()
    expect(api.defaults.headers.common.Authorization).toBeUndefined()
    expect(resetApiSession).toHaveBeenCalledTimes(2)
  })

  it('does not leave a partial session when login fails', async () => {
    api.post.mockRejectedValue({
      response: { data: { error: 'Invalid email or password' } }
    })
    const store = useAuthStore()

    await expect(store.login('owner@example.com', 'wrong')).rejects.toBeDefined()

    expect(store.error).toBe('Invalid email or password')
    expect(store.isAuthenticated).toBe(false)
    expect(store.token).toBeNull()
    expect(sessionStorage.getItem('token')).toBeNull()
  })

  it('clears every tenant-scoped store before activating another user', () => {
    const accounts = useAccountsStore()
    const bankAccounts = useBankAccountsStore()
    const categories = useCategoriesStore()
    const holdings = useHoldingsStore()

    accounts.$patch({
      accounts: [{ id: 1, account_name: 'Previous owner' }],
      currentAccount: 1,
      error: 'stale'
    })
    bankAccounts.$patch({
      bankAccounts: [{ id: 2, bank_name: 'Old bank' }],
      selectedBank: { id: 2 },
      transactions: {
        items: [{ id: 3 }],
        loading: false,
        error: 'stale'
      }
    })
    categories.$patch({
      categories: [{ id: 4, name: 'Private category' }],
      lastFetched: Date.now()
    })
    holdings.$patch({
      holdings: [{ id: 5, tradingsymbol: 'PRIVATE' }],
      summary: { current_value: 100 },
      portfolioHistory: [{ date: '2026-01-01', value: 100 }],
      lastUpdated: new Date()
    })

    const store = useAuthStore()
    store.setAuth({
      access_token: 'next-user-token',
      user: { id: 10, email: 'next@example.com' }
    })

    expect(resetApiSession).toHaveBeenCalledOnce()
    expect(accounts.$state).toEqual({
      accounts: [],
      currentAccount: null,
      loading: false,
      error: null
    })
    expect(bankAccounts.bankAccounts).toEqual([])
    expect(bankAccounts.selectedBank).toBeNull()
    expect(bankAccounts.transactions.items).toEqual([])
    expect(bankAccounts.transactions.error).toBeNull()
    expect(categories.categories).toEqual([])
    expect(categories.lastFetched).toBeNull()
    expect(holdings.holdings).toEqual([])
    expect(holdings.summary).toBeNull()
    expect(holdings.portfolioHistory).toEqual([])
    expect(holdings.lastUpdated).toBeNull()
  })
})
