"""
AMFI (Association of Mutual Funds in India) NAV enrichment service.

Uses two free, unauthenticated public sources:
  1. https://www.amfiindia.com/spages/NAVAll.txt
     Full daily NAV feed for all schemes.  Parsed to build an ISIN→scheme-code
     map and capture today's official NAV.

  2. https://api.mfapi.in/mf/<scheme_code>
     Community wrapper around AMFI historical data.  Returns the last N NAV
     entries so we can grab the two most-recent values and compute a genuine
     day-over-day change.

The service is intentionally stateless and makes no database calls.  It is
called from KiteService.get_mutual_fund_holdings() after the Kite /mf/holdings
response is available.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

_AMFI_NAV_URL = 'https://www.amfiindia.com/spages/NAVAll.txt'
_MFAPI_URL = 'https://api.mfapi.in/mf/{scheme_code}'

# Shared session for connection reuse
_session = requests.Session()
_session.headers.update({'User-Agent': 'ZerodhaDashboard/1.0'})
_TIMEOUT = 10  # seconds per request


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def fetch_nav_feed() -> Dict[str, dict]:
    """
    Download and parse the AMFI NAV-all text feed.

    Returns
    -------
    dict keyed by ISIN (both payout and growth ISINs map to the same entry)::

        {
            '<isin>': {
                'scheme_code': '100028',
                'scheme_name': 'ICICI Pru Liquid …',
                'nav': Decimal('100.4538'),
                'nav_date': '03-Aug-2026',
            },
            …
        }
    """
    try:
        resp = _session.get(_AMFI_NAV_URL, timeout=_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning('AMFI feed fetch failed: %s', exc)
        return {}

    result: Dict[str, dict] = {}
    for line in resp.text.splitlines():
        line = line.strip()
        if not line or ';' not in line:
            continue
        parts = line.split(';')
        if len(parts) < 6:
            continue
        scheme_code, isin1, isin2, scheme_name, nav_str, nav_date = (
            parts[0].strip(),
            parts[1].strip(),
            parts[2].strip(),
            parts[3].strip(),
            parts[4].strip(),
            parts[5].strip(),
        )
        try:
            nav = Decimal(nav_str)
        except Exception:
            continue

        entry = {
            'scheme_code': scheme_code,
            'scheme_name': scheme_name,
            'nav': nav,
            'nav_date': nav_date,
        }
        for isin in (isin1, isin2):
            if isin and isin != '-':
                result[isin] = entry

    logger.info('AMFI feed parsed: %d ISIN entries', len(result))
    return result


def fetch_previous_nav(scheme_code: str) -> Optional[Decimal]:
    """
    Fetch the two most-recent NAV entries from mfapi.in for *scheme_code*
    and return the second-most-recent value (i.e. "yesterday's" NAV).

    Returns None on any failure so callers can degrade gracefully.
    """
    url = _MFAPI_URL.format(scheme_code=scheme_code)
    try:
        resp = _session.get(url, timeout=_TIMEOUT, params={'type': 'json'})
        resp.raise_for_status()
        data = resp.json().get('data', [])
        if len(data) >= 2:
            return Decimal(str(data[1]['nav']))
        if len(data) == 1:
            # Only one entry available — no previous day to compare
            return None
    except Exception as exc:
        logger.debug('mfapi fetch failed for scheme %s: %s', scheme_code, exc)
    return None


def enrich_mf_holdings(holdings: List[dict]) -> List[dict]:
    """
    Given a list of normalised MF holding dicts (from KiteService), add
    accurate ``day_change`` and ``day_change_percentage`` using AMFI data.

    The function:
      1. Fetches the full AMFI NAV feed once.
      2. For each holding whose ISIN is found in the feed, calls mfapi.in
         to retrieve yesterday's NAV.
      3. Updates ``last_price``, ``day_change``, and ``day_change_percentage``
         in-place and returns the (possibly mutated) list.

    Holdings whose ISIN is absent from the feed (e.g. ETFs traded on exchange
    rather than via Coin, or missing ISIN) are left unchanged.
    """
    if not holdings:
        return holdings

    nav_feed = fetch_nav_feed()
    if not nav_feed:
        logger.warning('AMFI feed empty — skipping MF day-change enrichment')
        return holdings

    # Deduplicate scheme_code requests
    isin_to_entry: Dict[str, dict] = {}
    for holding in holdings:
        isin = holding.get('isin')
        if isin and isin in nav_feed:
            isin_to_entry[isin] = nav_feed[isin]

    # Fetch previous-day NAVs (one request per unique scheme_code)
    scheme_code_to_prev: Dict[str, Optional[Decimal]] = {}
    fetched_scheme_codes = set()
    for isin, entry in isin_to_entry.items():
        sc = entry['scheme_code']
        if sc not in fetched_scheme_codes:
            fetched_scheme_codes.add(sc)
            scheme_code_to_prev[sc] = fetch_previous_nav(sc)

    # Enrich holdings
    enriched = 0
    for holding in holdings:
        isin = holding.get('isin')
        if not isin or isin not in isin_to_entry:
            continue
        entry = isin_to_entry[isin]
        current_nav = entry['nav']
        prev_nav = scheme_code_to_prev.get(entry['scheme_code'])

        # Update last_price to today's official AMFI NAV
        holding['last_price'] = current_nav

        # Recompute current_value with fresh NAV
        qty = holding.get('quantity', Decimal('0'))
        holding['current_value'] = qty * current_nav

        if prev_nav and prev_nav > 0:
            day_change = current_nav - prev_nav
            holding['day_change'] = day_change
            holding['day_change_percentage'] = (day_change / prev_nav) * 100
            enriched += 1
        else:
            holding['day_change'] = Decimal('0')
            holding['day_change_percentage'] = Decimal('0')

    logger.info(
        'AMFI enrichment: %d/%d MF holdings got day-change data',
        enriched, len(holdings),
    )
    return holdings
