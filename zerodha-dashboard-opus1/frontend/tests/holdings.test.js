import { describe, expect, it } from 'vitest'

import {
  filterAndSortHoldings,
  holdingTypeLabel,
  safeNumber,
  summarizeHoldings
} from '@/utils/holdings'

const holding = (overrides = {}) => ({
  id: 1,
  tradingsymbol: 'ALPHA',
  instrument_type: 'equity',
  sector: 'Technology',
  currency: 'INR',
  quantity: 2,
  average_price: 100,
  last_price: 120,
  current_value: 240,
  pnl: 40,
  pnl_percentage: 20,
  day_change: 5,
  ...overrides
})

describe('safeNumber and holdingTypeLabel', () => {
  it.each([
    [12, 12],
    ['12.5', 12.5],
    [0, 0],
    ['', 0],
    [null, 0],
    [undefined, 0],
    [Number.NaN, 0],
    [Number.POSITIVE_INFINITY, 0],
    ['not-a-number', 0]
  ])('normalizes %p to %p', (value, expected) => {
    expect(safeNumber(value)).toBe(expected)
  })

  it('labels known and unknown instrument types without throwing', () => {
    expect(holdingTypeLabel('equity')).toBe('Equity')
    expect(holdingTypeLabel('mf')).toBe('Mutual fund')
    expect(holdingTypeLabel('us_equity')).toBe('US equity')
    expect(holdingTypeLabel('fd')).toBe('Fixed deposit')
    expect(holdingTypeLabel('private_credit')).toBe('private credit')
    expect(holdingTypeLabel()).toBe('Other')
  })
})

describe('filterAndSortHoldings', () => {
  const holdings = [
    holding({
      id: 1,
      tradingsymbol: 'ALPHA',
      sector: 'Technology',
      account_name: 'Asha',
      pnl: 40,
      current_value: 240
    }),
    holding({
      id: 2,
      tradingsymbol: 'BETA FUND',
      instrument_type: 'mf',
      sector: 'Large Cap',
      folio: 'FOLIO-77',
      account_name: 'Bharat',
      pnl: 0,
      current_value: 500
    }),
    holding({
      id: 3,
      tradingsymbol: 'OMEGA',
      instrument_type: 'us_equity',
      sector: 'Healthcare',
      currency: 'USD',
      account_id: 42,
      pnl: -15,
      current_value: 180
    })
  ]

  it.each([
    ['alpha', ['ALPHA']],
    ['technology', ['ALPHA']],
    ['mutual FUND', ['BETA FUND']],
    ['folio-77', ['BETA FUND']],
    ['bharat', ['BETA FUND']],
    ['42', ['OMEGA']]
  ])('searches all user-visible identity fields for %s', (query, symbols) => {
    const result = filterAndSortHoldings(holdings, {
      searchQuery: query,
      sortBy: 'tradingsymbol',
      sortDirection: 'asc'
    })

    expect(result.map(item => item.tradingsymbol)).toEqual(symbols)
  })

  it('combines type, search, and performance filters', () => {
    expect(filterAndSortHoldings(holdings, {
      filterType: 'equity',
      performanceFilter: 'gains',
      searchQuery: 'asha'
    })).toEqual([holdings[0]])

    expect(filterAndSortHoldings(holdings, {
      performanceFilter: 'losses'
    })).toEqual([holdings[2]])
  })

  it('treats zero P&L as neither a gain nor a loss', () => {
    expect(filterAndSortHoldings(holdings, {
      performanceFilter: 'gains'
    }).map(item => item.id)).toEqual([1])
    expect(filterAndSortHoldings(holdings, {
      performanceFilter: 'losses'
    }).map(item => item.id)).toEqual([3])
  })

  it('sorts numeric and textual fields in both directions', () => {
    expect(filterAndSortHoldings(holdings, {
      sortBy: 'current_value',
      sortDirection: 'asc'
    }).map(item => item.id)).toEqual([3, 1, 2])

    expect(filterAndSortHoldings(holdings, {
      sortBy: 'current_value',
      sortDirection: 'desc'
    }).map(item => item.id)).toEqual([2, 1, 3])

    expect(filterAndSortHoldings(holdings, {
      sortBy: 'tradingsymbol',
      sortDirection: 'desc'
    }).map(item => item.tradingsymbol)).toEqual([
      'OMEGA',
      'BETA FUND',
      'ALPHA'
    ])
  })

  it('uses a stable identity tie-breaker without mutating the input', () => {
    const tied = [
      holding({ id: 3, tradingsymbol: 'TIE', folio: 'B', current_value: 10 }),
      holding({ id: 2, tradingsymbol: 'TIE', folio: 'A', current_value: 10 }),
      holding({ id: 1, tradingsymbol: 'ALPHA', current_value: 10 })
    ]
    const originalOrder = tied.slice()
    const originalObjects = tied.map(item => ({ ...item }))

    const result = filterAndSortHoldings(tied, {
      sortBy: 'current_value',
      sortDirection: 'desc'
    })

    expect(result.map(item => item.id)).toEqual([1, 2, 3])
    expect(tied).toEqual(originalOrder)
    expect(tied).toEqual(originalObjects)
    expect(result).not.toBe(tied)
    expect(result[0]).toBe(tied[2])
  })

  it('handles missing and non-numeric sort values deterministically', () => {
    const sparse = [
      holding({ id: 3, tradingsymbol: 'C', current_value: undefined }),
      holding({ id: 1, tradingsymbol: 'A', current_value: 0 }),
      holding({ id: 2, tradingsymbol: 'B', current_value: 'invalid' })
    ]

    expect(filterAndSortHoldings(sparse, {
      sortBy: 'current_value',
      sortDirection: 'asc'
    }).map(item => item.id)).toEqual([1, 2, 3])
  })

  it('sorts numeric API strings as numbers instead of lexicographically', () => {
    const serialized = [
      holding({ id: 1, tradingsymbol: 'TEN', current_value: '10' }),
      holding({ id: 2, tradingsymbol: 'TWO', current_value: '2' }),
      holding({ id: 3, tradingsymbol: 'ONE HUNDRED', current_value: '100' })
    ]

    expect(filterAndSortHoldings(serialized, {
      sortBy: 'current_value',
      sortDirection: 'asc'
    }).map(item => item.id)).toEqual([2, 1, 3])
  })
})

