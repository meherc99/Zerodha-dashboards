const ISO_CURRENCY = /^[A-Z]{3}$/

export const normalizeCurrency = (currency, fallback = 'INR') => {
  const normalized = String(currency || '').trim().toUpperCase()
  return ISO_CURRENCY.test(normalized) ? normalized : fallback
}

export const createCurrencyFormatter = (currency, options = {}) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: normalizeCurrency(currency),
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    ...options,
  })
}

export const formatCurrency = (value, currency, options = {}) => {
  const number = Number(value)
  return createCurrencyFormatter(currency, options).format(
    Number.isFinite(number) ? number : 0
  )
}
