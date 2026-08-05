from __future__ import annotations

import argparse
import re
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

from dotenv import dotenv_values
from kiteconnect import KiteConnect


@dataclass(frozen=True)
class AccountCredentials:
    alias: str
    prefix: str
    api_key: str
    api_secret: str


def sanitize_alias(alias: str) -> str:
    return alias.strip().replace(" ", "_").upper()


def load_account_credentials(env_path: Path, alias: str) -> AccountCredentials:
    values = dotenv_values(env_path)
    prefix = sanitize_alias(alias)
    api_key = (values.get(f"{prefix}_API_KEY") or "").strip()
    api_secret = (values.get(f"{prefix}_API_SECRET") or "").strip()

    if not api_key or not api_secret:
        raise ValueError(
            f"Missing credentials for alias '{alias}'. Expected {prefix}_API_KEY and {prefix}_API_SECRET in {env_path}."
        )

    return AccountCredentials(alias=alias, prefix=prefix, api_key=api_key, api_secret=api_secret)


def upsert_env_var(env_path: Path, key: str, value: str) -> None:
    env_path.parent.mkdir(parents=True, exist_ok=True)

    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    updated = False
    new_lines: list[str] = []

    for line in lines:
        if pattern.match(line):
            new_lines.append(f"{key}={value}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        if new_lines and new_lines[-1] != "":
            new_lines.append("")
        new_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


class CallbackState:
    def __init__(self) -> None:
        self.request_token: Optional[str] = None
        self.error: Optional[str] = None
        self.event = threading.Event()


class KiteCallbackHandler(BaseHTTPRequestHandler):
    state: CallbackState
    callback_path: str

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != self.callback_path:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        params = parse_qs(parsed.query)
        request_token = (params.get("request_token") or [None])[0]
        error = (params.get("error") or [None])[0]

        self.state.request_token = request_token
        self.state.error = error
        self.state.event.set()

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        if request_token:
            message = """
            <html><body style=\"font-family:system-ui;padding:24px\">
            <h2>✅ Authentication successful</h2>
            <p>You can close this tab and return to the terminal.</p>
            </body></html>
            """
        else:
            message = """
            <html><body style=\"font-family:system-ui;padding:24px\">
            <h2>⚠️ Authentication failed</h2>
            <p>No request token was received. Check terminal logs.</p>
            </body></html>
            """

        self.wfile.write(message.encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def wait_for_request_token(port: int, callback_path: str, timeout_seconds: int) -> tuple[Optional[str], Optional[str]]:
    state = CallbackState()

    handler_class = type(
        "_DynamicKiteCallbackHandler",
        (KiteCallbackHandler,),
        {"state": state, "callback_path": callback_path},
    )

    server = HTTPServer(("127.0.0.1", port), handler_class)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        completed = state.event.wait(timeout=timeout_seconds)
    finally:
        server.shutdown()
        server.server_close()

    if not completed:
        return None, f"Timed out after {timeout_seconds}s waiting for Kite callback."

    return state.request_token, state.error


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Open Kite login, capture request_token from redirect, and update ACCESS_TOKEN in .env"
    )
    parser.add_argument("--alias", required=True, help="Account alias from ACCOUNT_ALIASES (e.g. Self)")
    parser.add_argument("--env-file", default=".env", help="Path to .env file (default: .env)")
    parser.add_argument("--port", type=int, default=8765, help="Local callback port (default: 8765)")
    parser.add_argument("--callback-path", default="/callback", help="Local callback path (default: /callback)")
    parser.add_argument("--timeout", type=int, default=180, help="Wait timeout in seconds (default: 180)")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Print login URL only (do not auto-open browser)",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    env_path = Path(args.env_file).expanduser().resolve()

    try:
        creds = load_account_credentials(env_path, args.alias)
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1

    callback_url = f"http://127.0.0.1:{args.port}{args.callback_path}"

    print(f"\nUsing alias: {creds.alias} ({creds.prefix})")
    print(f"Expected local callback URL: {callback_url}")
    print("Make sure this exact URL is added as Redirect URL in your Kite app settings.\n")

    kite = KiteConnect(api_key=creds.api_key)
    login_url = kite.login_url()

    print("Starting local callback server and waiting for Kite redirect...")
    print(f"Login URL: {login_url}\n")

    if not args.no_browser:
        opened = webbrowser.open(login_url)
        if opened:
            print("Opened Kite login in your default browser.")
        else:
            print("Could not auto-open browser. Open the Login URL manually.")

    request_token, callback_error = wait_for_request_token(
        port=args.port,
        callback_path=args.callback_path,
        timeout_seconds=args.timeout,
    )

    if callback_error:
        print(f"[ERROR] {callback_error}")
        return 1

    if not request_token:
        print("[ERROR] Kite callback did not include request_token.")
        return 1

    try:
        session = kite.generate_session(request_token, api_secret=creds.api_secret)
    except Exception as exc:
        print(f"[ERROR] Failed to exchange request_token for access_token: {exc}")
        return 1

    access_token = (session.get("access_token") or "").strip()
    if not access_token:
        print("[ERROR] Kite session response did not include access_token.")
        return 1

    upsert_env_var(env_path, f"{creds.prefix}_ACCESS_TOKEN", access_token)
    upsert_env_var(env_path, f"{creds.prefix}_LAST_TOKEN_REFRESH_TS", str(int(time.time())))

    print("\n✅ Access token generated and saved.")
    print(f"Updated key: {creds.prefix}_ACCESS_TOKEN in {env_path}")
    print("You can now rerun Streamlit sync.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
