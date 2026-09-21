"""Frontend<->backend API contract test.

This is the core "don't break production" guard for the seam between the Vue
frontend and the Flask API. It scans every HTTP call the frontend makes
(``api.<verb>('/path')`` and ``apiClient.<verb>('/path')`` across the whole
``frontend/src`` tree) and asserts that each one maps to a route the backend
actually registers, with a matching HTTP method.

If a backend route is renamed, its method changes, or a frontend call is added
that has no server handler, this test fails before the mismatch reaches users.
"""
import os
import re

import pytest

from conftest import FRONTEND_SRC

# Matches api.get('/x'), apiClient.post(`/x/${id}`, ...), etc. The path always
# starts with '/' and never contains a quote/backtick, so a simple character
# class terminates it correctly for plain and template strings alike.
CALL_PATTERN = re.compile(
    r"\b(?:api|apiClient)\.(get|post|put|delete|patch)\(\s*[\"'`](/[^\"'`]*)"
)
# Flask converters such as <int:account_id> or <path:filename>.
RULE_PARAM = re.compile(r"<[^>]+>")
# Frontend template interpolation such as ${accountId}.
TEMPLATE_PARAM = re.compile(r"\$\{[^}]+\}")


def _normalise(path):
    """Reduce a URL to (path-with-{}-params) so both sides compare equally."""
    path = RULE_PARAM.sub("{}", path)
    path = TEMPLATE_PARAM.sub("{}", path)
    if len(path) > 1:
        path = path.rstrip("/")
    return path


def _iter_frontend_source_files():
    for root, _dirs, files in os.walk(FRONTEND_SRC):
        for name in files:
            if name.endswith((".js", ".vue")):
                yield os.path.join(root, name)


def _collect_frontend_calls():
    """Return a set of (METHOD, normalised-path) pairs used by the frontend."""
    calls = set()
    for file_path in _iter_frontend_source_files():
        with open(file_path, encoding="utf-8") as handle:
            source = handle.read()
        for method, raw_path in CALL_PATTERN.findall(source):
            # The frontend axios client is configured with a '/api' baseURL, so
            # every relative call is prefixed with '/api' on the wire.
            full_path = "/api" + raw_path if raw_path != "/" else "/api"
            calls.add((method.upper(), _normalise(full_path)))
    return calls


def _collect_backend_routes(app):
    """Return a set of (METHOD, normalised-path) pairs the backend serves."""
    routes = set()
    for rule in app.url_map.iter_rules():
        normalised = _normalise(rule.rule)
        for method in rule.methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            routes.add((method, normalised))
    return routes


def test_frontend_source_defines_api_calls():
    """Guard against the scanner silently matching nothing."""
    calls = _collect_frontend_calls()
    assert calls, "No frontend API calls were discovered; the scanner regex may be broken."


def test_every_frontend_call_has_a_backend_route(app):
    """Every endpoint the frontend calls must exist on the backend."""
    frontend_calls = _collect_frontend_calls()
    backend_routes = _collect_backend_routes(app)

    missing = sorted(call for call in frontend_calls if call not in backend_routes)

    assert not missing, (
        "Frontend calls without a matching backend route "
        "(method, path):\n" + "\n".join(f"  {m} {p}" for m, p in missing)
    )


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/auth/register"),
        ("POST", "/api/auth/login"),
        ("GET", "/api/auth/me"),
        ("POST", "/api/auth/logout"),
        ("GET", "/api/accounts"),
        ("POST", "/api/holdings/sync"),
        ("GET", "/api/holdings"),
        ("GET", "/api/analytics/performance-metrics"),
        ("GET", "/api/bank-accounts"),
        ("GET", "/api/categories"),
    ],
)
def test_critical_endpoints_are_registered(app, method, path):
    """Explicit smoke list so a dropped critical route is obvious in the report."""
    backend_routes = _collect_backend_routes(app)
    assert (method, _normalise(path)) in backend_routes
