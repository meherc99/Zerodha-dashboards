"""End-to-end regression coverage for the bank-statement API contract."""

from datetime import date, timedelta
import io

from app.database import db
from app.models.bank_account import BankAccount
from app.models.bank_statement import BankStatement
from app.models.transaction import Transaction
from app.models.transaction_category import TransactionCategory
from app.services.pdf_parser_service import PDFParserService
import app.services.bank_statement_service as bank_statement_service


def test_upload_parse_review_approve_and_analyze_canonical_statement(
    app,
    client,
    auth_headers,
    other_auth_headers,
    sample_bank_account,
    monkeypatch,
    tmp_path,
):
    """Every boundary uses one DTO and approved data feeds verified analytics."""
    monkeypatch.setattr(
        bank_statement_service,
        'UPLOAD_BASE_DIR',
        str(tmp_path / 'statements'),
    )
    transaction_date = date.today() - timedelta(days=2)

    with app.app_context():
        groceries = TransactionCategory(
            name='Groceries',
            icon='🛒',
            color='#10b981',
            keywords=['bigbasket'],
        )
        uncategorized = TransactionCategory(
            name='Uncategorized',
            icon='❓',
            color='#9ca3af',
            keywords=[],
        )
        db.session.add_all([groceries, uncategorized])
        db.session.commit()
        groceries_id = groceries.id

    uploaded = client.post(
        (
            f'/api/bank-accounts/{sample_bank_account["id"]}'
            '/statements/upload'
        ),
        data={
            'file': (
                io.BytesIO(b'%PDF-1.4\ncanonical workflow'),
                'statement.pdf',
            )
        },
        content_type='multipart/form-data',
        headers=auth_headers,
    )
    assert uploaded.status_code == 202
    statement_id = uploaded.get_json()['statement_id']

    def fake_parse(parsed_statement_id):
        statement = db.session.get(BankStatement, parsed_statement_id)
        statement.statement_period_start = transaction_date
        statement.statement_period_end = transaction_date
        statement.parsed_data = {
            'bank_name': 'Unknown',
            'transactions': [
                {
                    # Parser storage remains implementation-private; both
                    # spellings make this fixture compatible while the API
                    # response below is asserted to be canonical.
                    'date': transaction_date.isoformat(),
                    'transaction_date': transaction_date.isoformat(),
                    'description': 'BIGBASKET WEEKLY ORDER',
                    'amount': '250.00',
                    'transaction_type': 'debit',
                    'balance': '750.00',
                    'running_balance': '750.00',
                }
            ],
        }
        statement.status = 'review'
        db.session.commit()
        return statement.parsed_data

    monkeypatch.setattr(
        PDFParserService,
        'parse_statement',
        staticmethod(fake_parse),
    )

    hidden = client.post(
        f'/api/statements/{statement_id}/parse',
        headers=other_auth_headers,
    )
    assert hidden.status_code == 404

    parsed = client.post(
        f'/api/statements/{statement_id}/parse',
        headers=auth_headers,
    )
    assert parsed.status_code == 200
    assert parsed.get_json() == {
        'statement_id': statement_id,
        'status': 'review',
    }

    preview = client.get(
        f'/api/statements/{statement_id}/preview',
        headers=auth_headers,
    )
    assert preview.status_code == 200
    preview_data = preview.get_json()
    assert preview_data['statement']['status'] == 'review'
    assert len(preview_data['transactions']) == 1
    review_transaction = preview_data['transactions'][0]
    assert set(review_transaction) == {
        'transaction_date',
        'description',
        'amount',
        'transaction_type',
        'running_balance',
        'category_id',
        'category_confidence',
        'notes',
    }
    assert review_transaction == {
        'transaction_date': transaction_date.isoformat(),
        'description': 'BIGBASKET WEEKLY ORDER',
        'amount': '250.00',
        'transaction_type': 'debit',
        'running_balance': '750.00',
        'category_id': groceries_id,
        'category_confidence': 0.8,
        'notes': '',
    }

    approved = client.post(
        f'/api/statements/{statement_id}/approve',
        json={'transactions': preview_data['transactions']},
        headers=auth_headers,
    )
    assert approved.status_code == 200
    assert approved.get_json()['transaction_count'] == 1

    balance = client.get(
        (
            f'/api/bank-accounts/{sample_bank_account["id"]}'
            '/analytics/balance-trend?days=30'
        ),
        headers=auth_headers,
    )
    assert balance.status_code == 200
    assert balance.get_json()['dates'] == [transaction_date.isoformat()]
    assert balance.get_json()['balances'] == [750.0]

    spending = client.get(
        (
            f'/api/bank-accounts/{sample_bank_account["id"]}'
            '/analytics/category-breakdown?period_days=30'
        ),
        headers=auth_headers,
    )
    assert spending.status_code == 200
    assert spending.get_json()['total_spending'] == 250.0
    assert spending.get_json()['categories'][0]['id'] == groceries_id

    with app.app_context():
        statement = db.session.get(BankStatement, statement_id)
        transaction = Transaction.query.filter_by(
            statement_id=statement_id
        ).one()
        account = db.session.get(
            BankAccount,
            sample_bank_account['id'],
        )
        assert statement.status == 'approved'
        assert transaction.verified is True
        assert float(account.current_balance) == 750.0
        assert account.last_statement_date == transaction_date


def test_statement_approval_rejects_non_object_and_unknown_fields(
    client,
    auth_headers,
):
    for body in ('[]', 'null', '{broken'):
        response = client.post(
            '/api/statements/1/approve',
            data=body,
            content_type='application/json',
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert response.get_json()['error'] == 'Invalid JSON data'

    unknown = client.post(
        '/api/statements/1/approve',
        json={'transactions': [], 'user_id': 123},
        headers=auth_headers,
    )
    assert unknown.status_code == 400
    assert unknown.get_json()['error'] == 'Unsupported field: user_id'
