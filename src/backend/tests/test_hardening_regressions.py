"""Focused regressions for security and financial-integrity hardening."""

from datetime import date, datetime, timedelta
from decimal import Decimal
import io
import os
import stat
import threading

from cryptography.fernet import Fernet
import pandas as pd
import pytest

from app import create_app
from app.database import db
from app.models import (
    Account,
    BankAccount,
    BankStatement,
    Holding,
    PortfolioTimeseries,
    RateLimitBucket,
    Snapshot,
    Transaction,
    TransactionCategory,
    User,
)
from app.services.analytics_service import AnalyticsService
from app.services.bank_analytics_service import BankAnalyticsService
from app.services.bank_statement_service import BankStatementService
from app.services.fd_service import FDService
from app.services.pdf_parser_service import (
    MAX_PDF_PAGES,
    PARSING_LEASE_MINUTES,
    PDFParserService,
)
from app.services.portfolio_service import PortfolioService
from app.services.us_holdings_service import USHoldingsService
import app.services.bank_statement_service as bank_statement_service
import app.services.pdf_parser_service as pdf_parser_service


def _statement(
    bank_account_id,
    path,
    *,
    status='uploaded',
    period_start=date(2026, 1, 1),
    period_end=date(2026, 1, 31),
    parsed_data=None,
):
    statement = BankStatement(
        bank_account_id=bank_account_id,
        statement_period_start=period_start,
        statement_period_end=period_end,
        pdf_file_path=str(path),
        status=status,
        parsed_data=parsed_data,
    )
    db.session.add(statement)
    db.session.flush()
    return statement


def _review_transaction(**overrides):
    transaction = {
        'transaction_date': '2026-01-15',
        'description': 'Statement transaction',
        'amount': '100.00',
        'transaction_type': 'debit',
        'running_balance': '900.00',
        'category_id': None,
        'category_confidence': None,
        'notes': None,
    }
    transaction.update(overrides)
    return transaction


def test_identical_statement_content_is_rejected_per_bank_account(
    app,
    client,
    auth_headers,
    sample_bank_account,
    monkeypatch,
    tmp_path,
):
    upload_root = tmp_path / 'statements'
    monkeypatch.setattr(
        bank_statement_service,
        'UPLOAD_BASE_DIR',
        str(upload_root),
    )
    content = b'%PDF-1.4\nidentical statement bytes'
    endpoint = (
        f'/api/bank-accounts/{sample_bank_account["id"]}/statements/upload'
    )

    first = client.post(
        endpoint,
        data={'file': (io.BytesIO(content), 'january.pdf')},
        content_type='multipart/form-data',
        headers=auth_headers,
    )
    duplicate = client.post(
        endpoint,
        data={'file': (io.BytesIO(content), 'renamed.pdf')},
        content_type='multipart/form-data',
        headers=auth_headers,
    )

    assert first.status_code == 202
    assert duplicate.status_code == 400
    assert 'already been uploaded' in duplicate.get_json()['error']
    with app.app_context():
        statements = BankStatement.query.filter_by(
            bank_account_id=sample_bank_account['id']
        ).all()
        assert len(statements) == 1
        assert len(statements[0].file_sha256) == 64
    assert len(list(upload_root.rglob('*.pdf'))) == 1
    for directory in (
        upload_root,
        upload_root / str(sample_bank_account['user_id']),
        upload_root
        / str(sample_bank_account['user_id'])
        / str(sample_bank_account['id']),
    ):
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700


def test_failed_upload_cleanup_retains_authenticated_retry_tombstone(
    app,
    sample_bank_account,
    monkeypatch,
    tmp_path,
):
    upload_root = tmp_path / 'statements'
    monkeypatch.setattr(
        bank_statement_service,
        'UPLOAD_BASE_DIR',
        str(upload_root),
    )

    class FailingUpload:
        filename = 'partial.pdf'

        def __init__(self):
            self.stream = io.BytesIO(b'%PDF-1.4\nprivate partial content')

        def seek(self, *args):
            return self.stream.seek(*args)

        def tell(self):
            return self.stream.tell()

        def read(self, *args):
            return self.stream.read(*args)

        def save(self, destination):
            with open(destination, 'wb') as saved:
                saved.write(self.stream.read())
            raise OSError('simulated interrupted upload')

    real_remove = os.remove
    monkeypatch.setattr(
        bank_statement_service.os,
        'remove',
        lambda _path: (_ for _ in ()).throw(
            OSError('simulated cleanup failure')
        ),
    )

    with app.app_context():
        with pytest.raises(RuntimeError, match='Failed to save statement'):
            BankStatementService.process_upload(
                FailingUpload(),
                sample_bank_account['id'],
                sample_bank_account['user_id'],
            )

        statement = BankStatement.query.filter_by(
            bank_account_id=sample_bank_account['id']
        ).one()
        statement_id = statement.id
        statement_path = statement.pdf_file_path
        assert statement.status == 'deleting'
        assert 'retry' in statement.error_message.lower()
        assert os.path.exists(statement_path)

        monkeypatch.setattr(
            bank_statement_service.os,
            'remove',
            real_remove,
        )
        BankStatementService.delete_statement(
            statement_id,
            sample_bank_account['user_id'],
        )
        assert db.session.get(BankStatement, statement_id) is None
        assert not os.path.exists(statement_path)


