#!/usr/bin/env python3
"""One-time Google OAuth setup for ReClaw MCP Gmail + Drive connectors."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.google_oauth import CREDENTIALS_FILE, SCOPES, TOKEN_FILE

SUCCESS_HTML = b"""<!DOCTYPE html><html><body style="font-family:sans-serif;text-align:center;padding:40px">
<h1 style="color:green">ReClaw connected!</h1>
<p>Gmail + Drive access saved on the server.</p>
<p>You can close this tab.</p></body></html>"""


def _tailscale_ip() -> str:
    try:
        out = subprocess.check_output(["tailscale", "ip", "-4"], text=True, timeout=5)
        return out.strip()
    except Exception:
        return "127.0.0.1"


def _save_token(creds) -> Path:
    token_path = Path(TOKEN_FILE)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    os.chmod(token_path, 0o600)
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        text = env_path.read_text(encoding="utf-8")
        for key, val in [
            ("GOOGLE_TOKEN_FILE", TOKEN_FILE),
            ("GOOGLE_CREDENTIALS_FILE", CREDENTIALS_FILE),
        ]:
            if f"{key}=" not in text:
                text += f"\n{key}={val}\n"
        env_path.write_text(text, encoding="utf-8")
    return token_path


def run_auto(port: int = 8765) -> None:
    """Listen on Tailscale IP; capture code automatically — no copy/paste needed."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    host = _tailscale_ip()
    redirect_uri = f"http://{host}:{port}/"
    creds_path = Path(CREDENTIALS_FILE)
    if not creds_path.exists():
        print(f"Missing credentials file: {creds_path}")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    flow.redirect_uri = redirect_uri
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

    captured: dict = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            if "code" in params:
                captured["code"] = params["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(SUCCESS_HTML)
            elif "error" in params:
                captured["error"] = params.get("error", ["unknown"])[0]
                self.send_response(400)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(f"OAuth error: {captured['error']}".encode())
            else:
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"ReClaw OAuth callback server running.")

    server = HTTPServer(("0.0.0.0", port), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print("\n=== AUTO OAUTH (no copy/paste) ===\n")
    print("FIRST: In Google Cloud Console -> Credentials -> your OAuth client")
    print("Add this Authorized redirect URI (if not already):")
    print(f"  {redirect_uri}\n")
    print("Make sure your Gmail is a Test user on the OAuth consent screen.\n")
    print("Then open this link on your phone (Tailscale connected) or PC:\n")
    print(auth_url)
    print(f"\nWaiting up to 5 minutes for callback on {redirect_uri} ...\n")

    deadline = time.time() + 300
    while time.time() < deadline:
        if "code" in captured:
            break
        if "error" in captured:
            print(f"OAuth error: {captured['error']}")
            server.shutdown()
            sys.exit(1)
        time.sleep(0.5)

    server.shutdown()

    if "code" not in captured:
        print("Timed out — no callback received.")
        sys.exit(1)

    flow.fetch_token(code=captured["code"])
    token_path = _save_token(flow.credentials)
    print(f"SUCCESS: token saved to {token_path}")


def main():
    parser = argparse.ArgumentParser(description="Google OAuth setup for ReClaw")
    parser.add_argument("--auto", action="store_true", help="Auto-capture via Tailscale callback (no copy)")
    parser.add_argument("--port", type=int, default=8765, help="Callback port for --auto (default 8765)")
    parser.add_argument("--url-only", action="store_true", help="Print authorization URL only")
    parser.add_argument("--code", help="Authorization code from Google (manual fallback)")
    args = parser.parse_args()

    if args.auto:
        run_auto(port=args.port)
        return

    creds_path = Path(CREDENTIALS_FILE)
    if not creds_path.exists():
        print(f"Missing credentials file: {creds_path}")
        sys.exit(1)

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)

    if args.url_only:
        flow.redirect_uri = "http://localhost"
        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
        print("\n=== GOOGLE OAUTH — open this URL on your phone/PC ===\n")
        print(auth_url)
        print("\nPrefer no copy/paste? Run: python scripts/google_oauth_setup.py --auto\n")
        return

    if args.code:
        flow.redirect_uri = "http://localhost"
        flow.fetch_token(code=args.code)
        creds = flow.credentials
    else:
        print("Running console flow — paste the code Google gives you:\n")
        creds = flow.run_console()

    token_path = _save_token(creds)
    print(f"\nToken saved: {token_path}")


if __name__ == "__main__":
    main()