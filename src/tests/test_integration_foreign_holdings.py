"""US / EU / Fixed-Deposit spreadsheet import and refresh workflow.

The spreadsheet parsing and price providers are mocked so the upload plumbing
(multipart handling, magic-byte validation, ownership checks, response shape)
is verified without depending on real broker exports or live price feeds. A
genuine, minimal ``.xlsx`` byte stream is generated so the server-side zip and
magic-byte validation runs for real.
"""
import io
import json

import pytest
from openpyxl import Workbook


def _valid_xlsx_bytes():
    """Return the bytes of a real (minimal) xlsx workbook."""
    workbook = Workbook()
    sheet = workbook.active
    sheet["A1"] = "symbol"
    sheet["A2"] = "AAPL"
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer.read()


def _upload(client, headers, url, account_id):
    data = {
        "account_id": str(account_id),
        "file": (io.BytesIO(_valid_xlsx_bytes()), "holdings.xlsx"),
    }
    return client.post(
        url, data=data, content_type="multipart/form-data", headers=headers
    )


@pytest.mark.parametrize(
    "url,service_path,parse_method,create_method",
    [
        (
            "/api/holdings/us/upload",
            "app.services.us_holdings_service.USHoldingsService",
            "parse_excel_file",
            "create_holdings",
        ),
        (
            "/api/holdings/eu/upload",
            "app.services.eu_holdings_service.EUHoldingsService",
            "parse_excel_file",
            "create_holdings",
        ),
        (
            "/api/holdings/fd/upload",
            "app.services.fd_service.FDService",
            "parse_excel_file",
            "create_fd_holdings",
        ),
    ],
)
def test_spreadsheet_upload_flow(
    client,
    auth_headers,
    sample_user,
    make_kite_account,
    monkeypatch,
    url,
    service_path,
    parse_method,
    create_method,
):
    account_id = make_kite_account(sample_user["id"])

    module_name, class_name = service_path.rsplit(".", 1)
    module = __import__(module_name, fromlist=[class_name])
    service_class = getattr(module, class_name)

    monkeypatch.setattr(service_class, parse_method, lambda self, path: [{"symbol": "AAPL"}])
    monkeypatch.setattr(service_class, create_method, lambda self, account, parsed, **kwargs: [])

    response = _upload(client, auth_headers, url, account_id)
    assert response.status_code == 201, response.data
    assert "count" in json.loads(response.data)


def test_upload_rejects_non_spreadsheet(client, auth_headers, sample_user, make_kite_account):
    account_id = make_kite_account(sample_user["id"])
    data = {
        "account_id": str(account_id),
        "file": (io.BytesIO(b"not really a spreadsheet"), "holdings.xlsx"),
    }
    response = client.post(
        "/api/holdings/us/upload",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_upload_requires_authentication(client):
    data = {"account_id": "1", "file": (io.BytesIO(_valid_xlsx_bytes()), "holdings.xlsx")}
    response = client.post(
        "/api/holdings/us/upload", data=data, content_type="multipart/form-data"
    )
    assert response.status_code == 401


def test_upload_rejects_other_users_account(
    client, other_auth_headers, sample_user, make_kite_account
):
    account_id = make_kite_account(sample_user["id"])
    response = _upload(client, other_auth_headers, "/api/holdings/us/upload", account_id)
    assert response.status_code == 404


@pytest.mark.parametrize(
    "url,service_path,method",
    [
        (
            "/api/holdings/us/refresh-prices",
            "app.services.us_holdings_service.USHoldingsService",
            "refresh_prices",
        ),
        (
            "/api/holdings/eu/refresh-prices",
            "app.services.eu_holdings_service.EUHoldingsService",
            "refresh_prices",
        ),
        (
            "/api/holdings/fd/refresh-values",
            "app.services.fd_service.FDService",
            "refresh_fd_values",
        ),
    ],
)
def test_refresh_flow(
    client,
    auth_headers,
    sample_user,
    make_kite_account,
    monkeypatch,
    url,
    service_path,
    method,
):
    account_id = make_kite_account(sample_user["id"])

    module_name, class_name = service_path.rsplit(".", 1)
    module = __import__(module_name, fromlist=[class_name])
    service_class = getattr(module, class_name)
    monkeypatch.setattr(service_class, method, lambda self, account: 1)

    response = client.post(
        url,
        data=json.dumps({"account_id": account_id}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.data
    assert json.loads(response.data)["updated_count"] == 1
