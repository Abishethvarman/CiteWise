from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Chunk, Document, Page
from app.schemas import DocumentDetail, DocumentSummary, PagePreview


def chunk_count(db: Session, document_id: str) -> int:
    value = db.scalar(
        select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
    )
    return int(value or 0)


def to_summary(db: Session, document: Document) -> DocumentSummary:
    return DocumentSummary(
        id=document.id,
        filename=document.filename,
        size_bytes=document.size_bytes,
        page_count=document.page_count,
        mime_type=document.mime_type,
        status=document.status,
        index_status=document.index_status,
        error_message=document.error_message,
        extraction_notes=document.extraction_notes,
        jurisdiction=document.jurisdiction,
        jurisdiction_source="user_supplied" if document.jurisdiction else "not_specified",
        synthetic=document.synthetic,
        likely_scanned=document.likely_scanned,
        uploaded_at=document.uploaded_at,
        processed_at=document.processed_at,
        chunk_count=chunk_count(db, document.id),
        sha256=document.sha256,
    )


def to_detail(db: Session, document: Document) -> DocumentDetail:
    pages = db.scalars(
        select(Page).where(Page.document_id == document.id).order_by(Page.page_number)
    ).all()
    previews = [
        PagePreview(
            page_number=page.page_number,
            char_count=page.char_count,
            is_empty=page.is_empty,
            preview=(page.text[:280] if page.text else ""),
        )
        for page in pages
    ]
    summary = to_summary(db, document)
    return DocumentDetail(**summary.model_dump(), pages=previews)
