export const safeNumber = value => {
  const number = Number(value)
  return Number.isFinite(number) ? number : 0
}

export const holdingTypeLabel = type => ({
  equity: 'Equity',
  mf: 'Mutual fund',
  us_equity: 'US equity',
  fd: 'Fixed deposit'
}[type] || (type ? String(type).replaceAll('_', ' ') : 'Other'))

const NUMERIC_SORT_FIELDS = new Set([
  'quantity',
  'average_price',
  'last_price',
  'current_value',
  'pnl',
  'pnl_percentage',
  'day_change',
  'day_change_percentage'
])

export const filterAndSortHoldings = (
  holdings,
  {
    searchQuery = '',
    filterType = '',
    performanceFilter = '',
    sortBy = 'current_value',
    sortDirection = 'desc'
  } = {}
) => {
  const query = String(searchQuery).trim().toLocaleLowerCase()
  const direction = sortDirection === 'desc' ? -1 : 1

  return holdings
    .filter(holding => {
      if (filterType && holding.instrument_type !== filterType) return false

      const pnl = safeNumber(holding.pnl)
      if (performanceFilter === 'gains' && pnl <= 0) return false
      if (performanceFilter === 'losses' && pnl >= 0) return false
      if (!query) return true

      return [
        holding.tradingsymbol,
        holding.sector,
        holdingTypeLabel(holding.instrument_type),
        holding.fund_name,
        holding.folio,
        holding.folio_number,
        holding.account_name,
        holding.account_id
      ]
        .filter(Boolean)
        .some(value => String(value).toLocaleLowerCase().includes(query))
    })
    .slice()
    .sort((leftHolding, rightHolding) => {
      const left = leftHolding[sortBy]
      const right = rightHolding[sortBy]

      let comparison
      if (!NUMERIC_SORT_FIELDS.has(sortBy)) {
        comparison = String(left || '').localeCompare(
          String(right || ''),
          undefined,
          { sensitivity: 'base' }
        ) * direction
      } else {
        comparison = (safeNumber(left) - safeNumber(right)) * direction
      }

      if (comparison !== 0) return comparison

      const leftIdentity = [
        leftHolding.tradingsymbol,
        leftHolding.folio || leftHolding.folio_number,
        leftHolding.id
      ].filter(value => value !== undefined && value !== null).join('|')
      const rightIdentity = [
        rightHolding.tradingsymbol,
        rightHolding.folio || rightHolding.folio_number,
        rightHolding.id
      ].filter(value => value !== undefined && value !== null).join('|')
      return leftIdentity.localeCompare(rightIdentity, undefined, { sensitivity: 'base' })
    })
}

export const summarizeHoldings = holdings => {
  const groups = holdings.reduce((byCurrency, holding) => {
    const inferredCurrency = holding.instrument_type === 'us_equity' ? 'USD' : 'INR'
    const currency = String(holding.currency || inferredCurrency).toUpperCase()
    if (!byCurrency[currency]) byCurrency[currency] = []
    byCurrency[currency].push(holding)
    return byCurrency
  }, {})

  const summarizeCurrency = (currency, currencyHoldings) => {
    const totals = currencyHoldings.reduce((summary, holding) => {
      const quantity = safeNumber(holding.quantity)
      const averagePrice = safeNumber(holding.average_price)
      const invested = averagePrice * quantity
      const dayChange = holding.day_change_value !== undefined && holding.day_change_value !== null
        ? safeNumber(holding.day_change_value)
        : safeNumber(holding.day_change) * quantity

      summary.total_investment += invested
      summary.current_value += safeNumber(holding.current_value)
      summary.total_pnl += safeNumber(holding.pnl)
      summary.day_change += dayChange
      return summary
    }, {
      currency,
      current_value: 0,
      total_investment: 0,
      total_pnl: 0,
      total_pnl_percentage: 0,
      day_change: 0,
      total_holdings: currencyHoldings.length
    })

    totals.total_pnl_percentage = totals.total_investment > 0
      ? (totals.total_pnl / totals.total_investment) * 100
      : 0
    const prevClose = totals.current_value - totals.day_change
    totals.day_change_percentage = prevClose > 0
      ? (totals.day_change / prevClose) * 100
      : 0
    return totals
  }

  const byCurrency = Object.fromEntries(
    Object.entries(groups).map(([currency, currencyHoldings]) => [
      currency,
      summarizeCurrency(currency, currencyHoldings)
    ])
  )
  const currencies = Object.keys(byCurrency)

  if (!currencies.length) {
    return {
      currency: null,
      current_value: 0,
      total_investment: 0,
      total_pnl: 0,
      total_pnl_percentage: 0,
      day_change: 0,
      day_change_percentage: 0,
      total_holdings: 0,
      by_currency: {}
    }
  }

  if (currencies.length === 1) {
    return {
      ...byCurrency[currencies[0]],
      by_currency: byCurrency
    }
  }

  return {
    currency: 'MIXED',
    current_value: null,
    total_investment: null,
    total_pnl: null,
    total_pnl_percentage: null,
    day_change: null,
    day_change_percentage: null,
    total_holdings: holdings.length,
    by_currency: byCurrency
  }
}
