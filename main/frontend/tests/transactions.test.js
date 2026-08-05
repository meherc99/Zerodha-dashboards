import { describe, expect, it } from 'vitest'

import { buildTransactionQuery } from '@/utils/transactions'

describe('transaction query contract', () => {
  it.each([
    ['-date', 'date', 'desc'],
    ['date', 'date', 'asc'],
    ['-amount', 'amount', 'desc'],
    ['amount', 'amount', 'asc'],
    ['description', 'description', 'asc']
  ])('maps UI sort %s to backend field %s in %s order', (
    sortBy,
    expectedField,
    expectedOrder
  ) => {
    expect(buildTransactionQuery({ sortBy })).toMatchObject({
      sort_by: expectedField,
      order: expectedOrder
    })
  })

  it('uses the backend names for pagination and active filters', () => {
    expect(buildTransactionQuery({
      page: 3,
      limit: 50,
      search: '  grocery store  ',
      transactionType: 'debit',
      categoryId: 7,
      sortBy: '-amount'
    })).toEqual({
      page: 3,
      limit: 50,
      sort_by: 'amount',
      order: 'desc',
      search: 'grocery store',
      type: 'debit',
      category_id: 7
    })
  })

  it('omits inactive filters and falls back safely from invalid controls', () => {
    expect(buildTransactionQuery({
      page: 0,
      limit: 500,
      search: '   ',
      transactionType: 'withdrawal',
      categoryId: null,
      sortBy: 'private_field'
    })).toEqual({
      page: 1,
      limit: 200,
      sort_by: 'date',
      order: 'asc'
    })
  })
})
