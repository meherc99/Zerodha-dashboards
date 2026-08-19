"""
AMFI (Association of Mutual Funds in India) NAV enrichment service.

Uses mfapi.in — a free, unauthenticated community API wrapping AMFI data:
  https://api.mfapi.in/mf/<scheme_code>

Strategy for resolving Kite MF holdings → mfapi.in scheme_code:

  1. **Numeric tradingsymbol** (primary path)
     Kite Coin platform stores the AMFI scheme code as the tradingsymbol
     for directly-held regular/direct mutual fund units.  If the
     tradingsymbol is an integer string we query mfapi.in directly with it.

  2. **ISIN lookup via mfapi.in search** (fallback)
     If the tradingsymbol is not numeric, we search mfapi.in by fund name
     keywords and verify the result by matching ``meta.isin_growth`` or
     ``meta.isin_div_reinvestment`` against the Kite ISIN.  Results are
     cached for the lifetime of the process.

The service is intentionally stateless and makes no database calls.  It is
called from KiteService.get_mutual_fund_holdings() after the Kite /mf/holdings
response is available.
"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

_MFAPI_BASE = 'https://api.mfapi.in/mf'

# Module-level session for connection reuse
_session = requests.Session()
_session.headers.update({'User-Agent': 'ZerodhaDashboard/1.0'})
_TIMEOUT = 10  # seconds per request

# In-process cache: ISIN → scheme_code string
_isin_scheme_cache: Dict[str, Optional[str]] = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_scheme_data(scheme_code: str) -> Optional[dict]:
    """
    Fetch full scheme data from mfapi.in for *scheme_code*.

    Returns the parsed JSON dict (keys: ``meta``, ``data``) or None on failure.
    """
    url = f'{_MFAPI_BASE}/{scheme_code}'
    try:
        resp = _session.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
        # mfapi returns {"error": "..."} for bad codes
        if 'error' in payload:
            return None
        return payload
    except Exception as exc:
        logger.debug('mfapi fetch failed for scheme %s: %s', scheme_code, exc)
        return None


def _search_scheme_by_name(keywords: str) -> List[dict]:
    """Search mfapi.in by name keywords. Returns list of {schemeCode, schemeName}."""
    try:
        resp = _session.get(
            f'{_MFAPI_BASE}/search',
            params={'q': keywords},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json() or []
    except Exception as exc:
        logger.debug('mfapi search failed for %r: %s', keywords, exc)
        return []


def _resolve_scheme_code_by_isin(isin: str, fund_name: str) -> Optional[str]:
    """
    Resolve a Kite ISIN to an mfapi.in scheme_code.

    Tries a name-keyword search, then verifies each candidate by checking
    ``meta.isin_growth`` / ``meta.isin_div_reinvestment``.

    Results (including misses) are cached for the process lifetime.
    """
    if isin in _isin_scheme_cache:
        return _isin_scheme_cache[isin]

    # Build search keywords from fund name (first 3 significant words)
    words = [w for w in fund_name.replace('-', ' ').split() if len(w) > 2]
    query = ' '.join(words[:4]) if words else fund_name[:30]

    candidates = _search_scheme_by_name(query)
    for candidate in candidates:
        sc = str(candidate.get('schemeCode', ''))
        if not sc:
            continue
        data = _fetch_scheme_data(sc)
        if not data:
            continue
        meta = data.get('meta', {})
        if isin in (meta.get('isin_growth'), meta.get('isin_div_reinvestment')):
            logger.info('Resolved ISIN %s → scheme_code %s via name search', isin, sc)
            _isin_scheme_cache[isin] = sc
            return sc

    logger.debug('Could not resolve ISIN %s (query=%r) to any scheme_code', isin, query)
    _isin_scheme_cache[isin] = None
    return None


def _navs_from_scheme_data(scheme_data: dict) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """
    Extract (today_nav, yesterday_nav) from mfapi.in scheme data.
    Returns (None, None) if data is insufficient.
    """
    entries = scheme_data.get('data', [])
    try:
        today = Decimal(str(entries[0]['nav'])) if len(entries) >= 1 else None
        yesterday = Decimal(str(entries[1]['nav'])) if len(entries) >= 2 else None
        return today, yesterday
    except (KeyError, IndexError, InvalidOperation):
        return None, None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enrich_mf_holdings(holdings: List[dict]) -> List[dict]:
    """
    Given a list of normalised MF holding dicts (from KiteService), add
    accurate ``day_change`` and ``day_change_percentage`` using mfapi.in.

    Strategy per holding:
      1. If ``tradingsymbol`` is numeric → use as mfapi.in scheme_code directly.
      2. Else if ``isin`` is present → attempt ISIN→scheme_code resolution via
         mfapi.in name search + ISIN verification.
      3. If neither works, leave day_change = 0 (Kite default).

    Updates are done **in-place**; the same list is returned.
    """
    if not holdings:
        return holdings

    # Collect unique scheme lookups to minimise HTTP calls
    # key → scheme_code str (or None if unresolvable)
    holding_scheme: List[Optional[str]] = []

    seen: Dict[str, Optional[str]] = {}  # tradingsymbol/isin → scheme_code

    for holding in holdings:
        symbol = holding.get('tradingsymbol', '')
        isin = holding.get('isin', '')

        if symbol.isdigit():
            # Primary path: Kite Coin stores AMFI scheme_code as tradingsymbol
            sc = symbol
        elif isin:
            fund_name = holding.get('fund_name') or holding.get('tradingsymbol') or ''
            cache_key = isin
            if cache_key not in seen:
                seen[cache_key] = _resolve_scheme_code_by_isin(isin, fund_name)
            sc = seen[cache_key]
        else:
            sc = None

        holding_scheme.append(sc)

    # Fetch scheme data (deduplicated)
    scheme_data_cache: Dict[str, Optional[dict]] = {}
    for sc in set(filter(None, holding_scheme)):
        if sc not in scheme_data_cache:
            scheme_data_cache[sc] = _fetch_scheme_data(sc)

    # Enrich holdings
    enriched = 0
    for holding, sc in zip(holdings, holding_scheme):
        if not sc:
            continue
        data = scheme_data_cache.get(sc)
        if not data:
            continue

        today_nav, yesterday_nav = _navs_from_scheme_data(data)
        if today_nav is None:
            continue

        qty = holding.get('quantity', Decimal('0'))

        # Update last_price and current_value to official AMFI NAV
        holding['last_price'] = today_nav
        holding['current_value'] = qty * today_nav

        if yesterday_nav and yesterday_nav > 0:
            day_change_per_unit = today_nav - yesterday_nav
            holding['day_change'] = day_change_per_unit * qty
            holding['day_change_percentage'] = float(
                (day_change_per_unit / yesterday_nav) * 100
            )
            enriched += 1
        else:
            holding['day_change'] = Decimal('0')
            holding['day_change_percentage'] = 0.0

    logger.info(
        'mfapi enrichment: %d/%d MF holdings got day-change data',
        enriched, len(holdings),
    )
    return holdings
