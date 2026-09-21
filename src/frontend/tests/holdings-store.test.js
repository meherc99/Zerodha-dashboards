import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const api = vi.hoisted(() => ({
  getAggregatedHoldings: vi.fn(),
  getHoldings: vi.fn(),
  getPortfolioHistory: vi.fn(),
  getSectorBreakdown: vi.fn(),
  refreshUSPrices: vi.fn(),
  syncHoldings: vi.fn()
}))

vi.mock('@/services/api', () => ({ api }))

import { useHoldingsStore } from '@/stores/holdings'

const holding = {
  id: 1,
  account_id: 42,
  tradingsymbol: 'ALPHA',
  instrument_type: 'equity',
  current_value: 120,
  pnl: 20
}

describe('holdings sync outcomes', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    api.getPortfolioHistory.mockResolvedValue({ data: { timeseries: [] } })
    api.getSectorBreakdown.mockResolvedValue({ data: { sectors: [] } })
  })

  it('returns a completed result after refreshing the selected account', async () => {
    const syncResult = {
      status: 'completed',
      accounts_total: 1,
      accounts_succeeded: 1,
      accounts_failed: 0
    }
    api.syncHoldings.mockResolvedValue({ data: syncResult })
    api.getHoldings.mockResolvedValue({
      data: {
        holdings: [holding],
        summary: { current_value: 120, total_pnl: 20 }
      }
    })

    const store = useHoldingsStore()

    await expect(store.syncHoldings(42)).resolves.toEqual(syncResult)

    expect(api.syncHoldings).toHaveBeenCalledWith(
      42,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    )
    expect(api.getHoldings).toHaveBeenCalledWith(
      { account_id: 42 },
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    )
    expect(api.getAggregatedHoldings).not.toHaveBeenCalled()
    expect(store.holdings).toEqual([holding])
    expect(store.summary).toEqual({ current_value: 120, total_pnl: 20 })
    expect(store.lastUpdated).toBeInstanceOf(Date)
    expect(store.error).toBeNull()
    expect(store.loading).toBe(false)
  })

  it('refreshes last-good family data but rejects a partial sync', async () => {
    const syncResult = {
      status: 'partial',
      accounts_total: 3,
      accounts_succeeded: 2,
      accounts_failed: 1
    }
    api.syncHoldings.mockResolvedValue({ data: syncResult })
    api.getAggregatedHoldings.mockResolvedValue({
      data: {
        holdings: [holding],
        current_value: 120,
        total_pnl: 20
      }
    })

    const store = useHoldingsStore()
    let error
    try {
      await store.syncHoldings()
    } catch (caught) {
      error = caught
    }

    expect(api.getAggregatedHoldings).toHaveBeenCalledOnce()
    expect(store.holdings).toEqual([holding])
    expect(store.summary.current_value).toBe(120)
    expect(error.syncResult).toEqual(syncResult)
    expect(error.message).toBe(
      '1 of 3 accounts failed to sync. Showing the latest available data.'
    )
    expect(store.error).toBe(error.message)
    expect(store.loading).toBe(false)
  })

  it('surfaces a failed status even when the latest portfolio can be loaded', async () => {
    const syncResult = {
      status: 'failed',
      accounts_total: 1,
      accounts_succeeded: 0,
      accounts_failed: 1
    }
    api.syncHoldings.mockResolvedValue({ data: syncResult })
    api.getHoldings.mockResolvedValue({
      data: {
        holdings: [holding],
        summary: { current_value: 120 }
      }
    })

    const store = useHoldingsStore()

    await expect(store.syncHoldings(42)).rejects.toMatchObject({
      message: 'Portfolio sync failed. Showing the latest available data.',
      syncResult
    })
    expect(store.holdings).toEqual([holding])
    expect(store.error).toBe(
      'Portfolio sync failed. Showing the latest available data.'
    )
    expect(store.loading).toBe(false)
  })

  it('preserves existing data when the sync request itself fails', async () => {
    const backendError = {
      response: { data: { error: 'Broker session expired' } }
    }
    api.syncHoldings.mockRejectedValue(backendError)
    const store = useHoldingsStore()
    store.$patch({
      holdings: [holding],
      summary: { current_value: 120 },
      lastUpdated: new Date('2026-07-01T12:00:00Z')
    })

    await expect(store.syncHoldings(42)).rejects.toBe(backendError)

    expect(api.getHoldings).not.toHaveBeenCalled()
    expect(store.holdings).toEqual([holding])
    expect(store.summary).toEqual({ current_value: 120 })
    expect(store.lastUpdated).toEqual(new Date('2026-07-01T12:00:00Z'))
    expect(store.error).toBe('Broker session expired')
    expect(store.loading).toBe(false)
  })
})

