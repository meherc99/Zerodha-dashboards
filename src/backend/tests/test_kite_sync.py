"""Kite normalization and atomic multi-account synchronization tests."""

from datetime import date, datetime
from decimal import Decimal

from app.database import db
from app.models import Account, Holding, Snapshot
from app.services.kite_service import KiteService
from app.services.scheduler_service import SchedulerService
from app.utils.encryption import get_encryptor


class FakeKiteClient:
    def holdings(self):
        return [
            {
                "tradingsymbol": "INFY",
                "exchange": "NSE",
                "isin": "INE009A01021",
                "quantity": 2,
                "average_price": 100,
                "last_price": 125,
                "day_change": 3,
            }
        ]

    def mf_holdings(self):
        return [
            {
                "tradingsymbol": "INDEX FUND",
                "isin": "INF000000001",
                "folio": "FOLIO-1",
                "quantity": "1.234567",
                "average_price": "100.50",
                "last_price": "110.25",
                "last_price_date": "2026-07-28",
            },
            {
                "tradingsymbol": "INDEX FUND",
                "isin": "INF000000001",
                "folio": "FOLIO-2",
                "quantity": "0.765433",
                "average_price": "101.50",
                "last_price": "110.25",
            },
        ]


def test_kite_fetches_equities_and_mutual_funds_from_distinct_apis():
    service = object.__new__(KiteService)
    service.access_token = "access-token"
    service.kite = FakeKiteClient()

    holdings = service.get_holdings()
    equity = holdings[0]
    funds = holdings[1:]

    assert equity["holding_key"] == "equity:NSE:INE009A01021"
    assert equity["instrument_type"] == "equity"
    assert equity["current_value"] == Decimal("250")
    assert equity["source"] == "kite_equity"

    assert [fund["quantity"] for fund in funds] == [
        Decimal("1.234567"),
        Decimal("0.765433"),
    ]
    assert funds[0]["last_price_date"] == date(2026, 7, 28)
    assert funds[0]["holding_key"] != funds[1]["holding_key"]
    assert {fund["folio"] for fund in funds} == {"FOLIO-1", "FOLIO-2"}
    assert all(fund["instrument_type"] == "mf" for fund in funds)
    assert all(fund["source"] == "kite_mf" for fund in funds)


def _create_encrypted_account(user_id, name, api_key):
    encryptor = get_encryptor()
    account = Account(
        user_id=user_id,
        account_name=name,
        api_key_encrypted=encryptor.encrypt(api_key),
        api_secret_encrypted=encryptor.encrypt("secret"),
        access_token_encrypted=encryptor.encrypt("access-token"),
        is_active=True,
    )
    db.session.add(account)
    db.session.flush()
    return account


def _normalized_holding(symbol, holding_key, instrument_type="equity"):
    return {
        "holding_key": holding_key,
        "tradingsymbol": symbol,
        "instrument_type": instrument_type,
        "market": "IN",
        "exchange": "MF" if instrument_type == "mf" else "NSE",
        "currency": "INR",
        "quantity": Decimal("1.5"),
        "average_price": Decimal("100"),
        "last_price": Decimal("120"),
        "pnl": Decimal("30"),
        "pnl_percentage": Decimal("20"),
        "day_change": Decimal("2"),
        "day_change_percentage": Decimal("1.5"),
        "current_value": Decimal("180"),
        "source": "test",
    }


def test_multi_account_sync_uses_savepoints_and_never_keeps_partial_holdings(
    app,
    sample_user,
    monkeypatch,
):
    class FakeKiteService:
        def __init__(self, api_key, api_secret, access_token):
            self.api_key = api_key

        def get_holdings(self):
            if self.api_key == "bad":
                duplicate = _normalized_holding("DUPLICATE", "duplicate-key")
                return [duplicate, duplicate.copy()]
            return [
                _normalized_holding("INFY", "equity:NSE:INFY"),
                _normalized_holding(
                    "INDEX FUND",
                    "mf:FOLIO-1:INDEX",
                    instrument_type="mf",
                ),
            ]

    monkeypatch.setattr(
        "app.services.scheduler_service.KiteService",
        FakeKiteService,
    )

    with app.app_context():
        good = _create_encrypted_account(sample_user["id"], "Good", "good")
        bad = _create_encrypted_account(sample_user["id"], "Bad", "bad")
        good_id = good.id
        bad_id = bad.id
        db.session.commit()

        result = SchedulerService(app).sync_user_accounts(sample_user["id"])

        assert result["status"] == "partial"
        assert result["accounts_succeeded"] == 1
        assert result["accounts_failed"] == 1

        snapshots = Snapshot.query.order_by(Snapshot.account_id).all()
        assert len(snapshots) == 2
        assert len({snapshot.batch_id for snapshot in snapshots}) == 1
        assert len({snapshot.snapshot_date for snapshot in snapshots}) == 1

        good_snapshot = Snapshot.query.filter_by(account_id=good_id).one()
        bad_snapshot = Snapshot.query.filter_by(account_id=bad_id).one()
        assert good_snapshot.status == "completed"
        assert bad_snapshot.status == "failed"
        assert good_snapshot.total_holdings == 2
        assert len(good_snapshot.holdings) == 2
        assert bad_snapshot.holdings == []
        assert bad_snapshot.error_message == "Portfolio refresh failed"


def test_kite_sync_replaces_kite_assets_but_carries_fixed_deposits_forward(
    app,
    sample_user,
    monkeypatch,
):
    class FakeKiteService:
        def __init__(self, api_key, api_secret, access_token):
            pass

        def get_holdings(self):
            return [_normalized_holding("TCS", "equity:NSE:TCS")]

    monkeypatch.setattr(
        "app.services.scheduler_service.KiteService",
        FakeKiteService,
    )

    with app.app_context():
        account = _create_encrypted_account(sample_user["id"], "Family", "good")
        previous = Snapshot(
            account_id=account.id,
            snapshot_date=datetime(2026, 1, 1),
            status="completed",
            trigger="fd_upload",
        )
        db.session.add(previous)
        db.session.flush()
        db.session.add(
            Holding(
                account_id=account.id,
                snapshot_id=previous.id,
                holding_key="fd:deposit-1",
                tradingsymbol="Example Bank FD",
                instrument_type="fd",
                market="IN",
                exchange="FD",
                currency="INR",
                quantity=Decimal("1"),
                average_price=Decimal("100000"),
                last_price=Decimal("103000"),
                current_value=Decimal("103000"),
                pnl=Decimal("3000"),
                pnl_percentage=Decimal("3"),
                day_change=Decimal("0"),
                day_change_percentage=Decimal("0"),
                purchase_date=date(2026, 1, 1),
                maturity_date=date(2027, 1, 1),
                interest_rate=Decimal("7"),
                sector="Fixed Deposit",
                source="upload_fd",
            )
        )
        db.session.commit()

        result = SchedulerService(app).sync_user_accounts(sample_user["id"])

        assert result["status"] == "completed"
        latest = (
            Snapshot.query.filter_by(account_id=account.id, status="completed")
            .order_by(Snapshot.snapshot_date.desc())
            .first()
        )
        assert {holding.instrument_type for holding in latest.holdings} == {
            "equity",
            "fd",
        }
        assert previous.holdings[0].tradingsymbol == "Example Bank FD"
