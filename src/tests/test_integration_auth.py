"""End-to-end authentication workflow through the real HTTP stack.

Covers the register -> login -> access-protected -> logout -> revoked journey
exactly as the frontend auth store drives it.
"""
import json


def _post(client, path, payload, headers=None):
    return client.post(
        path,
        data=json.dumps(payload),
        content_type="application/json",
        headers=headers or {},
    )


def test_register_returns_token_and_profile(client):
    response = _post(
        client,
        "/api/auth/register",
        {"email": "new@example.com", "password": "supersecret", "full_name": "New User"},
    )

    assert response.status_code == 201
    body = json.loads(response.data)
    assert body["access_token"]
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["full_name"] == "New User"
    assert "password" not in json.dumps(body)


def test_register_rejects_duplicate_email(client, sample_user):
    response = _post(
        client,
        "/api/auth/register",
        {"email": sample_user["email"], "password": "anotherpass"},
    )

    assert response.status_code == 400
    assert "error" in json.loads(response.data)


def test_login_and_access_protected_route(client, sample_user):
    login = _post(
        client,
        "/api/auth/login",
        {"email": sample_user["email"], "password": sample_user["password"]},
    )
    assert login.status_code == 200
    token = json.loads(login.data)["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert json.loads(me.data)["email"] == sample_user["email"]


def test_login_rejects_bad_password(client, sample_user):
    response = _post(
        client,
        "/api/auth/login",
        {"email": sample_user["email"], "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_protected_route_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_logout_revokes_token(client, sample_user):
    login = _post(
        client,
        "/api/auth/login",
        {"email": sample_user["email"], "password": sample_user["password"]},
    )
    token = json.loads(login.data)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/auth/me", headers=headers).status_code == 200

    logout = client.post("/api/auth/logout", headers=headers)
    assert logout.status_code == 200

    # The same token must no longer be accepted after logout.
    assert client.get("/api/auth/me", headers=headers).status_code == 401
