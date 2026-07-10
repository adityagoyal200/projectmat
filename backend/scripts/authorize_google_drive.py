"""One-time Google Drive OAuth authorization.

Opens a browser consent screen, captures the authorization code on a local
port, exchanges it for a refresh token, and writes GOOGLE_REFRESH_TOKEN to
the project .env. After this, resume imports authenticate automatically.

Usage:
    python scripts/authorize_google_drive.py
"""

import http.server
import re
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings

REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
SCOPE = "https://www.googleapis.com/auth/drive.readonly"
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

_received: dict[str, str] = {}


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            _received["code"] = params["code"][0]
            body = b"Authorization complete. You can close this tab."
        else:
            _received["error"] = params.get("error", ["unknown"])[0]
            body = b"Authorization failed. Check the terminal."
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


def _update_env_file(refresh_token: str) -> Path | None:
    for candidate in [
        Path(__file__).resolve().parents[2] / ".env",
        Path(__file__).resolve().parents[1] / ".env",
    ]:
        if candidate.exists():
            content = candidate.read_text(encoding="utf-8")
            line = f"GOOGLE_REFRESH_TOKEN={refresh_token}"
            if re.search(r"^GOOGLE_REFRESH_TOKEN=.*$", content, re.MULTILINE):
                content = re.sub(
                    r"^GOOGLE_REFRESH_TOKEN=.*$", line, content, flags=re.MULTILINE
                )
            else:
                content = content.rstrip("\n") + "\n" + line + "\n"
            candidate.write_text(content, encoding="utf-8")
            return candidate
    return None


def main() -> int:
    client_id = settings.GOOGLE_CLIENT_ID.strip()
    client_secret = settings.GOOGLE_CLIENT_SECRET.strip()
    if not client_id or not client_secret:
        print(
            "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env first "
            "(APIs & Services -> Credentials -> OAuth client)."
        )
        return 1

    auth_url = (
        AUTH_ENDPOINT
        + "?"
        + urllib.parse.urlencode(
            {
                "client_id": client_id,
                "redirect_uri": REDIRECT_URI,
                "response_type": "code",
                "scope": SCOPE,
                "access_type": "offline",
                "prompt": "consent",
            }
        )
    )

    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    print("Opening browser for Google consent...")
    print(f"If it does not open, visit:\n\n{auth_url}\n")
    webbrowser.open(auth_url)

    thread.join(timeout=300)
    server.server_close()

    if "code" not in _received:
        print(f"Authorization failed: {_received.get('error', 'timed out')}")
        if _received.get("error") == "redirect_uri_mismatch":
            print(
                f"\nAdd {REDIRECT_URI} to the OAuth client's authorized "
                "redirect URIs in Google Cloud Console (only needed for "
                "'Web application' clients; 'Desktop app' clients allow "
                "any localhost port)."
            )
        return 1

    resp = httpx.post(
        TOKEN_ENDPOINT,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": _received["code"],
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        },
        timeout=30,
    )
    resp.raise_for_status()
    tokens = resp.json()
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("No refresh token returned; re-run and approve consent again.")
        return 1

    env_path = _update_env_file(refresh_token)
    if env_path:
        print(f"Saved GOOGLE_REFRESH_TOKEN to {env_path}")
    else:
        print(f"Add this to your .env:\nGOOGLE_REFRESH_TOKEN={refresh_token}")
    print("Drive OAuth is configured. Resume imports will now use the API.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
