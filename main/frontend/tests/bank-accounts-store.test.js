import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const api = vi.hoisted(() => ({
  deleteBankAccount: vi.fn(),
  deleteStatement: vi.fn(),
  deleteTransaction: vi.fn(),
  getBankAccounts: vi.fn(),
  getBalanceTrend: vi.fn(),
  getCategoryBreakdown: vi.fn(),
  getCashflow: vi.fn(),
  getStatementPreview: vi.fn(),
  getStatements: vi.fn(),
  getTopMerchants: vi.fn(),
  getTransactions: vi.fn(),
  parseStatement: vi.fn()
}))

vi.mock('@/services/api', () => ({ api }))

import { useBankAccountsStore } from '@/stores/bankAccounts'

describe('bank analytics response normalization', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('adapts the four backend payloads into chart-ready records', async () => {
    api.getBalanceTrend.mockResolvedValue({
      data: {
        dates: ['2026-07-01', '2026-07-02'],
        balances: [1250.5, 1500]
      }
    })
    api.getCategoryBreakdown.mockResolvedValue({
      data: {
        transaction_count: 4,
        categories: [{
          id: 3,
          name: 'Groceries',
          icon: 'basket',
          total: 325.25,
          percentage: 65.05,
          transaction_count: 4
        }]
      }
    })
    api.getCashflow.mockResolvedValue({
      data: {
        periods: ['Week 1', 'Week 2'],
        credits: [2000, 0],
        debits: [500, 250],
        net: [1500, -250]
      }
    })
    api.getTopMerchants.mockResolvedValue({
      data: {
        merchants: [{
          merchant: 'Neighbourhood Market',
          total: 275,
          count: 3,
          avg_transaction: 91.67
        }]
      }
    })

    const store = useBankAccountsStore()
    await store.fetchAllAnalytics(17, 90)

    expect(api.getBalanceTrend).toHaveBeenCalledWith(
      17,
      90,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    )
    expect(api.getCategoryBreakdown).toHaveBeenCalledWith(
      17,
      90,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    )
    expect(api.getCashflow).toHaveBeenCalledWith(
      17,
      90,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    )
    expect(api.getTopMerchants).toHaveBeenCalledWith(
      17,
      10,
      90,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    )
    expect(store.analytics.balanceTrend).toEqual([
      { date: '2026-07-01', balance: 1250.5 },
      { date: '2026-07-02', balance: 1500 }
    ])
    expect(store.analytics.categoryBreakdown).toEqual([{
      id: 3,
      name: 'Groceries',
      icon: 'basket',
      total: 325.25,
      percentage: 65.05,
      transaction_count: 4,
      category: 'Groceries',
      count: 4
    }])
    expect(store.analytics.cashflow).toEqual([
      {
        period: 'Week 1',
        total_credit: 2000,
        total_debit: 500,
        net: 1500
      },
      {
        period: 'Week 2',
        total_credit: 0,
        total_debit: 250,
        net: -250
      }
    ])
    expect(store.analytics.topMerchants).toEqual([{
      merchant: 'Neighbourhood Market',
      total: 275,
      count: 3,
      avg_transaction: 91.67,
      total_spent: 275,
      transaction_count: 3
    }])
    expect(store.analytics.debitTransactionCount).toBe(4)
    expect(store.analytics.error).toBeNull()
    expect(store.analytics.loading).toBe(false)
  })

  it('normalizes sparse arrays to zero instead of leaking undefined to charts', async () => {
    api.getBalanceTrend.mockResolvedValue({
      data: { dates: ['2026-07-01', '2026-07-02'], balances: [100] }
    })
    api.getCategoryBreakdown.mockResolvedValue({ data: {} })
    api.getCashflow.mockResolvedValue({
      data: { periods: ['Week 1'], credits: [], debits: [], net: [] }
    })
    api.getTopMerchants.mockResolvedValue({ data: {} })

    const store = useBankAccountsStore()
    await store.fetchAllAnalytics(17)

    expect(store.analytics.balanceTrend).toEqual([
      { date: '2026-07-01', balance: 100 },
      { date: '2026-07-02', balance: 0 }
    ])
    expect(store.analytics.categoryBreakdown).toEqual([])
    expect(store.analytics.cashflow).toEqual([{
      period: 'Week 1',
      total_credit: 0,
      total_debit: 0,
      net: 0
    }])
    expect(store.analytics.topMerchants).toEqual([])
    expect(store.analytics.debitTransactionCount).toBe(0)
  })

  it('clears all related charts and exposes one stable error on partial failure', async () => {
    const backendError = {
      response: { data: { error: 'Analytics temporarily unavailable' } }
    }
    api.getBalanceTrend.mockResolvedValue({
      data: { dates: ['2026-07-01'], balances: [100] }
    })
    api.getCategoryBreakdown.mockRejectedValue(backendError)
    api.getCashflow.mockResolvedValue({
      data: { periods: [], credits: [], debits: [], net: [] }
    })
    api.getTopMerchants.mockResolvedValue({ data: { merchants: [] } })

    const store = useBankAccountsStore()
    store.analytics.balanceTrend = [{ date: 'stale', balance: 1 }]
    store.analytics.categoryBreakdown = [{ category: 'stale' }]
    store.analytics.cashflow = [{ period: 'stale' }]
    store.analytics.topMerchants = [{ merchant: 'stale' }]

    await expect(store.fetchAllAnalytics(17)).rejects.toBe(backendError)

    expect(store.analytics.balanceTrend).toEqual([])
    expect(store.analytics.categoryBreakdown).toEqual([])
    expect(store.analytics.cashflow).toEqual([])
    expect(store.analytics.topMerchants).toEqual([])
    expect(store.analytics.debitTransactionCount).toBe(0)
    expect(store.analytics.error).toBe('Analytics temporarily unavailable')
    expect(store.analytics.loading).toBe(false)
  })
})

