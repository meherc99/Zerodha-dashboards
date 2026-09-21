"""Zerodha account + holdings synchronization workflow.

The broker client is mocked so the sync path (route -> scheduler -> service ->
snapshot -> holdings) is exercised end-to-end without a live Kite session, then
the holdings and aggregation endpoints are asserted to reflect the synced data.
"""
import json
from decimal import Decimal


def _normalized_holding(symbol="INFY", key="equity:NSE:INE009A01021"):
    return {
        "holding_key": key,
        "tradingsymbol": symbol,
        "instrument_type": "equity",
        "market": "IN",
        "exchange": "NSE",
        "isin": "INE009A01021",
        "folio": None,
        "currency": "INR",
        "quantity": Decimal("2"),
        "average_price": Decimal("100"),
        "last_price": Decimal("125"),
        "last_price_date": None,
        "pnl": Decimal("50"),
        "pnl_percentage": Decimal("25"),
        "day_change": Decimal("3"),
        "day_change_percentage": Decimal("2.4"),
        "current_value": Decimal("250"),
        "source": "kite_equity",
    }


class _FakeKiteService:
    """Stand-in for KiteService used inside the scheduler during sync."""

    holdings_payload = [_normalized_holding()]

    def __init__(self, api_key=None, api_secret=None, access_token=None):
        self.access_token = access_token

    def get_holdings(self):
        return list(self.holdings_payload)


def _patch_kite(monkeypatch, payload=None):
    from app.services import scheduler_service

    if payload is not None:
        _FakeKiteService.holdings_payload = payload
    else:
        _FakeKiteService.holdings_payload = [_normalized_holding()]
    monkeypatch.setattr(scheduler_service, "KiteService", _FakeKiteService)


def test_holdings_empty_before_sync(client, auth_headers, sample_user, make_kite_account):
    make_kite_account(sample_user["id"])
    response = client.get("/api/holdings", headers=auth_headers)
    assert response.status_code == 200
    assert json.loads(response.data)["holdings"] == []


def test_sync_populates_holdings(client, auth_headers, sample_user, make_kite_account, monkeypatch):
    account_id = make_kite_account(sample_user["id"])
    _patch_kite(monkeypatch)

    sync = client.post(
        "/api/holdings/sync",
        data=json.dumps({"account_id": account_id}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert sync.status_code == 200
    result = json.loads(sync.data)
    assert result["accounts_succeeded"] == 1
    assert result["status"] == "completed"

    holdings = client.get("/api/holdings", headers=auth_headers)
    assert holdings.status_code == 200
    body = json.loads(holdings.data)
    assert len(body["holdings"]) == 1
    assert body["holdings"][0]["tradingsymbol"] == "INFY"
    assert body["summary"]["total_holdings"] == 1
    assert body["summary"]["by_currency"]["INR"]["current_value"] == 250.0


def test_aggregated_endpoint_after_sync(client, auth_headers, sample_user, make_kite_account, monkeypatch):
    account_id = make_kite_account(sample_user["id"])
    _patch_kite(monkeypatch)
    client.post(
        "/api/holdings/sync",
        data=json.dumps({"account_id": account_id}),
        content_type="application/json",
        headers=auth_headers,
    )

    response = client.get("/api/holdings/aggregated", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(json.loads(response.data), dict)


def test_sync_requires_authentication(client):
    response = client.post(
        "/api/holdings/sync",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert response.status_code == 401


def test_user_cannot_sync_another_users_account(
    client, other_auth_headers, sample_user, make_kite_account, monkeypatch
):
    account_id = make_kite_account(sample_user["id"])
    _patch_kite(monkeypatch)

    response = client.post(
        "/api/holdings/sync",
        data=json.dumps({"account_id": account_id}),
        content_type="application/json",
        headers=other_auth_headers,
    )
    assert response.status_code == 404


def test_user_cannot_read_another_users_holdings(
    client, auth_headers, other_auth_headers, sample_user, make_kite_account, monkeypatch
):
    account_id = make_kite_account(sample_user["id"])
    _patch_kite(monkeypatch)
    client.post(
        "/api/holdings/sync",
        data=json.dumps({"account_id": account_id}),
        content_type="application/json",
        headers=auth_headers,
    )

    # Filtering by another user's account id must not leak the holdings.
    leaked = client.get(
        f"/api/holdings?account_id={account_id}", headers=other_auth_headers
    )
    assert leaked.status_code == 404

    own = client.get("/api/holdings", headers=other_auth_headers)
    assert own.status_code == 200
    assert json.loads(own.data)["holdings"] == []
