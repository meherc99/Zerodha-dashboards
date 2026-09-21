"""Authorization and information-boundary tests for portfolio APIs."""

from datetime import datetime
from decimal import Decimal
import io

from app.database import db
from app.models import Account, Holding, Snapshot, User
from app.utils.encryption import get_encryptor


PROTECTED_ENDPOINTS = (
    "/api/accounts",
    "/api/holdings",
    "/api/holdings/aggregated",
    "/api/analytics/sector-breakdown",
    "/api/analytics/performance-metrics",
    "/api/analytics/portfolio-value-history",
    "/api/analytics/heatmap",
    "/api/analytics/correlation-matrix?symbols=INFY,TCS",
)


def _account(user_id, name):
    account = Account(
        user_id=user_id,
        account_name=name,
        api_key_encrypted=f"encrypted-{name}-key",
        api_secret_encrypted=f"encrypted-{name}-secret",
        access_token_encrypted=f"encrypted-{name}-token",
        is_active=True,
    )
    db.session.add(account)
    db.session.flush()
    return account


def _snapshot_with_holding(account, symbol, currency="INR"):
    snapshot = Snapshot(
        account_id=account.id,
        snapshot_date=datetime.utcnow(),
        status="completed",
        trigger="test",
        total_holdings=1,
        total_investment=Decimal("100"),
        current_value=Decimal("120"),
        total_pnl=Decimal("20"),
        total_pnl_percentage=Decimal("20"),
        currency=currency,
    )
    db.session.add(snapshot)
    db.session.flush()
    holding = Holding(
        account_id=account.id,
        snapshot_id=snapshot.id,
        holding_key=f"test:{currency}:{symbol}",
        tradingsymbol=symbol,
        instrument_type="equity",
        market="US" if currency == "USD" else "IN",
        exchange="NASDAQ" if currency == "USD" else "NSE",
        currency=currency,
        quantity=Decimal("1"),
        average_price=Decimal("100"),
        last_price=Decimal("120"),
        current_value=Decimal("120"),
        pnl=Decimal("20"),
        pnl_percentage=Decimal("20"),
        day_change=Decimal("1"),
        day_change_percentage=Decimal("1"),
        sector="Technology",
        source="test",
    )
    db.session.add(holding)
    return snapshot, holding


def test_portfolio_endpoints_require_authentication(client):
    for endpoint in PROTECTED_ENDPOINTS:
        response = client.get(endpoint)
        assert response.status_code == 401, endpoint

    assert client.post("/api/holdings/sync", json={}).status_code == 401
    assert client.post("/api/holdings/us/refresh-prices", json={}).status_code == 401
    assert client.post("/api/holdings/fd/refresh-values", json={}).status_code == 401


def test_account_credentials_never_leave_the_api(
    app,
    client,
    auth_headers,
    sample_user,
):
    with app.app_context():
        account = _account(sample_user["id"], "Private")
        account_id = account.id
        db.session.commit()

    detail = client.get(f"/api/accounts/{account_id}", headers=auth_headers)
    assert detail.status_code == 200
    serialized = detail.get_json()
    assert set(serialized) == {
        "id",
        "account_name",
        "is_active",
        "last_synced_at",
        "created_at",
    }
    assert not any(
        "key" in field or "secret" in field or "token" in field for field in serialized
    )


def test_other_users_account_ids_are_indistinguishable_from_missing_accounts(
    app,
    client,
    auth_headers,
    other_user,
):
    with app.app_context():
        foreign = _account(other_user["id"], "Foreign")
        _snapshot_with_holding(foreign, "FOREIGN")
        foreign_id = foreign.id
        db.session.commit()

    reads = (
        f"/api/accounts/{foreign_id}",
        f"/api/holdings?account_id={foreign_id}",
        f"/api/analytics/sector-breakdown?account_id={foreign_id}",
        f"/api/analytics/performance-metrics?account_id={foreign_id}",
    )
    for endpoint in reads:
        response = client.get(endpoint, headers=auth_headers)
        assert response.status_code == 404, endpoint
        assert response.get_json()["error"] == "Account not found"

    sync = client.post(
        "/api/holdings/sync",
        json={"account_id": foreign_id},
        headers=auth_headers,
    )
    assert sync.status_code == 404

    upload = client.post(
        "/api/holdings/fd/upload",
        data={
            "account_id": str(foreign_id),
            "file": (io.BytesIO(b"PK\x03\x04"), "deposits.xlsx"),
        },
        headers=auth_headers,
        content_type="multipart/form-data",
    )
    assert upload.status_code == 404


