import tempfile

import fitz  # PyMuPDF
import structlog
from gdown.download_folder import download_folder

logger = structlog.get_logger()


def download_resumes_from_drive(folder_url: str) -> dict[str, bytes]:
    """
    Downloads all files from a public Google Drive folder.
    Returns a dictionary mapping filename -> file_content (bytes).
    """
    resumes: dict[str, bytes] = {}
    if not folder_url:
        return resumes
    try:
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            logger.info(
                "Downloading Google Drive resumes", folder_url=folder_url, tmpdir=tmpdir
            )
            download_folder(url=folder_url, output=tmpdir, quiet=True)

            for file_path in Path(tmpdir).rglob("*"):
                if file_path.is_file():
                    try:
                        resumes[file_path.name] = file_path.read_bytes()
                    except Exception as e:
                        logger.warn(
                            "Failed to read downloaded resume file",
                            filename=file_path.name,
                            error=str(e),
                        )
    except Exception as e:
        logger.error(
            "Failed to download resumes from Google Drive",
            folder_url=folder_url,
            error=str(e),
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
