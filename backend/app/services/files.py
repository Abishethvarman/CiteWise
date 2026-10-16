import hashlib
import re
from pathlib import Path

import pymupdf

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_ALLOWED_TYPES = {"application/pdf", "application/octet-stream", "binary/octet-stream", ""}


class FileRejected(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def display_name(filename: str | None) -> str:
    name = Path(filename or "document.pdf").name
    name = re.sub(r"[^\w.\- ()]", "_", name, flags=re.UNICODE)
    name = name.strip(" .") or "document.pdf"
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name[:180]


def storage_path(data_dir: Path, document_id: str) -> Path:
    if not UUID_RE.fullmatch(document_id or ""):
        raise FileRejected("Invalid document id", 422)
    root = (data_dir / "uploads").resolve()
    path = (root / f"{document_id}.pdf").resolve()
    if path.parent != root:
        raise FileRejected("Unsafe storage path", 400)
    return path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_pdf(
    filename: str | None, content_type: str | None, data: bytes, max_bytes: int, max_pages: int
) -> int:
    if not data:
        raise FileRejected("The upload is empty", 400)
    if len(data) > max_bytes:
        raise FileRejected("The file is larger than the configured upload limit", 413)
    media = (content_type or "").split(";", 1)[0].strip().lower()
    if media not in _ALLOWED_TYPES or not (filename or "").lower().endswith(".pdf"):
        raise FileRejected("Only PDF files are supported", 415)
    if b"%PDF" not in data[:1024]:
        raise FileRejected("The file is not a PDF", 415)
    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise FileRejected("The file could not be read as a PDF", 400) from exc
    try:
        if document.is_encrypted and not document.authenticate(""):
            raise FileRejected("Encrypted PDFs are not supported", 400)
        page_count = int(document.page_count)
    finally:
        document.close()
    if page_count < 1:
        raise FileRejected("The PDF contains no pages", 400)
    if page_count > max_pages:
        raise FileRejected(
            f"This PDF has {page_count} pages, which is above the limit of {max_pages}",
            413,
        )
    return page_count


def extract_pages(data: bytes) -> list[tuple[int, str]]:
    document = pymupdf.open(stream=data, filetype="pdf")
    pages: list[tuple[int, str]] = []
    try:
        if document.is_encrypted and not document.authenticate(""):
            raise FileRejected("Encrypted PDFs are not supported", 400)
        for index in range(document.page_count):
            text = document.load_page(index).get_text("text") or ""
            pages.append((index + 1, text))
    finally:
        document.close()
    return pages
