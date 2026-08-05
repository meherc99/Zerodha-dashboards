"""Currency and account-snapshot invariants for portfolio calculations."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
import threading
from types import SimpleNamespace

from cryptography.fernet import Fernet
import pytest

from app import create_app
from app.database import db
from app.models import Account, Holding, PortfolioTimeseries, Snapshot, User
from app.services.portfolio_service import PortfolioService


def summary_holding(**overrides):
    values = {
        "currency": "INR",
        "quantity": Decimal("2"),
        "average_price": Decimal("100"),
        "last_price": Decimal("120"),
        "current_value": Decimal("240"),
        "pnl": Decimal("40"),
        "day_change": Decimal("5"),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def create_account(user_id, name, *, active=True):
    account = Account(
        user_id=user_id,
        account_name=name,
        api_key_encrypted=f"{name}-key",
        api_secret_encrypted=f"{name}-secret",
        is_active=active,
    )
    db.session.add(account)
    db.session.flush()
    return account


def create_snapshot(account, when, *, status="completed", trigger="test"):
    snapshot = Snapshot(
        account_id=account.id,
        snapshot_date=when,
        status=status,
        trigger=trigger,
    )
    db.session.add(snapshot)
    db.session.flush()
    return snapshot


def create_holding(
    account,
    snapshot,
    symbol,
    *,
    currency="INR",
    instrument_type="equity",
    quantity="1",
    average_price="100",
    last_price="120",
    current_value="120",
    day_change="1",
    sector="Other",
):
    invested = Decimal(quantity) * Decimal(average_price)
    current = Decimal(current_value)
    pnl = current - invested
    holding = Holding(
        account_id=account.id,
        snapshot_id=snapshot.id,
        holding_key=f"{instrument_type}:{currency}:{symbol}",
        tradingsymbol=symbol,
        instrument_type=instrument_type,
        market="US" if currency == "USD" else "IN",
        exchange="US" if currency == "USD" else "NSE",
        currency=currency,
        quantity=Decimal(quantity),
        average_price=Decimal(average_price),
        last_price=Decimal(last_price),
        current_value=current,
        pnl=pnl,
        pnl_percentage=pnl / invested * 100 if invested else 0,
        day_change=Decimal(day_change),
        day_change_percentage=0,
        sector=sector,
        source="test",
    )
    db.session.add(holding)
    return holding


def test_empty_portfolio_summary_is_explicit_and_currency_neutral():
    assert PortfolioService.calculate_portfolio_summary([]) == {
        "total_holdings": 0,
        "by_currency": {},
        "currency": None,
        "total_investment": 0,
        "current_value": 0,
        "total_pnl": 0,
        "total_pnl_percentage": 0,
        "day_change": 0,
    }


def test_homogeneous_summary_calculates_monetary_day_change():
    summary = PortfolioService.calculate_portfolio_summary(
        [
            summary_holding(),
            summary_holding(
                quantity=Decimal("3"),
                average_price=Decimal("50"),
                current_value=Decimal("180"),
                pnl=Decimal("30"),
                day_change=Decimal("-2"),
            ),
        ]
    )

    assert summary["currency"] == "INR"
    assert summary["total_holdings"] == 2
    assert summary["total_investment"] == 350
    assert summary["current_value"] == 420
    assert summary["total_pnl"] == 70
    assert summary["total_pnl_percentage"] == 20
    assert summary["day_change"] == 4
    assert summary["by_currency"]["INR"]["day_change"] == 4


def test_mixed_currency_summary_never_exposes_false_scalar_totals():
    summary = PortfolioService.calculate_portfolio_summary(
        [
            summary_holding(),
            summary_holding(
                currency="USD",
                quantity=Decimal("0.5"),
                average_price=Decimal("200"),
                last_price=Decimal("250"),
                current_value=Decimal("125"),
                pnl=Decimal("25"),
                day_change=Decimal("4"),
            ),
        ]
    )

    assert summary["currency"] == "MIXED"
    assert summary["total_holdings"] == 2
    assert summary["total_investment"] is None
    assert summary["current_value"] is None
    assert summary["total_pnl"] is None
    assert summary["total_pnl_percentage"] is None
    assert summary["day_change"] is None
    assert summary["by_currency"]["INR"] == {
        "currency": "INR",
        "total_holdings": 1,
        "total_investment": 200,
        "current_value": 240,
        "total_pnl": 40,
        "total_pnl_percentage": 20,
        "day_change": 10,
    }
    assert summary["by_currency"]["USD"] == {
        "currency": "USD",
        "total_holdings": 1,
        "total_investment": 100,
        "current_value": 125,
        "total_pnl": 25,
        "total_pnl_percentage": 25,
        "day_change": 2,
    }


def test_latest_holdings_selects_latest_completed_snapshot_per_owned_account(
    app,
    sample_user,
):
    with app.app_context():
        owner_id = sample_user["id"]
        other = User(email="portfolio-other@example.com", full_name="Other")
        other.set_password("password123")
        db.session.add(other)
        db.session.flush()

        first = create_account(owner_id, "First")
        second = create_account(owner_id, "Second")
        inactive = create_account(owner_id, "Inactive", active=False)
        foreign = create_account(other.id, "Foreign")

        first_old = create_snapshot(first, datetime(2025, 1, 1))
        create_holding(first, first_old, "FIRST_OLD")
        first_latest = create_snapshot(first, datetime(2025, 1, 2))
        create_holding(first, first_latest, "FIRST_LATEST")
        first_failed = create_snapshot(
            first,
            datetime(2025, 1, 3),
            status="failed",
        )
        create_holding(first, first_failed, "FIRST_FAILED")

        second_latest = create_snapshot(second, datetime(2025, 1, 4))
        create_holding(
            second,
            second_latest,
            "SECOND_LATEST",
            currency="USD",
            current_value="130",
        )

        inactive_latest = create_snapshot(inactive, datetime(2025, 1, 5))
        create_holding(inactive, inactive_latest, "INACTIVE_LATEST")
        foreign_latest = create_snapshot(foreign, datetime(2025, 1, 6))
        create_holding(foreign, foreign_latest, "FOREIGN_LATEST")
        db.session.commit()

        latest = PortfolioService.get_latest_holdings(owner_id)
        assert sorted(item.tradingsymbol for item in latest) == [
            "FIRST_LATEST",
            "SECOND_LATEST",
        ]

        selected = PortfolioService.get_latest_holdings(owner_id, [first.id])
        assert [item.tradingsymbol for item in selected] == ["FIRST_LATEST"]

        foreign_selection = PortfolioService.get_latest_holdings(
            owner_id,
            [foreign.id],
        )
        assert foreign_selection == []

        aggregate = PortfolioService.aggregate_accounts(owner_id)
        assert aggregate["currency"] == "MIXED"
        assert aggregate["current_value"] is None
        assert set(aggregate["by_currency"]) == {"INR", "USD"}
        assert sorted(
            item["tradingsymbol"] for item in aggregate["holdings"]
        ) == ["FIRST_LATEST", "SECOND_LATEST"]


def test_new_snapshot_carries_other_asset_types_without_mutating_history(
    app,
    sample_user,
):
    with app.app_context():
        account = create_account(sample_user["id"], "Carry Forward")
        previous = create_snapshot(account, datetime(2025, 2, 1))
        create_holding(account, previous, "EQUITY")
        create_holding(
            account,
            previous,
            "DEPOSIT",
            instrument_type="fd",
            quantity="1",
            average_price="1000",
            last_price="1050",
            current_value="1050",
            day_change="0",
            sector="Fixed Deposit",
        )
        db.session.commit()

        replacement = PortfolioService.create_account_snapshot(
            account,
            trigger="fd_upload",
            snapshot_date=datetime(2025, 2, 2),
            exclude_types=("fd",),
        )
        db.session.flush()

        assert replacement.status == "running"
        assert [item.tradingsymbol for item in replacement.holdings] == ["EQUITY"]
        assert sorted(item.tradingsymbol for item in previous.holdings) == [
            "DEPOSIT",
            "EQUITY",
        ]


def test_finalize_snapshot_persists_one_timeseries_per_currency(
    app,
    sample_user,
):
    with app.app_context():
        account = create_account(sample_user["id"], "Currencies")
        snapshot = PortfolioService.create_account_snapshot(
            account,
            trigger="test",
            snapshot_date=datetime(2025, 3, 1),
            copy_previous=False,
        )
        create_holding(
            account,
            snapshot,
            "IN_STOCK",
            currency="INR",
            current_value="120",
            sector="Technology",
        )
        create_holding(
            account,
            snapshot,
            "US_STOCK",
            currency="USD",
            quantity="0.5",
            average_price="200",
            last_price="250",
            current_value="125",
            day_change="4",
            sector="Technology",
        )

        summary = PortfolioService.finalize_snapshot(snapshot)
        db.session.commit()

        assert summary["currency"] == "MIXED"
        assert snapshot.status == "completed"
        assert snapshot.currency == "MIXED"
        assert snapshot.current_value is None
        rows = PortfolioTimeseries.query.filter_by(
            account_id=account.id,
            snapshot_id=snapshot.id,
        ).order_by(PortfolioTimeseries.currency).all()
        assert [row.currency for row in rows] == ["INR", "USD"]
        assert [float(row.total_value) for row in rows] == [120, 125]
        assert [float(row.day_change) for row in rows] == [1, 2]


def test_finalize_snapshot_rejects_same_currency_aggregate_overflow(
    app,
    sample_user,
):
    with app.app_context():
        account = create_account(
            sample_user['id'],
            'Aggregate precision',
        )
        db.session.commit()
        snapshot = create_snapshot(
            account,
            datetime(2026, 2, 1),
            status='running',
        )
        for symbol in ('FD-ONE', 'FD-TWO'):
            create_holding(
                account,
                snapshot,
                symbol,
                instrument_type='fd',
                average_price='6000000000000.00',
                last_price='6000000000000.00',
                current_value='6000000000000.00',
                day_change='0',
                sector='Fixed Deposit',
            )

        with pytest.raises(
            ValueError,
            match='Portfolio aggregate exceeds database precision',
        ):
            PortfolioService.finalize_snapshot(snapshot)
        db.session.rollback()

        assert Snapshot.query.filter_by(
            account_id=account.id,
            snapshot_date=datetime(2026, 2, 1),
        ).count() == 0


def test_concurrent_snapshot_writers_serialize_without_lost_assets(tmp_path):
    """Two asset-specific refreshes must both survive in the latest snapshot."""
    database_path = tmp_path / 'concurrent-snapshots.db'
    concurrent_app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{database_path}',
        'JWT_SECRET_KEY': 'test-jwt-secret-key-at-least-32-bytes',
        'SECRET_KEY': 'test-secret-key-at-least-32-bytes',
        'ENCRYPTION_KEY': Fernet.generate_key().decode(),
        'SCHEDULER_ENABLED': False,
    })

    with concurrent_app.app_context():
        db.create_all()
        user = User(
            email='snapshot-writers@example.com',
            password_hash='hash',
            full_name='Snapshot Writers',
        )
        db.session.add(user)
        db.session.flush()
        account = create_account(user.id, 'Concurrent portfolio')
        baseline = create_snapshot(account, datetime(2026, 1, 1))
        create_holding(
            account,
            baseline,
            'BASELINE-FD',
            instrument_type='fd',
            current_value='105',
        )
        db.session.commit()
        account_id = account.id

    start = threading.Barrier(2)

    def refresh_asset(instrument_type, symbol):
        with concurrent_app.app_context():
            account = db.session.get(Account, account_id)
            start.wait(timeout=5)
            snapshot = PortfolioService.create_account_snapshot(
                account,
                trigger=f'{instrument_type}_refresh',
                exclude_types=(instrument_type,),
            )
            create_holding(
                account,
                snapshot,
                symbol,
                instrument_type=instrument_type,
                current_value='120',
            )
            PortfolioService.finalize_snapshot(snapshot)
            db.session.commit()
            return snapshot.id

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(refresh_asset, 'equity', 'EQUITY'),
                executor.submit(refresh_asset, 'mf', 'MUTUAL-FUND'),
            ]
            created_ids = {future.result() for future in futures}

        with concurrent_app.app_context():
            account = db.session.get(Account, account_id)
            latest = (
                Snapshot.query.filter_by(
                    account_id=account_id,
                    status='completed',
                )
                .order_by(Snapshot.snapshot_date.desc(), Snapshot.id.desc())
                .first()
            )
            assert len(created_ids) == 2
            assert account.portfolio_version == 2
            assert {
                holding.tradingsymbol
                for holding in latest.holdings
            } == {'BASELINE-FD', 'EQUITY', 'MUTUAL-FUND'}
    finally:
        with concurrent_app.app_context():
            db.session.remove()
            db.drop_all()
