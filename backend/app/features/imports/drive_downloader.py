import re
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
import httpx
import structlog
from gdown.download import download
from gdown.download_folder import download_folder

from app.config import settings

logger = structlog.get_logger()

_DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"


def _extract_drive_folder_id(url: str) -> str | None:
    match = re.search(r"/folders/([A-Za-z0-9_\-]+)", url)
    if match:
        return match.group(1)
    match = re.search(r"[?&]id=([A-Za-z0-9_\-]+)", url)
    if match:
        return match.group(1)
    return None


def _get_oauth_access_token() -> str | None:
    """Exchange the stored refresh token for a short-lived access token."""
    client_id = settings.GOOGLE_CLIENT_ID.strip()
    client_secret = settings.GOOGLE_CLIENT_SECRET.strip()
    refresh_token = settings.GOOGLE_REFRESH_TOKEN.strip()
    if not (client_id and client_secret and refresh_token):
        return None
    resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _download_via_drive_api(
    folder_url: str,
    *,
    api_key: str | None = None,
    access_token: str | None = None,
) -> dict[str, bytes]:
    """List and download a Drive folder via the official v3 API.

    Authenticates with an OAuth access token (works for private folders the
    account can see) or an API key (public 'anyone with link' folders). Far
    more reliable than gdown's HTML scraping and not subject to the same
    access-frequency blocks.
    """
    folder_id = _extract_drive_folder_id(folder_url)
    if not folder_id:
        return {}

    headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
    key_params = {"key": api_key} if api_key and not access_token else {}

    resumes: dict[str, bytes] = {}
    with httpx.Client(timeout=60, headers=headers) as client:
        page_token: str | None = None
        files: list[dict] = []
        while True:
            params = {
                "q": f"'{folder_id}' in parents and trashed=false",
                "fields": "nextPageToken, files(id, name, mimeType)",
                "pageSize": 1000,
                **key_params,
            }
            if page_token:
                params["pageToken"] = page_token
            resp = client.get(f"{_DRIVE_API_BASE}/files", params=params)
            resp.raise_for_status()
            payload = resp.json()
            files.extend(payload.get("files", []))
            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        for f in files:
            # Google-native docs need export; resumes are uploaded PDFs/DOCX
            if f.get("mimeType", "").startswith("application/vnd.google-apps"):
                continue
            try:
                resp = client.get(
                    f"{_DRIVE_API_BASE}/files/{f['id']}",
                    params={"alt": "media", **key_params},
                )
                resp.raise_for_status()
                resumes[f["name"]] = resp.content
            except Exception as e:
                logger.warning(
                    "Drive API file download failed",
                    filename=f.get("name"),
                    error=str(e),
                )
    return resumes


def _read_downloaded_files(tmpdir: str) -> dict[str, bytes]:
    resumes: dict[str, bytes] = {}
    for file_path in Path(tmpdir).rglob("*"):
        if file_path.is_file():
            try:
                resumes[file_path.name] = file_path.read_bytes()
            except Exception as e:
                logger.warning(
                    "Failed to read downloaded resume file",
                    filename=file_path.name,
                    error=str(e),
                )
    return resumes


def _extract_drive_file_id(url: str) -> str | None:
    prefixes = ["id=", "/d/", "/file/d/"]
    for prefix in prefixes:
        if prefix in url:
            value = url.split(prefix, 1)[1]
            return value.split("/", 1)[0].split("&", 1)[0]
    return None


def download_resumes_from_drive(folder_url: str) -> dict[str, bytes]:
    """
    Downloads resumes from a public Google Drive folder or file link.
    Returns a dictionary mapping filename -> file_content (bytes).
    """
    resumes: dict[str, bytes] = {}
    if not folder_url:
        return resumes

    # Prefer the official Drive API when credentials are configured — gdown
    # scrapes the web UI and gets blocked after repeated folder accesses.
    # OAuth (refresh token) is tried first, then the API key.
    api_key = settings.GOOGLE_API_KEY.strip()
    access_token: str | None = None
    try:
        access_token = _get_oauth_access_token()
    except Exception as e:
        logger.warning("Google OAuth token refresh failed", error=str(e))

    if access_token or api_key:
        try:
            resumes = _download_via_drive_api(
                folder_url,
                api_key=api_key or None,
                access_token=access_token,
            )
            if resumes:
                logger.info(
                    "Downloaded resumes via Drive API",
                    folder_url=folder_url,
                    count=len(resumes),
                    auth="oauth" if access_token else "api_key",
                )
                return resumes
            logger.warning(
                "Drive API returned no files; falling back to gdown",
                folder_url=folder_url,
            )
        except Exception as e:
            logger.warning(
                "Drive API download failed; falling back to gdown",
                folder_url=folder_url,
                error=str(e),
            )

    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info(
            "Downloading Google Drive resumes", folder_url=folder_url, tmpdir=tmpdir
        )
        try:
            download_folder(url=folder_url, output=tmpdir, quiet=True)
            resumes = _read_downloaded_files(tmpdir)
            if resumes:
                return resumes
        except Exception as e:
            logger.warning(
                "Folder download failed, trying file fallback",
                folder_url=folder_url,
                error=str(e),
            )

        file_id = _extract_drive_file_id(folder_url)
        if file_id:
            file_url = f"https://drive.google.com/uc?id={file_id}"
            output = Path(tmpdir) / f"{file_id}.pdf"
            try:
                download(url=file_url, output=str(output), quiet=True, fuzzy=True)
                resumes = _read_downloaded_files(tmpdir)
                if resumes:
                    return resumes
            except Exception as e:
                logger.error(
                    "Failed to download resumes from Google Drive",
                    folder_url=folder_url,
                    file_url=file_url,
                    error=str(e),
                )
                return resumes

        logger.error(
            "Failed to download resumes from Google Drive",
            folder_url=folder_url,
            error="No downloadable files found",
        )
    return resumes


def parse_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extracts text from PDF bytes in-memory using PyMuPDF.

    Also appends the URIs of embedded link annotations: visible URL text is
    often wrapped/truncated at line breaks by the PDF layout, while the
    annotation target stores the full URL.
    """
    text = ""
    link_uris: list[str] = []
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                page_text = page.get_text()
                if isinstance(page_text, str):
                    text += page_text
                else:
                    text += str(page_text)
                for link in page.get_links():
                    uri = link.get("uri")
                    if uri and uri not in link_uris:
                        link_uris.append(uri)
    except Exception as e:
        logger.error("Failed to parse PDF bytes in-memory", error=str(e))
    if link_uris:
        text += "\n" + "\n".join(link_uris)
    return text
