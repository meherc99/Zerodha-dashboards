"""Portfolio analytics endpoints exercised against synced data.

Endpoints that read the local database (sector breakdown, performance metrics,
heatmap, value history) run against real synced holdings. Endpoints that reach
external providers (exchange rates, correlation matrix) have those providers
mocked so the HTTP contract is still verified deterministically.
"""
import json
from decimal import Decimal


class _FakeKiteService:
    def __init__(self, api_key=None, api_secret=None, access_token=None):
        pass

    def get_holdings(self):
        return [
            {
                "holding_key": "equity:NSE:INE009A01021",
                "tradingsymbol": "INFY",
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
        ]


def _sync(client, headers, account_id, monkeypatch):
    from app.services import scheduler_service

    monkeypatch.setattr(scheduler_service, "KiteService", _FakeKiteService)
    client.post(
        "/api/holdings/sync",
        data=json.dumps({"account_id": account_id}),
        content_type="application/json",
        headers=headers,
    )


def test_sector_breakdown(client, auth_headers, sample_user, make_kite_account, monkeypatch):
    account_id = make_kite_account(sample_user["id"])
    _sync(client, auth_headers, account_id, monkeypatch)

    response = client.get("/api/analytics/sector-breakdown", headers=auth_headers)
    assert response.status_code == 200
    assert "sectors" in json.loads(response.data)


def test_performance_metrics(client, auth_headers, sample_user, make_kite_account, monkeypatch):
    account_id = make_kite_account(sample_user["id"])
    _sync(client, auth_headers, account_id, monkeypatch)

    response = client.get("/api/analytics/performance-metrics", headers=auth_headers)
    assert response.status_code == 200
    body = json.loads(response.data)
    assert "top_performers" in body
    assert "worst_performers" in body


def test_performance_metrics_rejects_out_of_range_period(client, auth_headers):
    response = client.get(
        "/api/analytics/performance-metrics?period_days=5000", headers=auth_headers
    )
    assert response.status_code == 400


def test_heatmap(client, auth_headers, sample_user, make_kite_account, monkeypatch):
    account_id = make_kite_account(sample_user["id"])
    _sync(client, auth_headers, account_id, monkeypatch)

    response = client.get("/api/analytics/heatmap", headers=auth_headers)
    assert response.status_code == 200
    assert "data" in json.loads(response.data)


def test_heatmap_rejects_invalid_metric(client, auth_headers):
    response = client.get(
        "/api/analytics/heatmap?metric=not-a-metric", headers=auth_headers
    )
    assert response.status_code == 400


def test_portfolio_value_history(client, auth_headers):
    response = client.get(
        "/api/analytics/portfolio-value-history", headers=auth_headers
    )
    assert response.status_code == 200
    body = json.loads(response.data)
    assert "timeseries" in body
    assert body["data_points"] == len(body["timeseries"])


def test_portfolio_value_history_rejects_bad_granularity(client, auth_headers):
    response = client.get(
        "/api/analytics/portfolio-value-history?granularity=hourly",
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_exchange_rates(client, auth_headers, monkeypatch):
    from app.services.exchange_rate_service import ExchangeRateService

    monkeypatch.setattr(
        ExchangeRateService,
        "get_rates",
        lambda self: {"USD_INR": 83.1, "EUR_INR": 90.2},
    )

    response = client.get("/api/analytics/exchange-rates", headers=auth_headers)
    assert response.status_code == 200
    assert json.loads(response.data)["USD_INR"] == 83.1


def test_correlation_matrix(client, auth_headers, monkeypatch):
    from app.services.analytics_service import AnalyticsService

    monkeypatch.setattr(
        AnalyticsService,
        "calculate_correlation_matrix",
        staticmethod(lambda symbols, period_days: {"symbols": symbols, "matrix": []}),
    )

    response = client.get(
        "/api/analytics/correlation-matrix?symbols=INFY,TCS&period=90",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert json.loads(response.data)["symbols"] == ["INFY", "TCS"]


def test_correlation_matrix_requires_two_symbols(client, auth_headers):
    response = client.get(
        "/api/analytics/correlation-matrix?symbols=INFY", headers=auth_headers
    )
    assert response.status_code == 400


def test_analytics_requires_authentication(client):
    assert client.get("/api/analytics/sector-breakdown").status_code == 401
