"""Tests for CSV bank-statement parsing, tag generation, and the CSV workflow."""

import csv
import io

from app.database import db
from app.models.bank_statement import BankStatement
from app.models.transaction import Transaction
from app.models.transaction_category import TransactionCategory
from app.services.csv_parser_service import CSVParserService
from app.utils.bank_formats import seed_bank_formats


TRADE_REPUBLIC_HEADER = [
    'datetime', 'date', 'account_type', 'category', 'type', 'asset_class',
    'name', 'symbol', 'shares', 'price', 'amount', 'fee', 'tax', 'currency',
    'original_amount', 'original_currency', 'fx_rate', 'description',
    'transaction_id', 'counterparty_name', 'counterparty_iban',
    'payment_reference', 'mcc_code',
]


def _row(**overrides):
    base = {name: '' for name in TRADE_REPUBLIC_HEADER}
    base.update(overrides)
    return [base[name] for name in TRADE_REPUBLIC_HEADER]


def _build_trade_republic_csv(rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_ALL)
    writer.writerow(TRADE_REPUBLIC_HEADER)
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


SAMPLE_ROWS = [
    _row(
        datetime='2026-03-26T17:49:02Z', date='2026-03-26',
        account_type='DEFAULT', category='CASH', type='REFERRAL',
        amount='10.000000', currency='EUR',
        description='Referral bonus of 10 EUR',
        transaction_id='tx-referral',
    ),
    _row(
        datetime='2026-03-26T17:50:14Z', date='2026-03-26',
        account_type='DEFAULT', category='TRADING', type='BUY',
        asset_class='FUND', name='FTSE All-World USD (Acc)',
        amount='-142.70', currency='EUR',
        description='Buy trade IE00BK5BQT80 Vanguard FTSE All-World',
        transaction_id='tx-buy',
    ),
]


def test_build_tags_are_structured_and_deduped():
    record = {
        'category': 'TRADING',
        'type': 'BUY',
        'name': 'FTSE All-World USD (Acc)',
        'description': 'x' * 200,  # too long -> skipped
    }
    tags = CSVParserService.build_tags(
        record, ['category', 'type', 'name', 'description', 'category']
    )
    assert tags == [
        'category:TRADING',
        'type:BUY',
        'name:FTSE All-World USD (Acc)',
    ]


def test_detect_format_matches_trade_republic(app, tmp_path):
    with app.app_context():
        seed_bank_formats()
        csv_path = tmp_path / 'tr.csv'
        csv_path.write_text(_build_trade_republic_csv(SAMPLE_ROWS))

        template = CSVParserService.detect_format(str(csv_path))
        assert template is not None
        assert template.bank_name == 'Trade Republic'
        assert template.file_format == 'csv'


def test_detect_format_rejects_unknown_csv(app, tmp_path):
    with app.app_context():
        seed_bank_formats()
        csv_path = tmp_path / 'other.csv'
        csv_path.write_text('foo,bar,baz\n1,2,3\n')
        assert CSVParserService.detect_format(str(csv_path)) is None


def test_parse_maps_signed_amount_and_generates_tags(app, tmp_path):
    with app.app_context():
        seed_bank_formats()
        csv_path = tmp_path / 'tr.csv'
        csv_path.write_text(_build_trade_republic_csv(SAMPLE_ROWS))

        bank_name, transactions = CSVParserService.parse_file(str(csv_path))

    assert bank_name == 'Trade Republic'
    assert len(transactions) == 2

    credit = transactions[0]
    assert credit['transaction_type'] == 'credit'
    assert str(credit['amount']) == '10.000000'
    assert credit['balance'] is None
    assert 'category:CASH' in credit['tags']
    assert 'type:REFERRAL' in credit['tags']

    debit = transactions[1]
    assert debit['transaction_type'] == 'debit'
    assert str(debit['amount']) == '142.70'
    assert 'category:TRADING' in debit['tags']
    assert 'type:BUY' in debit['tags']
    assert 'name:FTSE All-World USD (Acc)' in debit['tags']


def test_parse_file_unknown_format_raises(app, tmp_path):
    with app.app_context():
        seed_bank_formats()
        csv_path = tmp_path / 'unknown.csv'
        csv_path.write_text('a,b,c\n1,2,3\n')
        try:
            CSVParserService.parse_file(str(csv_path))
        except ValueError as error:
            assert 'Unrecognized CSV format' in str(error)
        else:
            raise AssertionError('Expected ValueError for unknown CSV format')


def test_csv_upload_parse_review_approve_persists_tags(
    app, client, auth_headers, sample_bank_account
):
    """A Trade Republic CSV flows through the workflow and stores its tags."""
    with app.app_context():
        seed_bank_formats()
        db.session.add(
            TransactionCategory(
                name='Uncategorized', icon='❓', color='#9ca3af', keywords=[]
            )
        )
        db.session.commit()

    csv_bytes = _build_trade_republic_csv(SAMPLE_ROWS).encode('utf-8')
    uploaded = client.post(
        f'/api/bank-accounts/{sample_bank_account["id"]}/statements/upload',
        data={'file': (io.BytesIO(csv_bytes), 'transactions.csv')},
        content_type='multipart/form-data',
        headers=auth_headers,
    )
    assert uploaded.status_code == 202
    statement_id = uploaded.get_json()['statement_id']

    parsed = client.post(
        f'/api/statements/{statement_id}/parse', headers=auth_headers
    )
    assert parsed.status_code == 200, parsed.get_json()

    preview = client.get(
        f'/api/statements/{statement_id}/preview', headers=auth_headers
    )
    assert preview.status_code == 200
    transactions = preview.get_json()['transactions']
    assert len(transactions) == 2
    assert any(t['tags'] for t in transactions)

    approved = client.post(
        f'/api/statements/{statement_id}/approve',
        json={'transactions': transactions},
        headers=auth_headers,
    )
    assert approved.status_code == 200, approved.get_json()

    with app.app_context():
        stored = (
            Transaction.query.filter_by(statement_id=statement_id)
            .order_by(Transaction.id)
            .all()
        )
        assert len(stored) == 2
        all_tags = {tag for txn in stored for tag in (txn.tags or [])}
        assert 'category:TRADING' in all_tags
        assert 'type:BUY' in all_tags
        assert 'name:FTSE All-World USD (Acc)' in all_tags
