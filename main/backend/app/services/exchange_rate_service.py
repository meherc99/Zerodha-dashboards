"""Live and previous-day exchange rate fetching via the free Frankfurter API."""
import logging
from datetime import date, timedelta

import requests

logger = logging.getLogger(__name__)

_FRANKFURTER_BASE = 'https://api.frankfurter.app'
_TIMEOUT = 8  # seconds


def _fetch(path, params=None):
    resp = requests.get(
        f'{_FRANKFURTER_BASE}{path}',
        params=params,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


class ExchangeRateService:
    """Fetch USD/INR and EUR/INR rates (current and previous trading day)."""

    CURRENCIES = ['USD', 'EUR']
    BASE = 'INR'

    def get_rates(self):
        """Return current and previous-day rates for USD and EUR against INR.

        Returns a dict like::

            {
                "USD": {"rate": 83.5, "previous_rate": 83.4, "change": 0.1, "change_pct": 0.12},
                "EUR": {"rate": 91.2, "previous_rate": 91.0, "change": 0.2, "change_pct": 0.22},
                "date": "2026-08-21",
                "previous_date": "2026-08-20",
            }
        """
        try:
            latest = _fetch('/latest', params={
                'from': ','.join(self.CURRENCIES),
                'to': self.BASE,
            })
            current_date = latest.get('date', str(date.today()))
            current_rates = {
                currency: latest['rates'][self.BASE] / latest['rates'].get(currency, 1)
                for currency in self.CURRENCIES
            }
            # Frankfurter returns rates FROM each currency, so for
            # "from=USD&to=INR" the response has {"rates": {"INR": 83.5}}.
            # But with multiple from-currencies it returns per-currency blocks.
            # Use the simpler per-currency call style to be safe.
            current_rates = {}
            for currency in self.CURRENCIES:
                data = _fetch('/latest', params={'from': currency, 'to': self.BASE})
                current_rates[currency] = data['rates'][self.BASE]
        except Exception:
            logger.error('Exchange rate fetch (current) failed')
            raise

        try:
            # Frankfurter's /latest returns the most-recent trading day.
            # Fetch yesterday's date as starting point, walk back up to 7 days
            # to find the previous trading day's rate.
            prev_rates = {}
            prev_date = None
            for currency in self.CURRENCIES:
                found = False
                for days_back in range(1, 8):
                    candidate = date.today() - timedelta(days=days_back)
                    try:
                        data = _fetch(
                            f'/{candidate}',
                            params={'from': currency, 'to': self.BASE},
                        )
                        prev_rates[currency] = data['rates'][self.BASE]
                        if prev_date is None:
                            prev_date = data.get('date', str(candidate))
                        found = True
                        break
                    except Exception:
                        continue
                if not found:
                    prev_rates[currency] = current_rates[currency]
        except Exception:
            logger.warning('Previous-day exchange rate fetch failed; using current rates')
            prev_rates = dict(current_rates)
            prev_date = current_date

        result = {'date': current_date, 'previous_date': prev_date or current_date}
        for currency in self.CURRENCIES:
            rate = current_rates[currency]
            prev = prev_rates.get(currency, rate)
            change = rate - prev
            change_pct = (change / prev * 100) if prev else 0.0
            result[currency] = {
                'rate': round(rate, 4),
                'previous_rate': round(prev, 4),
                'change': round(change, 4),
                'change_pct': round(change_pct, 4),
            }
        return result