describe('portfolio scope isolation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    api.getPortfolioHistory.mockResolvedValue({ data: { timeseries: [] } })
    api.getSectorBreakdown.mockResolvedValue({ data: { sectors: [] } })
  })

  it('aborts and ignores a late family response after Member scope wins', async () => {
    let resolveFamily
    let resolveMember
    api.getAggregatedHoldings.mockImplementation(
      () => new Promise(resolve => {
        resolveFamily = resolve
      })
    )
    api.getHoldings.mockImplementation(
      () => new Promise(resolve => {
        resolveMember = resolve
      })
    )

    const store = useHoldingsStore()
    const familyLoad = store.loadPortfolio()
    const familySignal = api.getAggregatedHoldings.mock.calls[0][0].signal
    const memberLoad = store.loadPortfolio(42)

    expect(familySignal.aborted).toBe(true)

    const memberHolding = {
      ...holding,
      account_id: 42,
      tradingsymbol: 'MEMBER'
    }
    resolveMember({
      data: {
        holdings: [memberHolding],
        summary: { current_value: 420 }
      }
    })
    await expect(memberLoad).resolves.toEqual({
      stale: false,
      analyticsFailed: false
    })

    resolveFamily({
      data: {
        holdings: [{ ...holding, tradingsymbol: 'STALE-FAMILY' }],
        current_value: 999
      }
    })
    await expect(familyLoad).resolves.toEqual({ stale: true })

    expect(store.portfolioScope).toBe('account:42')
    expect(store.holdings).toEqual([memberHolding])
    expect(store.summary).toEqual({ current_value: 420 })
    expect(store.loading).toBe(false)
  })

  it('does not accept an older same-scope response after a retry', async () => {
    const pending = []
    api.getAggregatedHoldings.mockImplementation(
      () => new Promise(resolve => pending.push(resolve))
    )

    const store = useHoldingsStore()
    const firstLoad = store.loadPortfolio()
    const retryLoad = store.loadPortfolio()

    pending[1]({
      data: {
        holdings: [{ ...holding, tradingsymbol: 'LATEST' }],
        current_value: 200
      }
    })
    await retryLoad
    pending[0]({
      data: {
        holdings: [{ ...holding, tradingsymbol: 'OLDER' }],
        current_value: 100
      }
    })
    await firstLoad

    expect(store.holdings[0].tradingsymbol).toBe('LATEST')
    expect(store.summary.current_value).toBe(200)
  })

  it('rejects a zero-update US refresh instead of reporting success', async () => {
    api.refreshUSPrices.mockResolvedValue({
      data: {
        status: 'no_holdings',
        updated_count: 0,
        accounts_skipped: 1
      }
    })
    api.getHoldings.mockResolvedValue({
      data: { holdings: [], summary: { current_value: 0 } }
    })

    const store = useHoldingsStore()

    await expect(store.refreshUSPrices(42)).rejects.toMatchObject({
      message: 'No US holdings were available to refresh.',
      refreshResult: { status: 'no_holdings', updated_count: 0 }
    })
    expect(store.error).toBe('No US holdings were available to refresh.')
  })
})

describe('fixed-deposit summary contract', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('exposes accrued interest under canonical summary keys and FD aliases', () => {
    const store = useHoldingsStore()
    store.holdings = [{
      id: 8,
      instrument_type: 'fd',
      quantity: 1,
      average_price: 100000,
      current_value: 107500,
      pnl: 7500
    }]

    expect(store.fdSummary).toMatchObject({
      current_value: 107500,
      total_investment: 100000,
      total_pnl: 7500,
      total_pnl_percentage: 7.5,
      total_interest: 7500,
      total_interest_percentage: 7.5,
      total_holdings: 1
    })
  })
})
