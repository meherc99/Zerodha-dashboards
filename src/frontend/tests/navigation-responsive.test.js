import { readFile } from 'node:fs/promises'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'

const routerHarness = vi.hoisted(() => ({
  options: null,
  guard: null
}))

vi.mock('vue-router', () => ({
  createWebHistory: vi.fn(() => ({ type: 'history' })),
  createRouter: vi.fn(options => {
    routerHarness.options = options
    return {
      beforeEach: vi.fn(guard => {
        routerHarness.guard = guard
      })
    }
  }),
  useRoute: vi.fn(() => ({ query: {}, path: '/' })),
  useRouter: vi.fn(() => ({ push: vi.fn() }))
}))

import AccountSelector from '@/components/dashboard/AccountSelector.vue'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

describe('dashboard navigation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('registers every dedicated portfolio page beneath the protected dashboard', () => {
    expect(router).toBeDefined()
    const dashboard = routerHarness.options.routes.find(
      route => route.name === 'Dashboard'
    )

    expect(dashboard.meta.requiresAuth).toBe(true)
    expect(dashboard.redirect).toBe('/dashboard/overview')
    expect(dashboard.children.map(({ name, path }) => ({ name, path }))).toEqual([
      { name: 'Overview', path: 'overview' },
      { name: 'Stocks', path: 'stocks' },
      { name: 'MutualFunds', path: 'mutual-funds' },
      { name: 'USStocks', path: 'us-stocks' },
      { name: 'FixedDeposits', path: 'fixed-deposits' },
      { name: 'BankBalances', path: 'bank-balances' }
    ])
    expect(dashboard.children.every(route => route.component)).toBe(true)
  })

  it('lazy-loads the dedicated mutual-fund and fixed-deposit pages', async () => {
    const dashboard = routerHarness.options.routes.find(
      route => route.name === 'Dashboard'
    )
    const mutualFundsRoute = dashboard.children.find(
      route => route.name === 'MutualFunds'
    )
    const fixedDepositsRoute = dashboard.children.find(
      route => route.name === 'FixedDeposits'
    )

    const [mutualFundsModule, fixedDepositsModule] = await Promise.all([
      mutualFundsRoute.component(),
      fixedDepositsRoute.component()
    ])

    expect(mutualFundsModule.default.__name).toBe('MutualFundsTab')
    expect(fixedDepositsModule.default.__name).toBe('FixedDepositsTab')
  })

  it('describes mutual funds with scheme allocation and returns, not invented categories', async () => {
    const source = await readFile(
      new URL('../src/views/dashboard/MutualFundsTab.vue', import.meta.url),
      'utf8'
    )

    expect(source).toContain('title="Fund allocation"')
    expect(source).toContain('subtitle="Largest schemes by current value"')
    expect(source).toContain('title="Scheme returns"')
    expect(source).toContain('subtitle="Unrealised return by scheme"')
    expect(source).not.toMatch(/\bcategor(?:y|ies|isation|ization)\b/i)
  })

  it('preserves an intended protected destination through the login redirect', async () => {
    const auth = useAuthStore()
    auth.authReady = true
    auth.isAuthenticated = false

    await expect(routerHarness.guard({
      fullPath: '/dashboard/mutual-funds',
      matched: [{ meta: { requiresAuth: true } }]
    })).resolves.toEqual({
      path: '/login',
      query: { redirect: '/dashboard/mutual-funds' }
    })
  })

  it('keeps an authenticated user out of guest-only auth pages', async () => {
    const auth = useAuthStore()
    auth.authReady = true
    auth.isAuthenticated = true

    await expect(routerHarness.guard({
      fullPath: '/login',
      matched: [{ meta: { requiresGuest: true } }]
    })).resolves.toBe('/dashboard/overview')
  })
})

describe('responsive account scope selector', () => {
  it('server-renders an accessible family toggle without an empty member picker', async () => {
    const html = await renderToString(createSSRApp(AccountSelector, {
      modelValue: null,
      accounts: []
    }))

    expect(html).toMatch(/<legend[^>]*>Portfolio scope<\/legend>/)
    expect(html).toContain('aria-label="Choose family or individual portfolio"')
    expect(html).toContain('aria-pressed="true"')
    expect(html).not.toContain('aria-label="Family member account"')
  })

  it('server-renders the selected family member and mobile-width CSS contract', async () => {
    const html = await renderToString(createSSRApp(AccountSelector, {
      modelValue: 2,
      accounts: [
        { id: 1, account_name: 'Asha' },
        { id: 2, account_name: 'Bharat' }
      ]
    }))
    const source = await readFile(
      new URL('../src/components/dashboard/AccountSelector.vue', import.meta.url),
      'utf8'
    )

    expect(html).toContain('aria-label="Family member account"')
    expect(html).toContain('<select class="member-select" value="2"')
    expect(html).toContain('Bharat')
    expect(source).toMatch(/@media \(max-width: 620px\)/)
    expect(source).toMatch(/\.member-select\s*\{\s*width: 100%;/s)
  })
})
