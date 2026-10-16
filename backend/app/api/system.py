from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_index, get_settings
from app.config import Settings
from app.schemas import (
    HealthResponse,
    ModelCheckRequest,
    ModelStatus,
    RetentionResult,
    SettingsResponse,
    StoredSettings,
)
from app.services.index_store import IndexStore
from app.services.model_status import describe_models
from app.services.settings_store import load_runtime, save_runtime

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> HealthResponse:
    database = "ok"
    try:
        db.connection()
    except Exception:
        database = "error"
    runtime = load_runtime(db, settings) if database == "ok" else StoredSettings()
    return HealthResponse(
        status="ok" if database == "ok" else "error",
        version=settings.version,
        database=database,  # type: ignore[arg-type]
        inference=describe_models(runtime),
    )


@router.get("/models", response_model=ModelStatus)
def models(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> ModelStatus:
    return describe_models(load_runtime(db, settings))


@router.post("/models/check", response_model=ModelStatus)
def check_models(
    body: ModelCheckRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ModelStatus:
    runtime = load_runtime(db, settings)
    return describe_models(runtime, body.ollama_base_url, body.ollama_model)


@router.get("/settings", response_model=SettingsResponse)
def get_settings_route(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    index_store: IndexStore = Depends(get_index),
) -> SettingsResponse:
    runtime = load_runtime(db, settings)
    status = describe_models(runtime)
    return SettingsResponse(
        **runtime.model_dump(),
        embedding_active=index_store.embedder.name if index_store.embedder else "not-built",
        embedding_notice=index_store.embedding_notice,
        inference_mode=status.inference_mode,
        inference_detail=status.detail,
        data_dir=str(settings.data_dir),
    )


@router.put("/settings", response_model=SettingsResponse)
def update_settings(
    body: StoredSettings,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    index_store: IndexStore = Depends(get_index),
) -> SettingsResponse:
    current = load_runtime(db, settings)
    save_runtime(db, body)
    reindex = (
        current.chunk_size != body.chunk_size
        or current.chunk_overlap != body.chunk_overlap
        or current.embedding_backend != body.embedding_backend
        or current.embedding_model != body.embedding_model
        or current.ollama_embed_model != body.ollama_embed_model
        or current.ollama_base_url != body.ollama_base_url
    )
    status = describe_models(body)
    return SettingsResponse(
        **body.model_dump(),
        embedding_active=index_store.embedder.name if index_store.embedder else "not-built",
        embedding_notice=index_store.embedding_notice,
        inference_mode=status.inference_mode,
        inference_detail=status.detail,
        data_dir=str(settings.data_dir),
        reindex_required=reindex,
    )


@router.post("/settings/apply-retention", response_model=RetentionResult)
def apply_retention(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RetentionResult:
    from datetime import timedelta

    from sqlalchemy import select

    from app.models import Document
    from app.services.ingestion import delete_document_data
    from app.services.settings_store import utcnow

    runtime = load_runtime(db, settings)
    if runtime.retention_days is None:
        return RetentionResult(deleted_document_ids=[], retention_days=None)
    cutoff = utcnow() - timedelta(days=runtime.retention_days)
    documents = list(db.scalars(select(Document).where(Document.uploaded_at < cutoff)).all())
    deleted = []
    for document in documents:
        deleted.append(document.id)
        delete_document_data(db, settings, document)
    if deleted:
        request.app.state.index_store.rebuild(db, runtime)
    return RetentionResult(deleted_document_ids=deleted, retention_days=runtime.retention_days)