describe('summarizeHoldings', () => {
  it('returns a complete zero summary for an empty portfolio', () => {
    expect(summarizeHoldings([])).toEqual({
      currency: null,
      current_value: 0,
      total_investment: 0,
      total_pnl: 0,
      total_pnl_percentage: 0,
      day_change: 0,
      total_holdings: 0,
      by_currency: {}
    })
  })

  it('calculates homogeneous totals and monetary day change', () => {
    const result = summarizeHoldings([
      holding(),
      holding({
        id: 2,
        tradingsymbol: 'BETA',
        quantity: 3,
        average_price: 50,
        current_value: 180,
        pnl: 30,
        day_change: -2
      })
    ])

    expect(result).toEqual({
      currency: 'INR',
      current_value: 420,
      total_investment: 350,
      total_pnl: 70,
      total_pnl_percentage: 20,
      day_change: 4,
      total_holdings: 2,
      by_currency: {
        INR: {
          currency: 'INR',
          current_value: 420,
          total_investment: 350,
          total_pnl: 70,
          total_pnl_percentage: 20,
          day_change: 4,
          total_holdings: 2
        }
      }
    })
  })

  it('prefers an explicit monetary day_change_value over per-unit change', () => {
    const result = summarizeHoldings([
      holding({
        quantity: 10,
        day_change: 99,
        day_change_value: -12.5
      })
    ])

    expect(result.day_change).toBe(-12.5)
    expect(result.by_currency.INR.day_change).toBe(-12.5)
  })

  it('keeps fractional USD quantities and values in USD units', () => {
    const result = summarizeHoldings([
      holding({
        currency: 'usd',
        instrument_type: 'us_equity',
        quantity: 0.25,
        average_price: 100,
        current_value: 30,
        pnl: 5,
        day_change: 4
      })
    ])

    expect(result.currency).toBe('USD')
    expect(result.total_investment).toBe(25)
    expect(result.current_value).toBe(30)
    expect(result.total_pnl_percentage).toBe(20)
    expect(result.day_change).toBe(1)
    expect(Object.keys(result.by_currency)).toEqual(['USD'])
  })

  it('never adds unlike currencies into scalar monetary totals', () => {
    const result = summarizeHoldings([
      holding({ currency: 'INR', current_value: 240 }),
      holding({
        id: 2,
        currency: 'USD',
        instrument_type: 'us_equity',
        quantity: 1,
        average_price: 100,
        current_value: 125,
        pnl: 25,
        day_change: 2
      })
    ])

    expect(result.currency).toBe('MIXED')
    expect(result.total_holdings).toBe(2)
    expect(result.current_value).toBeNull()
    expect(result.total_investment).toBeNull()
    expect(result.total_pnl).toBeNull()
    expect(result.total_pnl_percentage).toBeNull()
    expect(result.day_change).toBeNull()
    expect(result.by_currency.INR.current_value).toBe(240)
    expect(result.by_currency.USD.current_value).toBe(125)
  })

  it('defaults missing currency to INR and normalizes invalid numbers to zero', () => {
    const result = summarizeHoldings([
      holding({
        currency: undefined,
        quantity: 'invalid',
        average_price: Number.POSITIVE_INFINITY,
        current_value: Number.NaN,
        pnl: undefined,
        day_change: null
      })
    ])

    expect(result.currency).toBe('INR')
    expect(result.current_value).toBe(0)
    expect(result.total_investment).toBe(0)
    expect(result.total_pnl).toBe(0)
    expect(result.total_pnl_percentage).toBe(0)
    expect(result.day_change).toBe(0)
  })
})
