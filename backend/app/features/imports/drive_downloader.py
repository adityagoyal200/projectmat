import tempfile
from pathlib import Path

import fitz  # PyMuPDF
import structlog
from gdown.download import download
from gdown.download_folder import download_folder

logger = structlog.get_logger()


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
    """Extracts text from PDF bytes in-memory using PyMuPDF."""
    text = ""
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                page_text = page.get_text()
                if isinstance(page_text, str):
                    text += page_text
                else:
                    text += str(page_text)
    except Exception as e:
        logger.error("Failed to parse PDF bytes in-memory", error=str(e))
    return text
