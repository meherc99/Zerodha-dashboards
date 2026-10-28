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