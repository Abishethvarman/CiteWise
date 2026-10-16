from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EmbeddingBackend = Literal["auto", "sentence-transformers", "ollama", "hash"]
SupportStatus = Literal[
    "insufficient",
    "supported",
    "partial",
    "unsupported",
    "model_unavailable",
    "invalid_model_output",
]
EvidenceStatus = Literal["source_matched", "partial_match", "unresolved"]
ClaimSupport = Literal["supported", "partial", "unsupported"]
InferenceMode = Literal["local_ollama", "model_missing", "unavailable"]


class StoredSettings(BaseModel):
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:3b"
    embedding_backend: EmbeddingBackend = "auto"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ollama_embed_model: str = "nomic-embed-text"
    top_k: int = Field(default=4, ge=1, le=20)
    bm25_weight: float = Field(default=0.45, ge=0, le=1)
    semantic_weight: float = Field(default=0.55, ge=0, le=1)
    score_threshold: float = Field(default=0.2, ge=0, le=1)
    chunk_size: int = Field(default=700, ge=50, le=2000)
    chunk_overlap: int = Field(default=100, ge=0, le=500)
    max_upload_mb: int = Field(default=25, ge=1, le=100)
    max_pages: int = Field(default=200, ge=1, le=2000)
    retention_days: int | None = Field(default=None, ge=1, le=3650)
    lexical_rerank: bool = False
    llm_timeout_seconds: float = Field(default=120, ge=5, le=600)
    prompt_passage_tokens: int = Field(default=280, ge=40, le=800)
    local_processing_only: Literal[True] = True

    @field_validator("ollama_base_url", "ollama_model", "embedding_model", "ollama_embed_model")
    @classmethod
    def strip_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("This value cannot be empty")
        return text

    @field_validator("local_processing_only")
    @classmethod
    def local_only(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError(
                "External model providers are disabled. CiteWise only talks to the configured local endpoint."
            )
        return True

    @model_validator(mode="after")
    def check_ranges(self) -> "StoredSettings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be smaller than chunk size")
        if self.bm25_weight == 0 and self.semantic_weight == 0:
            raise ValueError("At least one retrieval weight must be greater than zero")
        if not self.ollama_base_url.startswith(("http://", "https://")):
            raise ValueError("Model endpoint must start with http:// or https://")
        return self


class SettingsResponse(StoredSettings):
    embedding_active: str
    embedding_notice: str
    inference_mode: InferenceMode
    inference_detail: str
    external_providers_enabled: Literal[False] = False
    data_dir: str
    reindex_required: bool = False


class ModelInfo(BaseModel):
    name: str
    size: int | None = None
    modified_at: str | None = None


class ModelCheckRequest(BaseModel):
    ollama_base_url: str | None = None
    ollama_model: str | None = None


class ModelStatus(BaseModel):
    reachable: bool
    inference_mode: InferenceMode
    detail: str
    selected_model: str
    selected_model_installed: bool
    models: list[ModelInfo] = []
    external_providers_enabled: Literal[False] = False
    provider: Literal["ollama"] = "ollama"


class HealthResponse(BaseModel):
    status: Literal["ok", "error"]
    version: str
    database: Literal["ok", "error"]
    inference: ModelStatus
    external_providers_enabled: Literal[False] = False


class PagePreview(BaseModel):
    page_number: int
    char_count: int
    is_empty: bool
    preview: str


class DocumentSummary(BaseModel):
    id: str
    filename: str
    size_bytes: int
    page_count: int
    mime_type: str
    status: str
    index_status: str
    error_message: str | None
    extraction_notes: str | None
    jurisdiction: str | None
    jurisdiction_source: Literal["user_supplied", "not_specified"]
    synthetic: bool
    likely_scanned: bool
    uploaded_at: datetime
    processed_at: datetime | None
    chunk_count: int
    sha256: str


class DocumentDetail(DocumentSummary):
    pages: list[PagePreview]


class PageText(BaseModel):
    document_id: str
    filename: str
    page_number: int
    text: str
    is_empty: bool
    char_count: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    document_ids: list[str] = []
    top_k: int | None = Field(default=None, ge=1, le=20)


class PassageHit(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    text: str
    score: float
    bm25_score: float
    semantic_score: float


class SearchResponse(BaseModel):
    query: str
    passages: list[PassageHit]
    embedding_active: str
    embedding_notice: str
    retrieval: dict


class EvidenceIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    chunk_id: str = ""
    quotation: str = ""


class ClaimIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    text: str = ""
    chunk_ids: list[str] = []


class AnswerDraft(BaseModel):
    """Structured output required from the local model. Extra keys are ignored."""

    model_config = ConfigDict(extra="ignore")
    answer: str = ""
    claims: list[ClaimIn] = []
    evidence: list[EvidenceIn] = []
    limitations: list[str] = []
    insufficient_evidence: bool = False


class VerifiedEvidence(BaseModel):
    chunk_id: str
    quotation: str
    document_id: str | None = None
    document_name: str | None = None
    page_number: int | None = None
    source_passage: str | None = None
    status: EvidenceStatus
    supplied_to_model: bool
    chunk_exists: bool
    page_exists: bool
    notes: list[str]


class ClaimOut(BaseModel):
    text: str
    chunk_ids: list[str]
    support: ClaimSupport


class AnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_ids: list[str] = []
    session_id: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)


class AnswerResponse(BaseModel):
    turn_id: str
    session_id: str
    question: str
    answer: str
    claims: list[ClaimOut]
    evidence: list[VerifiedEvidence]
    limitations: list[str]
    insufficient_evidence: bool
    support_status: SupportStatus
    has_unresolved_citations: bool
    model_metadata: dict
    retrieved: list[PassageHit]
    embedding_notice: str


class SessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    document_ids: list[str] = []


class SessionSummary(BaseModel):
    id: str
    title: str
    document_ids: list[str]
    created_at: datetime
    updated_at: datetime
    turn_count: int


class TurnSummary(BaseModel):
    id: str
    question: str
    created_at: datetime
    support_status: str
    model_name: str | None = None
    insufficient_evidence: bool


class SessionDetail(SessionSummary):
    turns: list[TurnSummary]


class VerifyRequest(BaseModel):
    turn_id: str | None = None
    evidence: list[EvidenceIn] | None = None
    supplied_chunk_ids: list[str] | None = None


class VerifyResponse(BaseModel):
    turn_id: str | None
    evidence: list[VerifiedEvidence]
    has_unresolved_citations: bool
    support_status: SupportStatus
    limitations: list[str]
    note: str


class RetentionResult(BaseModel):
    deleted_document_ids: list[str]
    retention_days: int | None


class DemoSeedResult(BaseModel):
    documents: list[DocumentSummary]
    created: int
    already_present: int
