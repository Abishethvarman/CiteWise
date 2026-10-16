from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AppSetting
from app.schemas import StoredSettings


def utcnow() -> datetime:
    return datetime.now(UTC)


def runtime_from_env(settings: Settings) -> StoredSettings:
    return StoredSettings(
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        embedding_backend=settings.embedding_backend,  # type: ignore[arg-type]
        embedding_model=settings.embedding_model,
        ollama_embed_model=settings.ollama_embed_model,
        top_k=settings.top_k,
        bm25_weight=settings.bm25_weight,
        semantic_weight=settings.semantic_weight,
        score_threshold=settings.score_threshold,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        max_upload_mb=settings.max_upload_mb,
        max_pages=settings.max_pages,
        retention_days=settings.retention_days,
        lexical_rerank=settings.lexical_rerank,
        llm_timeout_seconds=settings.llm_timeout_seconds,
        prompt_passage_tokens=settings.prompt_passage_tokens,
        local_processing_only=True,
    )


def load_runtime(db: Session, settings: Settings) -> StoredSettings:
    row = db.get(AppSetting, 1)
    if row is None:
        runtime = runtime_from_env(settings)
        db.add(AppSetting(id=1, payload=runtime.model_dump(), updated_at=utcnow()))
        db.commit()
        return runtime
    return StoredSettings.model_validate(row.payload)


def save_runtime(db: Session, runtime: StoredSettings) -> StoredSettings:
    row = db.get(AppSetting, 1)
    payload = runtime.model_dump()
    if row is None:
        db.add(AppSetting(id=1, payload=payload, updated_at=utcnow()))
    else:
        row.payload = payload
        row.updated_at = utcnow()
    db.commit()
    return runtime
