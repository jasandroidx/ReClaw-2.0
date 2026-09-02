"""Google OAuth token helper for MCP Gmail/Drive connectors."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

CREDENTIALS_FILE = os.getenv(
    "GOOGLE_CREDENTIALS_FILE",
    "/root/ReClaw-2.0/credentials/.credentials.json",
)
TOKEN_FILE = os.getenv(
    "GOOGLE_TOKEN_FILE",
    "/root/ReClaw-2.0/credentials/google_token.json",
)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_access_token() -> Optional[str]:
    """Return a valid access token, refreshing from google_token.json if needed."""
    token_path = Path(TOKEN_FILE)
    if not token_path.exists():
        return os.getenv("GOOGLE_ACCESS_TOKEN") or os.getenv("GOOGLE_DRIVE_TOKEN") or os.getenv("GMAIL_TOKEN")

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json(), encoding="utf-8")
            os.chmod(token_path, 0o600)
        return creds.token
    except Exception:
        return os.getenv("GOOGLE_ACCESS_TOKEN")