describe('bank account and statement lifecycle', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('rebinds the selected bank to the refreshed account object', async () => {
    const store = useBankAccountsStore()
    const staleSelection = {
      id: 9,
      bank_name: 'Example Bank',
      current_balance: 100,
      currency: 'USD'
    }
    const refreshedSelection = {
      ...staleSelection,
      current_balance: 850
    }
    store.bankAccounts = [staleSelection]
    store.selectedBank = staleSelection
    api.getBankAccounts.mockResolvedValue({
      data: [refreshedSelection]
    })

    await store.fetchBankAccounts()

    expect(store.selectedBank).toBe(store.bankAccounts[0])
    expect(store.selectedBank.current_balance).toBe(850)
  })

  it('clears a selected bank that disappeared during refresh', async () => {
    const store = useBankAccountsStore()
    store.selectedBank = { id: 9 }
    api.getBankAccounts.mockResolvedValue({ data: [{ id: 10 }] })

    await store.fetchBankAccounts()

    expect(store.selectedBank).toBeNull()
  })

  it('retries parsing the retained statement without uploading it again', async () => {
    const store = useBankAccountsStore()
    store.bankAccounts = [{ id: 9, currency: 'EUR' }]
    api.parseStatement.mockResolvedValue({
      data: { statement_id: 71, status: 'review' }
    })
    api.getStatementPreview.mockResolvedValue({
      data: { transactions: [{ id: 1 }], validation_warnings: [] }
    })
    api.getStatements.mockResolvedValue({
      data: [{ id: 71, status: 'review' }]
    })

    await store.retryStatementParse(71, 9)

    expect(api.parseStatement).toHaveBeenCalledWith(71)
    expect(store.reviewModal).toMatchObject({
      isOpen: true,
      statementId: 71,
      bankAccountId: 9,
      currency: 'EUR',
      transactions: [{ id: 1 }]
    })
    expect(store.uploadModal.statementId).toBeNull()
  })

  it('permanently deletes the selected bank from local state after confirmation is handled by the UI', async () => {
    api.deleteBankAccount.mockResolvedValue({ data: { message: 'deleted' } })
    const store = useBankAccountsStore()
    store.bankAccounts = [{ id: '9' }, { id: 10 }]
    store.selectedBank = store.bankAccounts[0]

    await store.deleteBankAccount(9)

    expect(api.deleteBankAccount).toHaveBeenCalledWith(9)
    expect(store.bankAccounts).toEqual([{ id: 10 }])
    expect(store.selectedBank).toBeNull()
  })

  it('clears the previous bank statement list while a new bank loads', async () => {
    let resolveStatements
    api.getStatements.mockImplementation(
      () => new Promise(resolve => {
        resolveStatements = resolve
      })
    )
    const store = useBankAccountsStore()
    store.statements.accountId = 9
    store.statements.items = [{ id: 90, bank_account_id: 9 }]

    const load = store.fetchStatements(10)

    expect(store.statements.items).toEqual([])
    resolveStatements({
      data: [{ id: 100, bank_account_id: 10 }]
    })
    await load
    expect(store.statements.items).toEqual([
      { id: 100, bank_account_id: 10 }
    ])
  })

  it('refreshes and rebinds the selected balance after transaction deletion', async () => {
    api.deleteTransaction.mockResolvedValue({ data: { message: 'deleted' } })
    const refreshedAccount = {
      id: 9,
      bank_name: 'Example Bank',
      current_balance: 725,
      currency: 'GBP'
    }
    api.getBankAccounts.mockResolvedValue({ data: [refreshedAccount] })
    const store = useBankAccountsStore()
    store.bankAccounts = [{
      ...refreshedAccount,
      current_balance: 900
    }]
    store.selectedBank = store.bankAccounts[0]

    await store.deleteTransaction(44)

    expect(api.deleteTransaction).toHaveBeenCalledWith(44)
    expect(api.getBankAccounts).toHaveBeenCalledOnce()
    expect(store.selectedBank).toBe(store.bankAccounts[0])
    expect(store.selectedBank.current_balance).toBe(725)
  })
})

