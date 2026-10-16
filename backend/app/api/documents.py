from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_index, get_settings
from app.config import Settings
from app.demo import seed_demo
from app.models import Document, Page
from app.schemas import DemoSeedResult, DocumentDetail, DocumentSummary, PageText
from app.services.files import UUID_RE, FileRejected, storage_path
from app.services.index_store import IndexStore
from app.services.ingestion import accept_upload, delete_document_data, ingest_document
from app.services.present import to_detail, to_summary
from app.services.settings_store import load_runtime

router = APIRouter()
_SORTS = {
    "uploaded_at": Document.uploaded_at,
    "filename": Document.filename,
    "size_bytes": Document.size_bytes,
    "page_count": Document.page_count,
}


def _schedule(background: BackgroundTasks, request: Request, func, *args) -> None:
    if getattr(request.app.state, "inline_jobs", False):
        func(*args)
    else:
        background.add_task(func, *args)


def _ingest_job(
    session_factory, settings: Settings, index_store: IndexStore, document_id: str
) -> None:
    db = session_factory()
    try:
        ingest_document(db, settings, index_store, document_id)
    finally:
        db.close()


def _document_or_404(db: Session, document_id: str) -> Document:
    if not UUID_RE.fullmatch(document_id or ""):
        raise HTTPException(status_code=422, detail="Invalid document id")
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post("", response_model=DocumentSummary, status_code=201)
async def upload_document(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    jurisdiction: str | None = Form(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DocumentSummary:
    data = await file.read()
    try:
        document = accept_upload(
            db,
            settings,
            filename=file.filename,
            content_type=file.content_type,
            data=data,
            jurisdiction=jurisdiction,
        )
    except FileRejected as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    _schedule(
        background,
        request,
        _ingest_job,
        request.app.state.session_factory,
        settings,
        request.app.state.index_store,
        document.id,
    )
    if getattr(request.app.state, "inline_jobs", False):
        db.expire_all()
        document = db.get(Document, document.id) or document
    return to_summary(db, document)


@router.get("", response_model=list[DocumentSummary])
def list_documents(
    q: str | None = None,
    status: str | None = None,
    sort: str = "uploaded_at",
    order: str = "desc",
    db: Session = Depends(get_db),
) -> list[DocumentSummary]:
    column = _SORTS.get(sort, Document.uploaded_at)
    direction = asc if order == "asc" else desc
    stmt = select(Document).order_by(direction(column)).limit(500)
    if q:
        stmt = stmt.where(Document.filename.contains(q))
    if status:
        stmt = stmt.where(Document.status == status)
    return [to_summary(db, document) for document in db.scalars(stmt).all()]


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, db: Session = Depends(get_db)) -> DocumentDetail:
    return to_detail(db, _document_or_404(db, document_id))


@router.get("/{document_id}/pages/{page_number}", response_model=PageText)
def get_page(document_id: str, page_number: int, db: Session = Depends(get_db)) -> PageText:
    document = _document_or_404(db, document_id)
    page = db.scalar(
        select(Page).where(Page.document_id == document.id, Page.page_number == page_number)
    )
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return PageText(
        document_id=document.id,
        filename=document.filename,
        page_number=page.page_number,
        text=page.text,
        is_empty=page.is_empty,
        char_count=page.char_count,
    )


@router.get("/{document_id}/file")
def get_file(
    document_id: str, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    document = _document_or_404(db, document_id)
    path = storage_path(settings.data_dir, document.id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file not found")
    return FileResponse(path, media_type="application/pdf", filename=document.filename)


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: str,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    document = _document_or_404(db, document_id)
    delete_document_data(db, settings, document)
    request.app.state.index_store.rebuild(db, load_runtime(db, settings))


@router.post("/{document_id}/reindex", response_model=DocumentSummary)
def reindex_document(
    document_id: str,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DocumentSummary:
    document = _document_or_404(db, document_id)
    document.status = "pending"
    document.index_status = "pending"
    document.error_message = None
    db.commit()
    _schedule(
        background,
        request,
        _ingest_job,
        request.app.state.session_factory,
        settings,
        request.app.state.index_store,
        document.id,
    )
    if getattr(request.app.state, "inline_jobs", False):
        db.expire_all()
        document = db.get(Document, document.id) or document
    return to_summary(db, document)


@router.post("/demo/seed", response_model=DemoSeedResult)
def seed_demo_route(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    index_store: IndexStore = Depends(get_index),
) -> DemoSeedResult:
    documents, created, present = seed_demo(db, settings, index_store)
    return DemoSeedResult(
        documents=[to_summary(db, document) for document in documents],
        created=created,
        already_present=present,
    )