def test_statement_lists_are_metadata_only(
    app,
    client,
    auth_headers,
    sample_bank_account,
):
    with app.app_context():
        _statement(
            sample_bank_account['id'],
            '/private/statement.pdf',
            status='review',
            parsed_data={
                'transactions': [
                    {
                        'description': 'private merchant',
                        'amount': '125.00',
                    }
                ]
            },
        )
        db.session.commit()

    response = client.get(
        (
            f'/api/bank-accounts/{sample_bank_account["id"]}'
            '/statements'
        ),
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert len(response.get_json()) == 1
    assert 'parsed_data' not in response.get_json()[0]
    assert 'pdf_file_path' not in response.get_json()[0]


def test_approval_clears_transient_parsed_statement_data(
    app,
    sample_user,
    sample_bank_account,
):
    with app.app_context():
        statement = _statement(
            sample_bank_account['id'],
            '/private/statement.pdf',
            status='review',
            parsed_data={'transactions': [{'description': 'sensitive'}]},
        )
        statement_id = statement.id
        db.session.commit()

        result = BankStatementService.approve_statement(
            statement_id,
            [_review_transaction()],
            sample_user['id'],
        )

        assert result['transaction_count'] == 1
        statement = db.session.get(BankStatement, statement_id)
        assert statement.status == 'approved'
        assert statement.parsed_data is None
        assert statement.parsing_template_id is None


def test_delete_failure_leaves_retryable_tombstone_and_retry_recomputes_state(
    app,
    client,
    auth_headers,
    sample_bank_account,
    monkeypatch,
    tmp_path,
):
    older_path = tmp_path / 'older.pdf'
    latest_path = tmp_path / 'latest.pdf'
    older_path.write_bytes(b'older')
    latest_path.write_bytes(b'latest')

    with app.app_context():
        older = _statement(
            sample_bank_account['id'],
            older_path,
            status='approved',
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        latest = _statement(
            sample_bank_account['id'],
            latest_path,
            status='approved',
            period_start=date(2026, 2, 1),
            period_end=date(2026, 2, 28),
        )
        db.session.add_all(
            [
                Transaction(
                    statement_id=older.id,
                    bank_account_id=sample_bank_account['id'],
                    transaction_date=date(2026, 1, 31),
                    description='Older balance',
                    amount=Decimal('100.00'),
                    transaction_type='credit',
                    running_balance=Decimal('1000.00'),
                    verified=True,
                ),
                Transaction(
                    statement_id=latest.id,
                    bank_account_id=sample_bank_account['id'],
                    transaction_date=date(2026, 2, 28),
                    description='Latest balance',
                    amount=Decimal('250.00'),
                    transaction_type='credit',
                    running_balance=Decimal('1250.00'),
                    verified=True,
                ),
            ]
        )
        account = db.session.get(
            BankAccount,
            sample_bank_account['id'],
        )
        account.current_balance = Decimal('1250.00')
        account.last_statement_date = date(2026, 2, 28)
        latest_id = latest.id
        older_id = older.id
        db.session.commit()

    real_remove = os.remove
    attempts = 0

    def fail_once(path):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError('simulated filesystem failure')
        return real_remove(path)

    monkeypatch.setattr(bank_statement_service.os, 'remove', fail_once)

    failed = client.delete(
        f'/api/statements/{latest_id}',
        headers=auth_headers,
    )
    assert failed.status_code == 500
    assert latest_path.exists()
    with app.app_context():
        tombstone = db.session.get(BankStatement, latest_id)
        account = db.session.get(BankAccount, sample_bank_account['id'])
        assert tombstone.status == 'deleting'
        assert 'retry' in tombstone.error_message.lower()
        assert account.current_balance == Decimal('1250.00')
        assert account.last_statement_date == date(2026, 2, 28)

    retried = client.delete(
        f'/api/statements/{latest_id}',
        headers=auth_headers,
    )
    assert retried.status_code == 200
    assert not latest_path.exists()
    with app.app_context():
        assert db.session.get(BankStatement, latest_id) is None
        assert db.session.get(BankStatement, older_id) is not None
        account = db.session.get(BankAccount, sample_bank_account['id'])
        assert account.current_balance == Decimal('1000.00')
        assert account.last_statement_date == date(2026, 1, 31)


def test_deleting_latest_standalone_transaction_recomputes_cached_balance(
    app,
    client,
    auth_headers,
    sample_bank_account,
):
    with app.app_context():
        older = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 1),
            description='Older standalone balance',
            amount=Decimal('100.00'),
            transaction_type='credit',
            running_balance=Decimal('1000.00'),
            verified=True,
        )
        latest = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 2),
            description='Latest standalone balance',
            amount=Decimal('200.00'),
            transaction_type='credit',
            running_balance=Decimal('1200.00'),
            verified=True,
        )
        db.session.add_all([older, latest])
        account = db.session.get(BankAccount, sample_bank_account['id'])
        account.current_balance = Decimal('1200.00')
        db.session.flush()
        latest_id = latest.id
        older_id = older.id
        db.session.commit()

    response = client.delete(
        f'/api/transactions/{latest_id}',
        headers=auth_headers,
    )

    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(Transaction, latest_id) is None
        assert db.session.get(Transaction, older_id) is not None
        account = db.session.get(BankAccount, sample_bank_account['id'])
        assert account.current_balance == Decimal('1000.00')


def test_transaction_verification_changes_recompute_cached_balance(
    app,
    client,
    auth_headers,
    sample_bank_account,
):
    with app.app_context():
        older = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 1),
            description='Older verified balance',
            amount=Decimal('100.00'),
            transaction_type='credit',
            running_balance=Decimal('1000.00'),
            verified=True,
        )
        latest = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 3, 2),
            description='Latest verified balance',
            amount=Decimal('200.00'),
            transaction_type='credit',
            running_balance=Decimal('1200.00'),
            verified=True,
        )
        db.session.add_all([older, latest])
        account = db.session.get(BankAccount, sample_bank_account['id'])
        account.current_balance = Decimal('1200.00')
        db.session.flush()
        latest_id = latest.id
        db.session.commit()

    unverified = client.put(
        f'/api/transactions/{latest_id}',
        json={'verified': False},
        headers=auth_headers,
    )
    assert unverified.status_code == 200
    assert unverified.get_json()['verified'] is False
    with app.app_context():
        account = db.session.get(BankAccount, sample_bank_account['id'])
        assert account.current_balance == Decimal('1000.00')

    reverified = client.put(
        f'/api/transactions/{latest_id}',
        json={'verified': True},
        headers=auth_headers,
    )
    assert reverified.status_code == 200
    assert reverified.get_json()['verified'] is True
    with app.app_context():
        account = db.session.get(BankAccount, sample_bank_account['id'])
        assert account.current_balance == Decimal('1200.00')


