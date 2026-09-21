import { readFile } from 'node:fs/promises'
import { describe, expect, it } from 'vitest'

import { formatCurrency, normalizeCurrency } from '@/utils/currency'

const source = relativePath => readFile(
  new URL(`../src/${relativePath}`, import.meta.url),
  'utf8'
)

describe('multi-currency bank presentation', () => {
  it.each([
    ['INR', '₹'],
    ['USD', '$'],
    ['EUR', '€'],
    ['GBP', '£']
  ])('formats %s values with that account currency', (currency, symbol) => {
    const formatted = formatCurrency(1234.5, currency)

    expect(normalizeCurrency(currency)).toBe(currency)
    expect(formatted).toContain(symbol)
    if (currency !== 'INR') expect(formatted).not.toContain('₹')
  })

  it('threads selected-bank currency through transactions, analytics, and statement review', async () => {
    const [
      bankPage,
      transactions,
      analytics,
      review
    ] = await Promise.all([
      source('views/dashboard/BankBalancesTab.vue'),
      source('components/bank/TransactionsList.vue'),
      source('components/bank/BankAnalyticsView.vue'),
      source('components/bank/StatementReviewModal.vue')
    ])

    expect(bankPage).toMatch(/:currency="selectedBank\.currency"/)
    expect(transactions).toContain("default: 'INR'")
    expect(transactions).toContain("from '@/utils/currency'")
    expect(analytics).toContain('Debit transactions')
    expect(analytics).not.toContain('Math.max(categoryTotal, merchantTotal)')
    expect(review).toContain('reviewModal.value.currency')
  })

  it('uses the selected currency for account opening balance and monthly change', async () => {
    const [addAccount, bankCard] = await Promise.all([
      source('components/bank/AddBankAccountModal.vue'),
      source('components/bank/BankCard.vue')
    ])

    expect(addAccount).toContain('<span class="prefix">{{ currencySymbol }}</span>')
    expect(addAccount).toContain('createCurrencyFormatter(form.value.currency)')
    expect(bankCard).toContain(
      'formatCurrency(bank.monthly_change, bank.currency)'
    )
  })
})

describe('operational recovery UI', () => {
  it('reconnects an existing account through its server-owned Kite login URL', async () => {
    const accounts = await source('views/Accounts.vue')

    expect(accounts).toContain('api.getAccountLoginUrl(reconnectAccount.value.id)')
    expect(accounts).toContain('accountsStore.reconnectAccount(')
    expect(accounts).toMatch(/no duplicate\s+account will be created/i)
    expect(accounts).not.toContain('id="reconnect-api-key"')
  })

  it('offers statement resume, review, and deletion without re-uploading', async () => {
    const [upload, history, bankPage] = await Promise.all([
      source('components/bank/BankUploadModal.vue'),
      source('components/bank/StatementHistory.vue'),
      source('views/dashboard/BankBalancesTab.vue')
    ])

    expect(upload).toContain('retryStatementParse()')
    expect(upload).toContain('discardStatement()')
    expect(history).toContain('Resume parsing')
    expect(history).toContain('Ready for review')
    expect(bankPage).toContain('<StatementHistory :account="selectedBank" />')
  })

  it('requires explicit irreversible confirmation before deleting a bank account', async () => {
    const bankPage = await source('views/dashboard/BankBalancesTab.vue')

    expect(bankPage).toContain('Permanently delete this bank account?')
    expect(bankPage).toContain('transactions, uploaded ')
    expect(bankPage).toContain('statements, and PDF files')
    expect(bankPage).toContain('bankAccountsStore.deleteBankAccount(bank.id)')
  })

  it('reloads transaction rows after the store refreshes the post-delete balance', async () => {
    const transactions = await source('components/bank/TransactionsList.vue')

    expect(transactions).toMatch(
      /await bankStore\.deleteTransaction\(transaction\.id\)\s+await loadTransactions\(\)/
    )
  })
})

describe('fixed-deposit estimate disclosure', () => {
  it('labels simple-interest values as estimates and discloses omitted terms', async () => {
    const [page, table] = await Promise.all([
      source('views/dashboard/FixedDepositsTab.vue'),
      source('components/dashboard/FixedDepositTable.vue')
    ])

    expect(page).toContain('value-title="Estimated current value"')
    expect(page).toContain('return-title="Estimated accrued interest"')
    expect(page).toContain('Compounding frequency, payout')
    expect(page).toContain('bank-specific terms are not modelled')
    expect(table).toContain('Estimated accrued interest')
    expect(table).toContain('Estimated current value')
  })
})
