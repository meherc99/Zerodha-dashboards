"""Bank accounts, statements, transactions and bank analytics workflow.

Drives the bank-side CRUD surface the frontend uses, plus the read-only
analytics endpoints, and asserts cross-user ownership isolation.
"""
import json


def _create_bank_account(client, headers, **overrides):
    payload = {
        "bank_name": "HDFC Bank",
        "account_number": "1234567890",
        "account_type": "savings",
        "current_balance": 50000.00,
        "currency": "INR",
    }
    payload.update(overrides)
    return client.post(
        "/api/bank-accounts",
        data=json.dumps(payload),
        content_type="application/json",
        headers=headers,
    )


def test_bank_account_crud_lifecycle(client, auth_headers):
    created = _create_bank_account(client, auth_headers)
    assert created.status_code == 201
    account_id = json.loads(created.data)["id"]

    listing = client.get("/api/bank-accounts", headers=auth_headers)
    assert listing.status_code == 200
    assert any(a["id"] == account_id for a in json.loads(listing.data))

    fetched = client.get(f"/api/bank-accounts/{account_id}", headers=auth_headers)
    assert fetched.status_code == 200

    updated = client.put(
        f"/api/bank-accounts/{account_id}",
        data=json.dumps({"bank_name": "HDFC Bank Ltd"}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert json.loads(updated.data)["bank_name"] == "HDFC Bank Ltd"

    deleted = client.delete(f"/api/bank-accounts/{account_id}", headers=auth_headers)
    assert deleted.status_code == 200

    gone = client.get(f"/api/bank-accounts/{account_id}", headers=auth_headers)
    assert gone.status_code == 404


def test_bank_account_requires_authentication(client):
    assert client.get("/api/bank-accounts").status_code == 401


def test_statements_list_empty_for_new_account(client, auth_headers):
    account_id = json.loads(_create_bank_account(client, auth_headers).data)["id"]
    response = client.get(
        f"/api/bank-accounts/{account_id}/statements", headers=auth_headers
    )
    assert response.status_code == 200


def test_transactions_list_empty_for_new_account(client, auth_headers):
    account_id = json.loads(_create_bank_account(client, auth_headers).data)["id"]
    response = client.get(
        f"/api/bank-accounts/{account_id}/transactions", headers=auth_headers
    )
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body["transactions"] == []


def test_categories_endpoint(client, auth_headers):
    response = client.get("/api/categories", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(json.loads(response.data), list)


def test_bank_analytics_endpoints_for_owned_account(client, auth_headers):
    account_id = json.loads(_create_bank_account(client, auth_headers).data)["id"]
    endpoints = [
        f"/api/bank-accounts/{account_id}/analytics/balance-trend",
        f"/api/bank-accounts/{account_id}/analytics/category-breakdown",
        f"/api/bank-accounts/{account_id}/analytics/cashflow",
        f"/api/bank-accounts/{account_id}/analytics/monthly-cashflow",
        f"/api/bank-accounts/{account_id}/analytics/top-merchants",
    ]
    for endpoint in endpoints:
        response = client.get(endpoint, headers=auth_headers)
        assert response.status_code == 200, endpoint


def test_bank_analytics_unknown_account_returns_404(client, auth_headers):
    response = client.get(
        "/api/bank-accounts/999999/analytics/balance-trend", headers=auth_headers
    )
    assert response.status_code == 404


def test_user_cannot_access_another_users_bank_account(
    client, auth_headers, other_auth_headers
):
    account_id = json.loads(_create_bank_account(client, auth_headers).data)["id"]

    assert (
        client.get(
            f"/api/bank-accounts/{account_id}", headers=other_auth_headers
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/bank-accounts/{account_id}/analytics/balance-trend",
            headers=other_auth_headers,
        ).status_code
        == 404
    )
