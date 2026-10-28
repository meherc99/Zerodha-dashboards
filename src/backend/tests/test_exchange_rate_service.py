from app.services import exchange_rate_service


def test_get_rates_fetches_current_rates_per_currency(monkeypatch):
    calls = []

    def fake_fetch(path, params=None):
        calls.append((path, params))
        if path == '/latest':
            return {
                'date': '2026-10-27',
                'rates': {'INR': 83.5 if params['from'] == 'USD' else 91.4},
            }
        return {
            'date': path[1:],
            'rates': {'INR': 83.0 if params['from'] == 'USD' else 91.0},
        }

    monkeypatch.setattr(exchange_rate_service, '_fetch', fake_fetch)

    result = exchange_rate_service.ExchangeRateService().get_rates()

    latest_calls = [params for path, params in calls if path == '/latest']
    assert latest_calls == [
        {'from': 'USD', 'to': 'INR'},
        {'from': 'EUR', 'to': 'INR'},
    ]
    assert result['date'] == '2026-10-27'
    assert result['USD']['rate'] == 83.5
    assert result['EUR']['rate'] == 91.4


def test_get_rates_skips_historical_response_on_latest_date(monkeypatch):
    def fake_fetch(path, params=None):
        currency = params['from']
        current_rate = 83.5 if currency == 'USD' else 91.4
        previous_rate = 83.0 if currency == 'USD' else 91.0
        if path == '/latest':
            return {
                'date': '2026-10-27',
                'rates': {'INR': current_rate},
            }
        if path == '/2026-10-26':
            return {
                'date': '2026-10-27',
                'rates': {'INR': current_rate},
            }
        return {
            'date': '2026-10-26',
            'rates': {'INR': previous_rate},
        }

    monkeypatch.setattr(exchange_rate_service, '_fetch', fake_fetch)

    result = exchange_rate_service.ExchangeRateService().get_rates()

    assert result['date'] == '2026-10-27'
    assert result['previous_date'] == '2026-10-26'
    assert result['USD']['previous_rate'] == 83.0
    assert result['EUR']['previous_rate'] == 91.0
    assert result['USD']['change'] == 0.5
    assert result['EUR']['change'] == 0.4