def test_family_view_contains_only_owned_holdings(
    app,
    client,
    auth_headers,
    sample_user,
    other_user,
):
    with app.app_context():
        owned = _account(sample_user["id"], "Owned")
        foreign = _account(other_user["id"], "Foreign")
        _snapshot_with_holding(owned, "OWNED")
        _snapshot_with_holding(foreign, "FOREIGN")
        db.session.commit()

    response = client.get(
        "/api/holdings?sort_by=tradingsymbol&sort_order=asc",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.get_json()
    assert [item["tradingsymbol"] for item in response.get_json()["holdings"]] == [
        "OWNED"
    ]


def test_deactivated_users_are_rejected_after_token_issuance(
    app,
    client,
    auth_headers,
    sample_user,
):
    with app.app_context():
        user = db.session.get(User, sample_user["id"])
        user.is_active = False
        db.session.commit()

    response = client.get("/api/accounts", headers=auth_headers)
    assert response.status_code == 401
    assert response.get_json()["error"] == "User account is unavailable"


def test_portfolio_query_validation_fails_closed(client, auth_headers):
    cases = (
        "/api/holdings?account_id=not-an-id",
        "/api/holdings?instrument_type=crypto",
        "/api/holdings?sort_by=__dict__",
        "/api/holdings?sort_order=sideways",
        "/api/analytics/portfolio-value-history?start_date=nope",
        "/api/analytics/performance-metrics?period_days=0",
        "/api/analytics/correlation-matrix?symbols=ONLYONE",
    )
    for endpoint in cases:
        assert client.get(endpoint, headers=auth_headers).status_code == 400


def test_kite_request_token_is_exchanged_server_side_and_not_retained(
    app,
    client,
    auth_headers,
    monkeypatch,
):
    monkeypatch.setattr(
        'app.routes.accounts._generate_access_token',
        lambda api_key, api_secret, request_token: 'server-access-token',
    )

    response = client.post(
        '/api/accounts',
        json={
            'account_name': 'Server exchange',
            'api_key': 'kite-key-123',
            'api_secret': 'kite-secret-123',
            'request_token': 'one-time-request-token',
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert not any('token' in key for key in response.get_json())
    with app.app_context():
        account = db.session.get(Account, response.get_json()['id'])
        encryptor = get_encryptor()
        assert (
            encryptor.decrypt(account.access_token_encrypted)
            == 'server-access-token'
        )
        assert account.request_token_encrypted is None


def test_account_api_rejects_direct_brokerage_access_tokens(
    client,
    auth_headers,
):
    response = client.post(
        '/api/accounts',
        json={
            'account_name': 'Unsafe client token',
            'api_key': 'kite-key-123',
            'api_secret': 'kite-secret-123',
            'access_token': 'browser-supplied-token',
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.get_json()['error'] == 'Unsupported field: access_token'


def test_account_updates_validate_boolean_and_credential_refresh_contract(
    app,
    client,
    auth_headers,
    sample_user,
):
    with app.app_context():
        account = _account(sample_user['id'], 'Update validation')
        account_id = account.id
        db.session.commit()

    bad_boolean = client.put(
        f'/api/accounts/{account_id}',
        json={'is_active': 'false'},
        headers=auth_headers,
    )
    assert bad_boolean.status_code == 400
    assert bad_boolean.get_json()['error'] == 'is_active must be a boolean'

    missing_refresh = client.put(
        f'/api/accounts/{account_id}',
        json={'api_key': 'replacement-key'},
        headers=auth_headers,
    )
    assert missing_refresh.status_code == 400
    assert 'request_token is required' in missing_refresh.get_json()['error']


def test_owned_account_login_url_uses_server_side_api_key(
    app,
    client,
    auth_headers,
    other_auth_headers,
    sample_user,
    monkeypatch,
):
    with app.app_context():
        encryptor = get_encryptor()
        account = Account(
            user_id=sample_user['id'],
            account_name='Reconnect account',
            api_key_encrypted=encryptor.encrypt('stored-kite-api-key'),
            api_secret_encrypted=encryptor.encrypt('stored-kite-secret'),
            is_active=True,
        )
        db.session.add(account)
        db.session.commit()
        account_id = account.id

    seen = []
    monkeypatch.setattr(
        'app.routes.accounts._generate_login_url',
        lambda api_key: (
            seen.append(api_key)
            or 'https://kite.zerodha.com/connect/login?v=3'
        ),
    )

    unauthorized = client.get(f'/api/accounts/{account_id}/login-url')
    assert unauthorized.status_code == 401
    other_user = client.get(
        f'/api/accounts/{account_id}/login-url',
        headers=other_auth_headers,
    )
    assert other_user.status_code == 404

    response = client.get(
        f'/api/accounts/{account_id}/login-url',
        headers=auth_headers,
    )
    assert response.status_code == 200, response.get_json()
    assert response.get_json() == {
        'login_url': 'https://kite.zerodha.com/connect/login?v=3'
    }
    assert seen == ['stored-kite-api-key']
    assert 'stored-kite-api-key' not in response.get_data(as_text=True)
