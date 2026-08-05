const SORT_FIELDS = new Set(['date', 'amount', 'description'])
const TRANSACTION_TYPES = new Set(['credit', 'debit'])

const positiveInteger = (value, fallback) => {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback
}

export const buildTransactionQuery = ({
  page = 1,
  limit = 20,
  search = '',
  transactionType = '',
  categoryId = '',
  sortBy = '-date'
} = {}) => {
  const rawSort = String(sortBy || '-date')
  const requestedField = rawSort.replace(/^-/, '')
  const sortField = SORT_FIELDS.has(requestedField) ? requestedField : 'date'
  const query = {
    page: positiveInteger(page, 1),
    limit: Math.min(positiveInteger(limit, 20), 200),
    sort_by: sortField,
    order: rawSort.startsWith('-') ? 'desc' : 'asc'
  }
  const normalizedSearch = String(search || '').trim()

  if (normalizedSearch) query.search = normalizedSearch
  if (TRANSACTION_TYPES.has(transactionType)) query.type = transactionType
  if (categoryId !== '' && categoryId !== null && categoryId !== undefined) {
    query.category_id = categoryId
  }

  return query
}