def test_recalculation_falls_back_to_manual_opening_balance(
    app,
    client,
    auth_headers,
):
    created = client.post(
        '/api/bank-accounts',
        json={
            'bank_name': 'Opening Balance Bank',
            'account_number': '123456789012',
            'current_balance': '4321.50',
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    account_id = created.get_json()['id']
    assert created.get_json()['opening_balance'] == '4321.50'

    with app.app_context():
        transaction = Transaction(
            bank_account_id=account_id,
            transaction_date=date(2026, 3, 2),
            description='Only verified balance',
            amount=Decimal('678.50'),
            transaction_type='credit',
            running_balance=Decimal('5000.00'),
            verified=True,
        )
        db.session.add(transaction)
        account = db.session.get(BankAccount, account_id)
        account.current_balance = Decimal('5000.00')
        db.session.flush()
        transaction_id = transaction.id
        db.session.commit()

    deleted = client.delete(
        f'/api/transactions/{transaction_id}',
        headers=auth_headers,
    )
    assert deleted.status_code == 200
    with app.app_context():
        account = db.session.get(BankAccount, account_id)
        assert account.opening_balance == Decimal('4321.50')
        assert account.current_balance == Decimal('4321.50')


def test_approving_older_statement_preserves_newest_cached_account_state(
    app,
    client,
    auth_headers,
    sample_bank_account,
):
    with app.app_context():
        newer = _statement(
            sample_bank_account['id'],
            '/private/newer.pdf',
            status='approved',
            period_start=date(2026, 2, 1),
            period_end=date(2026, 2, 28),
        )
        db.session.add(
            Transaction(
                statement_id=newer.id,
                bank_account_id=sample_bank_account['id'],
                transaction_date=date(2026, 2, 28),
                description='Newer closing balance',
                amount=Decimal('1000.00'),
                transaction_type='credit',
                running_balance=Decimal('2000.00'),
                verified=True,
            )
        )
        older = _statement(
            sample_bank_account['id'],
            '/private/older-review.pdf',
            status='review',
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            parsed_data={'transactions': []},
        )
        account = db.session.get(BankAccount, sample_bank_account['id'])
        account.current_balance = Decimal('2000.00')
        account.last_statement_date = date(2026, 2, 28)
        older_id = older.id
        db.session.commit()

    response = client.post(
        f'/api/statements/{older_id}/approve',
        json={
            'transactions': [
                _review_transaction(
                    transaction_date='2026-01-31',
                    running_balance='1000.00',
                )
            ]
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    with app.app_context():
        account = db.session.get(BankAccount, sample_bank_account['id'])
        assert account.current_balance == Decimal('2000.00')
        assert account.last_statement_date == date(2026, 2, 28)
        assert db.session.get(BankStatement, older_id).status == 'approved'


def test_statement_period_overlap_is_rejected_but_adjacent_period_is_allowed(
    app,
    sample_bank_account,
):
    with app.app_context():
        existing = _statement(
            sample_bank_account['id'],
            '/private/january.pdf',
            status='approved',
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        db.session.commit()

        overlap = BankStatementService.find_duplicate_statement(
            sample_bank_account['id'],
            date(2026, 1, 15),
            date(2026, 2, 15),
        )
        adjacent = BankStatementService.find_duplicate_statement(
            sample_bank_account['id'],
            date(2026, 2, 1),
            date(2026, 2, 28),
        )
        shared_boundary = BankStatementService.find_duplicate_statement(
            sample_bank_account['id'],
            date(2026, 1, 31),
            date(2026, 2, 28),
        )

        assert overlap.id == existing.id
        assert shared_boundary.id == existing.id
        assert adjacent is None


def test_bank_account_delete_erases_rows_and_owned_statement_file(
    app,
    client,
    auth_headers,
    sample_bank_account,
    monkeypatch,
    tmp_path,
):
    upload_root = tmp_path / 'account-uploads'
    monkeypatch.setattr(
        bank_statement_service,
        'UPLOAD_BASE_DIR',
        str(upload_root),
    )
    account_directory = (
        upload_root
        / str(sample_bank_account['user_id'])
        / str(sample_bank_account['id'])
    )
    account_directory.mkdir(parents=True)
    statement_path = account_directory / 'owned.pdf'
    statement_path.write_bytes(b'%PDF-1.4\nowned')
    orphan_path = account_directory / 'orphan.pdf'
    orphan_path.write_bytes(b'%PDF-1.4\nlegacy orphan')

    with app.app_context():
        statement = _statement(
            sample_bank_account['id'],
            statement_path,
            status='approved',
        )
        transaction = Transaction(
            statement_id=statement.id,
            bank_account_id=sample_bank_account['id'],
            transaction_date=date(2026, 1, 31),
            description='Account-scoped transaction',
            amount=Decimal('50.00'),
            transaction_type='debit',
            running_balance=Decimal('950.00'),
            verified=True,
        )
        db.session.add(transaction)
        statement_id = statement.id
        db.session.flush()
        transaction_id = transaction.id
        db.session.commit()

    response = client.delete(
        f'/api/bank-accounts/{sample_bank_account["id"]}',
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert not statement_path.exists()
    assert not orphan_path.exists()
    assert not account_directory.exists()
    with app.app_context():
        assert db.session.get(
            BankAccount,
            sample_bank_account['id'],
        ) is None
        assert db.session.get(BankStatement, statement_id) is None
        assert db.session.get(Transaction, transaction_id) is None


def test_bank_account_file_removal_failure_is_active_and_retryable(
    app,
    client,
    auth_headers,
    sample_bank_account,
    monkeypatch,
    tmp_path,
):
    upload_root = tmp_path / 'account-uploads'
    monkeypatch.setattr(
        bank_statement_service,
        'UPLOAD_BASE_DIR',
        str(upload_root),
    )
    account_directory = (
        upload_root
        / str(sample_bank_account['user_id'])
        / str(sample_bank_account['id'])
    )
    account_directory.mkdir(parents=True)
    statement_path = account_directory / 'retry.pdf'
    statement_path.write_bytes(b'%PDF-1.4\nretry')

    with app.app_context():
        statement = _statement(
            sample_bank_account['id'],
            statement_path,
            status='uploaded',
        )
        statement_id = statement.id
        db.session.commit()

    real_remove = os.remove
    monkeypatch.setattr(
        bank_statement_service.os,
        'remove',
        lambda _path: (_ for _ in ()).throw(
            OSError('simulated removal failure')
        ),
    )

    failed = client.delete(
        f'/api/bank-accounts/{sample_bank_account["id"]}',
        headers=auth_headers,
    )

    assert failed.status_code == 500
    assert statement_path.exists()
    with app.app_context():
        account = db.session.get(BankAccount, sample_bank_account['id'])
        assert account is not None
        assert account.is_active is True
        assert db.session.get(BankStatement, statement_id) is not None

    monkeypatch.setattr(bank_statement_service.os, 'remove', real_remove)
    retried = client.delete(
        f'/api/bank-accounts/{sample_bank_account["id"]}',
        headers=auth_headers,
    )
    assert retried.status_code == 200
    assert not statement_path.exists()
    with app.app_context():
        assert db.session.get(
            BankAccount,
            sample_bank_account['id'],
        ) is None


def test_bank_account_delete_refuses_symlinked_orphan(
    app,
    client,
    auth_headers,
    sample_bank_account,
    monkeypatch,
    tmp_path,
):
    upload_root = tmp_path / 'account-uploads'
    monkeypatch.setattr(
        bank_statement_service,
        'UPLOAD_BASE_DIR',
        str(upload_root),
    )
    account_directory = (
        upload_root
        / str(sample_bank_account['user_id'])
        / str(sample_bank_account['id'])
    )
    account_directory.mkdir(parents=True)
    outside_path = tmp_path / 'outside.pdf'
    outside_path.write_bytes(b'%PDF-1.4\noutside')
    (account_directory / 'unsafe.pdf').symlink_to(outside_path)

    response = client.delete(
        f'/api/bank-accounts/{sample_bank_account["id"]}',
        headers=auth_headers,
    )

    assert response.status_code == 500
    assert outside_path.read_bytes() == b'%PDF-1.4\noutside'
    with app.app_context():
        account = db.session.get(BankAccount, sample_bank_account['id'])
        assert account is not None
        assert account.is_active is True


def test_bank_account_database_delete_failure_reactivates_for_retry(
    app,
    sample_bank_account,
    monkeypatch,
    tmp_path,
):
    upload_root = tmp_path / 'account-uploads'
    monkeypatch.setattr(
        bank_statement_service,
        'UPLOAD_BASE_DIR',
        str(upload_root),
    )
    account_directory = (
        upload_root
        / str(sample_bank_account['user_id'])
        / str(sample_bank_account['id'])
    )
    account_directory.mkdir(parents=True)
    statement_path = account_directory / 'database-retry.pdf'
    statement_path.write_bytes(b'%PDF-1.4\ndatabase retry')

    with app.app_context():
        _statement(
            sample_bank_account['id'],
            statement_path,
            status='uploaded',
        )
        db.session.commit()
        account = db.session.get(
            BankAccount,
            sample_bank_account['id'],
        )

        real_commit = db.session.commit
        commit_count = 0

        def fail_database_delete_once():
            nonlocal commit_count
            commit_count += 1
            if commit_count == 2:
                raise RuntimeError('simulated database deletion failure')
            return real_commit()

        monkeypatch.setattr(
            db.session,
            'commit',
            fail_database_delete_once,
        )
        with pytest.raises(RuntimeError, match='Failed to delete bank account'):
            BankStatementService.permanently_delete_account(account)

        assert not statement_path.exists()
        remaining = db.session.get(
            BankAccount,
            sample_bank_account['id'],
        )
        assert remaining is not None
        assert remaining.is_active is True

        monkeypatch.setattr(db.session, 'commit', real_commit)
        BankStatementService.permanently_delete_account(remaining)
        assert db.session.get(
            BankAccount,
            sample_bank_account['id'],
        ) is None


def test_busy_statement_blocks_bank_account_deletion_before_file_removal(
    app,
    client,
    auth_headers,
    sample_bank_account,
    monkeypatch,
    tmp_path,
):
    upload_root = tmp_path / 'account-uploads'
    monkeypatch.setattr(
        bank_statement_service,
        'UPLOAD_BASE_DIR',
        str(upload_root),
    )
    account_directory = (
        upload_root
        / str(sample_bank_account['user_id'])
        / str(sample_bank_account['id'])
    )
    account_directory.mkdir(parents=True)
    statement_path = account_directory / 'busy.pdf'
    statement_path.write_bytes(b'%PDF-1.4\nbusy')

    with app.app_context():
        statement = _statement(
            sample_bank_account['id'],
            statement_path,
            status='parsing',
        )
        statement.parsing_started_at = datetime.utcnow()
        statement_id = statement.id
        db.session.commit()

    response = client.delete(
        f'/api/bank-accounts/{sample_bank_account["id"]}',
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert 'in progress' in response.get_json()['error']
    assert statement_path.exists()
    with app.app_context():
        account = db.session.get(BankAccount, sample_bank_account['id'])
        assert account is not None
        assert account.is_active is True
        assert db.session.get(BankStatement, statement_id) is not None


def test_inactive_bank_accounts_are_hidden_from_every_operation(
    app,
    client,
    auth_headers,
    sample_bank_account,
):
    with app.app_context():
        statement = _statement(
            sample_bank_account['id'],
            '/private/inactive.pdf',
            status='review',
            parsed_data={'transactions': []},
        )
        transaction = Transaction(
            statement_id=statement.id,
            bank_account_id=sample_bank_account['id'],
            transaction_date=date.today(),
            description='Must remain hidden',
            amount=Decimal('25.00'),
            transaction_type='debit',
            running_balance=Decimal('975.00'),
            verified=True,
        )
        db.session.add(transaction)
        account = db.session.get(BankAccount, sample_bank_account['id'])
        account.is_active = False
        statement_id = statement.id
        db.session.commit()

    account_id = sample_bank_account['id']
    reads = (
        f'/api/bank-accounts/{account_id}',
        f'/api/bank-accounts/{account_id}/statements',
        f'/api/statements/{statement_id}',
        f'/api/statements/{statement_id}/preview',
        f'/api/bank-accounts/{account_id}/transactions',
        (
            f'/api/bank-accounts/{account_id}'
            '/analytics/category-breakdown'
        ),
    )
    for endpoint in reads:
        response = client.get(endpoint, headers=auth_headers)
        assert response.status_code == 404, endpoint

    assert client.post(
        f'/api/statements/{statement_id}/parse',
        headers=auth_headers,
    ).status_code == 404
    assert client.post(
        f'/api/statements/{statement_id}/approve',
        json={'transactions': [_review_transaction()]},
        headers=auth_headers,
    ).status_code == 404
    assert client.delete(
        f'/api/statements/{statement_id}',
        headers=auth_headers,
    ).status_code == 404

    global_search = client.get(
        '/api/transactions/search?search=hidden',
        headers=auth_headers,
    )
    assert global_search.status_code == 200
    assert global_search.get_json()['total'] == 0
    assert global_search.get_json()['transactions'] == []


def test_legacy_categories_are_hidden_and_rejected_at_write_boundaries(
    app,
    client,
    auth_headers,
    sample_user,
    sample_bank_account,
):
    with app.app_context():
        system = TransactionCategory(
            name='System Groceries',
            icon='cart',
            color='#00aa00',
            keywords=['grocery'],
            is_system=True,
        )
        legacy = TransactionCategory(
            name='Private Legacy Label',
            icon='lock',
            color='#aa0000',
            keywords=['private'],
            is_system=False,
        )
        db.session.add_all([system, legacy])
        db.session.flush()
        legacy_transaction = Transaction(
            bank_account_id=sample_bank_account['id'],
            transaction_date=date.today(),
            description='Legacy categorized spending',
            amount=Decimal('40.00'),
            transaction_type='debit',
            running_balance=Decimal('960.00'),
            category_id=legacy.id,
            verified=True,
        )
        statement = _statement(
            sample_bank_account['id'],
            '/private/category-review.pdf',
            status='review',
            parsed_data={'transactions': []},
        )
        db.session.add(legacy_transaction)
        db.session.flush()
        system_id = system.id
        legacy_id = legacy.id
        transaction_id = legacy_transaction.id
        statement_id = statement.id
        db.session.commit()

    categories = client.get('/api/categories', headers=auth_headers)
    assert categories.status_code == 200
    assert [category['id'] for category in categories.get_json()] == [
        system_id
    ]
    assert all(
        category['name'] != 'Private Legacy Label'
        for category in categories.get_json()
    )

    updated = client.put(
        f'/api/transactions/{transaction_id}',
        json={'category_id': legacy_id},
        headers=auth_headers,
    )
    assert updated.status_code == 400
    assert updated.get_json()['error'] == 'Invalid category_id'

    bulk = client.post(
        '/api/transactions/bulk-recategorize',
        json={
            'transaction_ids': [transaction_id],
            'category_id': legacy_id,
        },
        headers=auth_headers,
    )
    assert bulk.status_code == 400
    assert bulk.get_json()['error'] == 'Invalid category_id'

    approved = client.post(
        f'/api/statements/{statement_id}/approve',
        json={
            'transactions': [
                _review_transaction(category_id=legacy_id)
            ]
        },
        headers=auth_headers,
    )
    assert approved.status_code == 400
    assert approved.get_json()['error'] == f'Invalid category_id: {legacy_id}'
    with app.app_context():
        statement = db.session.get(BankStatement, statement_id)
        assert statement.status == 'review'
        assert statement.parsed_data == {'transactions': []}
        assert Transaction.query.filter_by(
            statement_id=statement_id
        ).count() == 0

    analytics = client.get(
        (
            f'/api/bank-accounts/{sample_bank_account["id"]}'
            '/analytics/category-breakdown?period_days=30'
        ),
        headers=auth_headers,
    )
    assert analytics.status_code == 200
    breakdown = analytics.get_json()
    assert breakdown['total_spending'] == 40.0
    assert breakdown['categories'][0]['name'] == 'Uncategorized'
    assert breakdown['categories'][0]['icon'] == '❓'
    assert breakdown['categories'][0]['color'] == '#9ca3af'
    assert 'Private Legacy Label' not in str(breakdown)


def test_anomaly_serialization_redacts_legacy_category(
    app,
    client,
    auth_headers,
    sample_bank_account,
):
    with app.app_context():
        legacy = TransactionCategory(
            name='Legacy Anomaly Label',
            icon='lock',
            color='#aa0000',
            keywords=['private'],
            is_system=False,
        )
        db.session.add(legacy)
        db.session.flush()
        for index in range(9):
            db.session.add(
                Transaction(
                    bank_account_id=sample_bank_account['id'],
                    transaction_date=date.today(),
                    description=f'Ordinary debit {index}',
                    amount=Decimal('10.00'),
                    transaction_type='debit',
                    verified=True,
                )
            )
        db.session.add(
            Transaction(
                bank_account_id=sample_bank_account['id'],
                transaction_date=date.today(),
                description='Outlier with legacy category',
                amount=Decimal('1000.00'),
                transaction_type='debit',
                category_id=legacy.id,
                verified=True,
            )
        )
        db.session.commit()

    response = client.get(
        (
            f'/api/bank-accounts/{sample_bank_account["id"]}'
            '/analytics/anomalies?threshold=2'
        ),
        headers=auth_headers,
    )

    assert response.status_code == 200
    anomalies = response.get_json()['anomalies']
    assert len(anomalies) == 1
    assert anomalies[0]['description'] == 'Outlier with legacy category'
    assert anomalies[0]['category'] is None
    assert 'Legacy Anomaly Label' not in str(response.get_json())


def test_active_parser_lease_is_compare_and_swap_guarded(
    app,
    sample_bank_account,
    monkeypatch,
):
    with app.app_context():
        statement = _statement(
            sample_bank_account['id'],
            '/private/active-lease.pdf',
            status='parsing',
        )
        statement.parsing_started_at = datetime.utcnow()
        statement_id = statement.id
        db.session.commit()

        monkeypatch.setattr(
            PDFParserService,
            'extract_text',
            staticmethod(
                lambda _path: pytest.fail(
                    'a live parsing lease must not run extraction'
                )
            ),
        )

        with pytest.raises(ValueError, match='already being parsed'):
            PDFParserService.parse_statement(statement_id)
        statement = db.session.get(BankStatement, statement_id)
        assert statement.status == 'parsing'
        assert statement.parsing_started_at is not None


def test_stale_parser_lease_can_be_recovered(
    app,
    sample_bank_account,
    monkeypatch,
):
    transaction_date = date(2026, 3, 2)
    with app.app_context():
        statement = _statement(
            sample_bank_account['id'],
            '/private/stale-lease.pdf',
            status='parsing',
        )
        statement.parsing_started_at = (
            datetime.utcnow()
            - timedelta(minutes=PARSING_LEASE_MINUTES + 1)
        )
        statement_id = statement.id
        db.session.commit()

        monkeypatch.setattr(
            PDFParserService,
            'extract_text',
            staticmethod(lambda _path: 'HDFC BANK'),
        )
        monkeypatch.setattr(
            PDFParserService,
            'extract_with_pdfplumber',
            staticmethod(
                lambda _path: (
                    [
                        {
                            'date': transaction_date,
                            'description': 'Recovered parser',
                            'amount': Decimal('10.00'),
                            'transaction_type': 'debit',
                            'balance': Decimal('990.00'),
                        }
                    ],
                    0.8,
                )
            ),
        )

        result = PDFParserService.parse_statement(statement_id)

        assert result['parsed_count'] == 1
        statement = db.session.get(BankStatement, statement_id)
        assert statement.status == 'review'
        assert statement.parsing_started_at is None
        assert (
            statement.parsed_data['transactions'][0]['description']
            == 'Recovered parser'
        )


def test_reclaimed_parser_lease_cannot_be_overwritten(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / 'parser-cas.db'
    parser_app = create_app(
        {
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{database_path}',
            'JWT_SECRET_KEY': 'parser-jwt-secret-key-at-least-32-bytes',
            'SECRET_KEY': 'parser-secret-key-at-least-32-bytes',
            'ENCRYPTION_KEY': Fernet.generate_key().decode(),
            'SCHEDULER_ENABLED': False,
        }
    )
    with parser_app.app_context():
        db.create_all()
        user = User(
            email='parser-cas@example.com',
            password_hash='hash',
        )
        db.session.add(user)
        db.session.flush()
        account = BankAccount(
            user_id=user.id,
            bank_name='Test Bank',
            account_number='12345678',
        )
        db.session.add(account)
        db.session.flush()
        statement = _statement(
            account.id,
            '/private/parser-cas.pdf',
        )
        statement_id = statement.id
        db.session.commit()

    first_claimed = threading.Event()
    release_first = threading.Event()
    first_errors = []

    def fake_extract_text(_path):
        if threading.current_thread().name == 'stale-parser':
            first_claimed.set()
            assert release_first.wait(timeout=10)
        return 'Test Bank'

    def fake_extract(_path):
        worker = threading.current_thread().name
        return (
            [
                {
                    'date': date(2026, 4, 1),
                    'description': worker,
                    'amount': Decimal('10.00'),
                    'transaction_type': 'debit',
                    'balance': Decimal('990.00'),
                }
            ],
            0.8,
        )

    monkeypatch.setattr(
        PDFParserService,
        'extract_text',
        staticmethod(fake_extract_text),
    )
    monkeypatch.setattr(
        PDFParserService,
        'extract_with_pdfplumber',
        staticmethod(fake_extract),
    )

    def run_first():
        with parser_app.app_context():
            try:
                PDFParserService.parse_statement(statement_id)
            except Exception as error:
                first_errors.append(error)
            finally:
                db.session.remove()

    first = threading.Thread(target=run_first, name='stale-parser')
    try:
        first.start()
        assert first_claimed.wait(timeout=10)
        with parser_app.app_context():
            statement = db.session.get(BankStatement, statement_id)
            statement.parsing_started_at = (
                datetime.utcnow()
                - timedelta(minutes=PARSING_LEASE_MINUTES + 1)
            )
            db.session.commit()
            db.session.remove()

        with parser_app.app_context():
            PDFParserService.parse_statement(statement_id)
            db.session.remove()

        release_first.set()
        first.join(timeout=10)
        assert not first.is_alive()
        assert len(first_errors) == 1
        assert 'lease was lost' in str(first_errors[0])

        with parser_app.app_context():
            statement = db.session.get(BankStatement, statement_id)
            assert statement.status == 'review'
            assert (
                statement.parsed_data['transactions'][0]['description']
                == 'MainThread'
            )
    finally:
        release_first.set()
        first.join(timeout=10)
        with parser_app.app_context():
            db.session.remove()
            db.drop_all()


class _OversizedPDF:
    def __init__(self):
        self.pages = [_UnusedPDFPage()] * (MAX_PDF_PAGES + 1)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _UnusedPDFPage:
    def extract_text(self):
        pytest.fail('oversized PDFs must be rejected before text extraction')

    def extract_tables(self):
        pytest.fail('oversized PDFs must be rejected before table extraction')


@pytest.mark.parametrize(
    'extractor',
    [
        PDFParserService.extract_text,
        PDFParserService.extract_tables_from_pdf,
    ],
)
def test_pdf_page_cap_is_enforced_before_page_iteration(
    extractor,
    monkeypatch,
):
    monkeypatch.setattr(
        pdf_parser_service.pdfplumber,
        'open',
        lambda _path: _OversizedPDF(),
    )

    with pytest.raises(ValueError, match=f'maximum of {MAX_PDF_PAGES} pages'):
        extractor('/private/oversized.pdf')


@pytest.mark.parametrize(
    'rows,expected_error',
    [
        (
            [
                {
                    'Symbol': 'AAPL',
                    'Quantity': 2,
                    'Average Price': 100,
                },
                {
                    'Symbol': 'MSFT',
                    'Quantity': -1,
                    'Average Price': 200,
                },
            ],
            'Row 3',
        ),
        (
            [
                {
                    'Symbol': 'aapl',
                    'Quantity': 2,
                    'Average Price': 100,
                },
                {
                    'Symbol': 'AAPL',
                    'Quantity': 1,
                    'Average Price': 110,
                },
            ],
            'Duplicate Symbol AAPL',
        ),
    ],
)
def test_us_workbook_validation_is_all_or_nothing(
    rows,
    expected_error,
    monkeypatch,
):
    monkeypatch.setattr(
        'app.services.us_holdings_service.pd.read_excel',
        lambda *_args, **_kwargs: pd.DataFrame(rows),
    )

    with pytest.raises(ValueError, match=expected_error):
        USHoldingsService().parse_excel_file('/private/positions.xlsx')


@pytest.mark.parametrize(
    'rows,expected_error',
    [
        (
            [
                {
                    'Bank Name': 'First Bank',
                    'Investment Amount': 100000,
                    'Investment Date': '2026-01-01',
                    'Interest Rate': 7,
                    'Deposit ID': 'FD-1',
                },
                {
                    'Bank Name': 'Second Bank',
                    'Investment Amount': -1,
                    'Investment Date': '2026-01-01',
                    'Interest Rate': 7,
                    'Deposit ID': 'FD-2',
                },
            ],
            'Row 3',
        ),
        (
            [
                {
                    'Bank Name': 'First Bank',
                    'Investment Amount': 100000,
                    'Investment Date': '2026-01-01',
                    'Interest Rate': 7,
                    'Deposit ID': 'FD-1',
                },
                {
                    'Bank Name': 'Second Bank',
                    'Investment Amount': 200000,
                    'Investment Date': '2026-02-01',
                    'Interest Rate': 8,
                    'Deposit ID': 'FD-1',
                },
            ],
            'Duplicate Deposit ID FD-1',
        ),
    ],
)
def test_fd_workbook_validation_is_all_or_nothing(
    rows,
    expected_error,
    monkeypatch,
):
    monkeypatch.setattr(
        'app.services.fd_service.pd.read_excel',
        lambda *_args, **_kwargs: pd.DataFrame(rows),
    )

    with pytest.raises(ValueError, match=expected_error):
        FDService().parse_excel_file('/private/deposits.xlsx')


def test_database_rate_limits_are_shared_by_separate_app_instances(tmp_path):
    database_path = tmp_path / 'shared-rate-limits.db'
    configuration = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{database_path}',
        'JWT_SECRET_KEY': 'shared-jwt-secret-key-at-least-32-bytes',
        'SECRET_KEY': 'shared-secret-key-at-least-32-bytes',
        'ENCRYPTION_KEY': Fernet.generate_key().decode(),
        'SCHEDULER_ENABLED': False,
        'RATELIMIT_STORAGE': 'database',
        'RATELIMIT_ENABLED': True,
    }
    first_app = create_app(configuration)
    second_app = create_app(configuration)
    with first_app.app_context():
        db.create_all()

    payload = {
        'email': 'missing@example.com',
        'password': 'incorrect-password',
    }
    first_client = first_app.test_client()
    second_client = second_app.test_client()
    try:
        for _ in range(3):
            assert first_client.post(
                '/api/auth/register',
                json=payload,
            ).status_code in {201, 400}
        for _ in range(2):
            assert second_client.post(
                '/api/auth/register',
                json=payload,
            ).status_code == 400

        limited = second_client.post('/api/auth/register', json=payload)
        assert limited.status_code == 429
        assert int(limited.headers['Retry-After']) > 0
        with first_app.app_context():
            bucket = RateLimitBucket.query.one()
            assert bucket.count == 6
    finally:
        with second_app.app_context():
            db.session.remove()
        with first_app.app_context():
            db.session.remove()
            db.drop_all()


def test_portfolio_history_carries_baseline_to_both_requested_boundaries(
    app,
    sample_user,
):
    start = datetime(2026, 5, 1)
    end = datetime(2026, 5, 31)
    with app.app_context():
        account = Account(
            user_id=sample_user['id'],
            account_name='Boundary account',
            api_key_encrypted='key',
            api_secret_encrypted='secret',
            is_active=True,
        )
        db.session.add(account)
        db.session.flush()
        db.session.add(
            PortfolioTimeseries(
                account_id=account.id,
                date=start - timedelta(days=1),
                total_value=Decimal('1250.00'),
                invested_value=Decimal('1000.00'),
                pnl=Decimal('250.00'),
                pnl_percentage=Decimal('25.00'),
                day_change=Decimal('10.00'),
                holdings_count=3,
                currency='INR',
            )
        )
        db.session.commit()

        history = AnalyticsService.get_portfolio_history(
            user_id=sample_user['id'],
            account_id=account.id,
            start_date=start,
            end_date=end,
            currency='INR',
        )

        assert [point['date'] for point in history] == [
            start.isoformat(),
            end.isoformat(),
        ]
        assert [point['total_value'] for point in history] == [1250.0, 1250.0]
        assert [point['day_change'] for point in history] == [0.0, 0.0]

        labels = AnalyticsService.calculate_returns(history)
        assert set(labels) == {
            'value_growth_percentage',
            'annualized_value_growth_percentage',
            'latest_day_change',
            'cash_flow_adjusted',
        }
        assert labels['value_growth_percentage'] == 0
        assert labels['cash_flow_adjusted'] is False


@pytest.mark.parametrize(
    'quotes',
    [
        {
            'AAPL': {'error': 'Quote unavailable'},
            'MSFT': {'error': 'Quote unavailable'},
        },
        {
            'AAPL': {
                'current_price': 150,
                'change': 1,
                'change_percent': 0.5,
            },
            'MSFT': {'error': 'Quote unavailable'},
        },
    ],
    ids=['all-quotes-fail', 'one-quote-fails'],
)
def test_us_refresh_quote_failures_publish_no_snapshot(
    app,
    sample_user,
    quotes,
):
    class StubPriceService:
        def get_quotes_batch(self, _symbols):
            return quotes

    with app.app_context():
        account = Account(
            user_id=sample_user['id'],
            account_name='US refresh account',
            api_key_encrypted='key',
            api_secret_encrypted='secret',
            is_active=True,
        )
        db.session.add(account)
        db.session.flush()
        baseline = Snapshot(
            account_id=account.id,
            snapshot_date=datetime(2026, 6, 1),
            status='completed',
            trigger='test',
            total_holdings=2,
            total_investment=Decimal('200.00'),
            current_value=Decimal('220.00'),
            total_pnl=Decimal('20.00'),
            total_pnl_percentage=Decimal('10.00'),
            currency='USD',
        )
        db.session.add(baseline)
        db.session.flush()
        for symbol in ('AAPL', 'MSFT'):
            db.session.add(
                Holding(
                    account_id=account.id,
                    snapshot_id=baseline.id,
                    holding_key=f'us_equity:US:{symbol}',
                    tradingsymbol=symbol,
                    instrument_type='us_equity',
                    market='US',
                    exchange='US',
                    currency='USD',
                    quantity=Decimal('1'),
                    average_price=Decimal('100'),
                    last_price=Decimal('110'),
                    current_value=Decimal('110'),
                    pnl=Decimal('10'),
                    pnl_percentage=Decimal('10'),
                    day_change=Decimal('1'),
                    day_change_percentage=Decimal('1'),
                    sector='Technology',
                    source='test',
                )
            )
        db.session.commit()
        baseline_id = baseline.id

        service = USHoldingsService(price_service=StubPriceService())
        with pytest.raises(RuntimeError, match='Live prices are unavailable'):
            service.refresh_prices(account)
        db.session.rollback()

        snapshots = Snapshot.query.filter_by(account_id=account.id).all()
        assert [snapshot.id for snapshot in snapshots] == [baseline_id]
        assert snapshots[0].status == 'completed'
        assert len(snapshots[0].holdings) == 2


def test_top_merchants_respects_requested_period(
    app,
    client,
    auth_headers,
    sample_bank_account,
):
    with app.app_context():
        db.session.add_all(
            [
                Transaction(
                    bank_account_id=sample_bank_account['id'],
                    transaction_date=date.today() - timedelta(days=5),
                    description='AMAZON RECENT',
                    amount=Decimal('25.00'),
                    transaction_type='debit',
                    verified=True,
                ),
                Transaction(
                    bank_account_id=sample_bank_account['id'],
                    transaction_date=date.today() - timedelta(days=60),
                    description='SWIGGY OLD',
                    amount=Decimal('1000.00'),
                    transaction_type='debit',
                    verified=True,
                ),
            ]
        )
        db.session.commit()

    recent = client.get(
        (
            f'/api/bank-accounts/{sample_bank_account["id"]}'
            '/analytics/top-merchants?limit=10&period_days=30'
        ),
        headers=auth_headers,
    )
    assert recent.status_code == 200
    assert recent.get_json()['period_days'] == 30
    assert [merchant['merchant'] for merchant in recent.get_json()['merchants']] == [
        'Amazon'
    ]

    expanded = client.get(
        (
            f'/api/bank-accounts/{sample_bank_account["id"]}'
            '/analytics/top-merchants?limit=10&period_days=90'
        ),
        headers=auth_headers,
    )
    assert expanded.status_code == 200
    assert expanded.get_json()['period_days'] == 90
    assert [
        merchant['merchant']
        for merchant in expanded.get_json()['merchants']
    ] == ['Swiggy', 'Amazon']


def test_snapshot_emits_zero_event_when_last_holding_in_currency_disappears(
    app,
    sample_user,
):
    first_date = datetime(2026, 6, 1)
    removal_date = datetime(2026, 6, 2)
    history_end = datetime(2026, 6, 3)
    with app.app_context():
        account = Account(
            user_id=sample_user['id'],
            account_name='Currency removal',
            api_key_encrypted='key',
            api_secret_encrypted='secret',
            is_active=True,
        )
        db.session.add(account)
        db.session.flush()
        initial = Snapshot(
            account_id=account.id,
            snapshot_date=first_date,
            status='running',
            trigger='test',
        )
        db.session.add(initial)
        db.session.flush()
        db.session.add_all(
            [
                Holding(
                    account_id=account.id,
                    snapshot_id=initial.id,
                    holding_key='equity:INR:INFY',
                    tradingsymbol='INFY',
                    instrument_type='equity',
                    market='IN',
                    exchange='NSE',
                    currency='INR',
                    quantity=Decimal('1'),
                    average_price=Decimal('100'),
                    last_price=Decimal('120'),
                    current_value=Decimal('120'),
                    pnl=Decimal('20'),
                    pnl_percentage=Decimal('20'),
                    day_change=Decimal('1'),
                    day_change_percentage=Decimal('1'),
                    sector='Technology',
                    source='test',
                ),
                Holding(
                    account_id=account.id,
                    snapshot_id=initial.id,
                    holding_key='us_equity:US:AAPL',
                    tradingsymbol='AAPL',
                    instrument_type='us_equity',
                    market='US',
                    exchange='US',
                    currency='USD',
                    quantity=Decimal('1'),
                    average_price=Decimal('100'),
                    last_price=Decimal('125'),
                    current_value=Decimal('125'),
                    pnl=Decimal('25'),
                    pnl_percentage=Decimal('25'),
                    day_change=Decimal('2'),
                    day_change_percentage=Decimal('2'),
                    sector='Technology',
                    source='test',
                ),
            ]
        )
        PortfolioService.finalize_snapshot(initial)
        db.session.commit()

        removed = PortfolioService.create_account_snapshot(
            account,
            trigger='us_upload',
            snapshot_date=removal_date,
            exclude_types=('us_equity',),
        )
        PortfolioService.finalize_snapshot(removed)
        db.session.commit()

        removal_rows = PortfolioTimeseries.query.filter_by(
            account_id=account.id,
            snapshot_id=removed.id,
        ).order_by(PortfolioTimeseries.currency).all()
        assert [
            (
                row.currency,
                row.total_value,
                row.invested_value,
                row.holdings_count,
            )
            for row in removal_rows
        ] == [
            ('INR', Decimal('120.00'), Decimal('100.00'), 1),
            ('USD', Decimal('0.00'), Decimal('0.00'), 0),
        ]

        usd_history = AnalyticsService.get_portfolio_history(
            user_id=sample_user['id'],
            account_id=account.id,
            start_date=first_date,
            end_date=history_end,
            currency='USD',
        )
        assert [
            (point['date'], point['total_value'], point['holdings_count'])
            for point in usd_history
        ] == [
            (first_date.isoformat(), 125.0, 1),
            (removal_date.isoformat(), 0.0, 0),
            (history_end.isoformat(), 0.0, 0),
        ]


def test_uncategorized_verified_debits_are_included_in_spending(
    app,
    sample_user,
    sample_bank_account,
):
    with app.app_context():
        db.session.add_all(
            [
                Transaction(
                    bank_account_id=sample_bank_account['id'],
                    transaction_date=date.today(),
                    description='No category debit',
                    amount=Decimal('40.00'),
                    transaction_type='debit',
                    category_id=None,
                    verified=True,
                ),
                Transaction(
                    bank_account_id=sample_bank_account['id'],
                    transaction_date=date.today(),
                    description='Unverified debit',
                    amount=Decimal('500.00'),
                    transaction_type='debit',
                    category_id=None,
                    verified=False,
                ),
            ]
        )
        db.session.commit()

        result = BankAnalyticsService.get_category_breakdown(
            sample_bank_account['id'],
            30,
            sample_user['id'],
        )

        assert result['total_spending'] == 40.0
        assert {
            item['name']: (item['total'], item['transaction_count'])
            for item in result['categories']
        } == {
            'Uncategorized': (40.0, 1),
        }


@pytest.mark.parametrize(
    'value',
    ['10000000000000.00', '-10000000000000.00', '1.001'],
)
def test_bank_account_balance_rejects_values_outside_numeric_15_2(
    client,
    auth_headers,
    value,
):
    response = client.post(
        '/api/bank-accounts',
        json={
            'bank_name': 'Boundary Bank',
            'account_number': '12345678',
            'current_balance': value,
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert '13 integer and 2 decimal places' in response.get_json()['error']


@pytest.mark.parametrize(
    'field,value',
    [
        ('amount', '10000000000000.00'),
        ('amount', '1.001'),
        ('running_balance', '-10000000000000.00'),
        ('running_balance', '1.001'),
    ],
)
def test_statement_approval_rejects_values_outside_numeric_15_2(
    app,
    field,
    value,
):
    with app.app_context():
        with pytest.raises(ValueError, match='database precision'):
            BankStatementService._normalize_approval_transactions(
                [_review_transaction(**{field: value})]
            )


@pytest.mark.parametrize(
    'service_path,rows',
    [
        (
            'us',
            [
                {
                    'Symbol': 'AAPL',
                    'Quantity': Decimal('10000000000000'),
                    'Average Price': Decimal('2'),
                }
            ],
        ),
        (
            'fd',
            [
                {
                    'Bank Name': 'Overflow Bank',
                    'Investment Amount': Decimal('10000000000000'),
                    'Investment Date': '2026-01-01',
                    'Interest Rate': Decimal('7'),
                }
            ],
        ),
    ],
)
def test_spreadsheet_imports_reject_values_that_overflow_numeric_15_2(
    service_path,
    rows,
    monkeypatch,
):
    module = (
        'app.services.us_holdings_service.pd.read_excel'
        if service_path == 'us'
        else 'app.services.fd_service.pd.read_excel'
    )
    monkeypatch.setattr(
        module,
        lambda *_args, **_kwargs: pd.DataFrame(rows),
    )
    service = USHoldingsService() if service_path == 'us' else FDService()

    with pytest.raises(ValueError, match='database precision'):
        service.parse_excel_file('/private/import.xlsx')