describe('bank data request isolation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    api.getCategoryBreakdown.mockImplementation(accountId => Promise.resolve({
      data: {
        transaction_count: accountId,
        categories: [{ name: `Account ${accountId}`, transaction_count: accountId }]
      }
    }))
    api.getCashflow.mockResolvedValue({
      data: { periods: [], credits: [], debits: [], net: [] }
    })
    api.getTopMerchants.mockResolvedValue({ data: { merchants: [] } })
  })

  it('aborts and ignores analytics from a previously selected bank', async () => {
    const pendingBalances = []
    api.getBalanceTrend.mockImplementation(
      () => new Promise(resolve => pendingBalances.push(resolve))
    )
    const store = useBankAccountsStore()

    const oldLoad = store.fetchAllAnalytics(17, 30)
    const oldSignal = api.getBalanceTrend.mock.calls[0][2].signal
    const currentLoad = store.fetchAllAnalytics(23, 30)

    expect(oldSignal.aborted).toBe(true)
    pendingBalances[1]({
      data: { dates: ['2026-07-02'], balances: [2300] }
    })
    await currentLoad
    pendingBalances[0]({
      data: { dates: ['2026-07-01'], balances: [1700] }
    })
    await expect(oldLoad).resolves.toBeNull()

    expect(store.analytics.accountId).toBe(23)
    expect(store.analytics.balanceTrend).toEqual([
      { date: '2026-07-02', balance: 2300 }
    ])
    expect(store.analytics.debitTransactionCount).toBe(23)
  })

  it('keeps the latest transaction response when account requests resolve out of order', async () => {
    const pending = []
    api.getTransactions.mockImplementation(
      () => new Promise(resolve => pending.push(resolve))
    )
    const store = useBankAccountsStore()

    const oldLoad = store.fetchTransactions(17)
    const oldSignal = api.getTransactions.mock.calls[0][2].signal
    const currentLoad = store.fetchTransactions(23)

    expect(oldSignal.aborted).toBe(true)
    pending[1]({ data: { transactions: [{ id: 23 }] } })
    await currentLoad
    pending[0]({ data: { transactions: [{ id: 17 }] } })
    await expect(oldLoad).resolves.toBeNull()

    expect(store.transactions.accountId).toBe(23)
    expect(store.transactions.items).toEqual([{ id: 23 }])
  })
})
