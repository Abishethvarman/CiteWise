import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Chunk, Document, Page
from app.schemas import StoredSettings
from app.services.chunking import chunk_id_for, chunk_text
from app.services.files import FileRejected, extract_pages, storage_path
from app.services.index_store import IndexStore
from app.services.settings_store import utcnow

logger = logging.getLogger("citewise.ingestion")
EMPTY_PAGE_CHARS = 15


def ingest_document(
    db: Session, settings: Settings, index_store: IndexStore, document_id: str
) -> None:
    document = db.get(Document, document_id)
    if document is None:
        logger.info("ingestion skipped missing document id=%s", document_id)
        return
    runtime = _runtime(db, settings)
    document.status = "processing"
    document.index_status = "indexing"
    document.error_message = None
    db.commit()
    try:
        path = storage_path(settings.data_dir, document.id)
        data = path.read_bytes()
        pages = extract_pages(data)
        _replace_pages_and_chunks(db, document, pages, runtime)
        notes, likely_scanned, indexed = _notes_for(pages)
        document.page_count = len(pages)
        document.likely_scanned = likely_scanned
        document.extraction_notes = notes
        document.status = "ready"
        document.index_status = "ready" if indexed else "no_text"
        document.processed_at = utcnow()
        db.commit()
        index_store.rebuild(db, runtime)
        logger.info(
            "ingestion ready id=%s pages=%s indexed=%s",
            document.id,
            document.page_count,
            indexed,
        )
    except Exception as exc:
        db.rollback()
        failed = db.get(Document, document_id)
        if failed is not None:
            failed.status = "failed"
            failed.index_status = "failed"
            failed.error_message = f"Extraction failed ({type(exc).__name__}): {str(exc)[:240]}"
            failed.processed_at = utcnow()
            db.commit()
        logger.info("ingestion failed id=%s error_type=%s", document_id, type(exc).__name__)


def _runtime(db: Session, settings: Settings) -> StoredSettings:
    from app.services.settings_store import load_runtime

    return load_runtime(db, settings)


def _replace_pages_and_chunks(
    db: Session,
    document: Document,
    pages: list[tuple[int, str]],
    runtime: StoredSettings,
) -> None:
    db.execute(delete(Chunk).where(Chunk.document_id == document.id))
    db.execute(delete(Page).where(Page.document_id == document.id))
    for page_number, text in pages:
        stripped = text.strip()
        db.add(
            Page(
                id=str(uuid.uuid4()),
                document_id=document.id,
                page_number=page_number,
                text=text,
                char_count=len(text),
                is_empty=len(stripped) < EMPTY_PAGE_CHARS,
            )
        )
        if len(stripped) < EMPTY_PAGE_CHARS:
            continue
        for piece in chunk_text(text, runtime.chunk_size, runtime.chunk_overlap):
            db.add(
                Chunk(
                    id=chunk_id_for(
                        document.id, page_number, piece.chunk_index, piece.start_offset
                    ),
                    document_id=document.id,
                    page_number=page_number,
                    chunk_index=piece.chunk_index,
                    text=piece.text,
                    token_count=piece.token_count,
                    start_offset=piece.start_offset,
                    end_offset=piece.end_offset,
                )
            )
    db.commit()


def _notes_for(pages: list[tuple[int, str]]) -> tuple[str | None, bool, bool]:
    empty_numbers = [number for number, text in pages if len(text.strip()) < EMPTY_PAGE_CHARS]
    indexed = len(empty_numbers) < len(pages)
    likely_scanned = bool(pages) and len(empty_numbers) / len(pages) >= 0.8
    notes: list[str] = []
    if empty_numbers:
        listed = ", ".join(str(number) for number in empty_numbers[:40])
        notes.append(
            f"No extractable text on pages {listed}. Those pages were kept in the page list and were not indexed. "
            "OCR is not enabled, so a scanned page cannot be searched."
        )
    if likely_scanned:
        notes.append("Most pages have no extractable text. This PDF may be scanned.")
    if not notes:
        return None, likely_scanned, indexed
    return " ".join(notes)[:2000], likely_scanned, indexed


def accept_upload(
    db: Session,
    settings: Settings,
    *,
    filename: str | None,
    content_type: str | None,
    data: bytes,
    jurisdiction: str | None,
    synthetic: bool = False,
) -> Document:
    from app.services.files import display_name, sha256_bytes, validate_pdf
    from app.services.settings_store import load_runtime

    runtime = load_runtime(db, settings)
    page_count = validate_pdf(
        filename,
        content_type,
        data,
        runtime.max_upload_mb * 1024 * 1024,
        runtime.max_pages,
    )
    digest = sha256_bytes(data)
    existing = db.scalar(select(Document).where(Document.sha256 == digest))
    if existing is not None:
        raise FileRejected(
            f"A document with the same content already exists ({existing.id}).",
            409,
        )
    document_id = str(uuid.uuid4())
    path = storage_path(settings.data_dir, document_id)
    path.write_bytes(data)
    supplied = (jurisdiction or "").strip() or None
    document = Document(
        id=document_id,
        filename=display_name(filename),
        sha256=digest,
        size_bytes=len(data),
        page_count=page_count,
        mime_type="application/pdf",
        status="pending",
        index_status="pending",
        jurisdiction=supplied[:160] if supplied else None,
        synthetic=synthetic,
        likely_scanned=False,
        uploaded_at=utcnow(),
    )
    db.add(document)
    db.commit()
    return document


def delete_document_data(db: Session, settings: Settings, document: Document) -> None:
    from sqlalchemy.orm.attributes import flag_modified

    from app.models import ResearchSession

    path = storage_path(settings.data_dir, document.id)
    if path.exists():
        path.unlink()
    db.execute(delete(Chunk).where(Chunk.document_id == document.id))
    db.execute(delete(Page).where(Page.document_id == document.id))
    sessions = db.scalars(select(ResearchSession)).all()
    for session in sessions:
        if document.id in (session.document_ids or []):
            session.document_ids = [item for item in session.document_ids if item != document.id]
            flag_modified(session, "document_ids")
    db.delete(document)
    db.commit()
