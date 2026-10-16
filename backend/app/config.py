from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DATABASE_URL = "sqlite:///./data/citewise.db"


class Settings(BaseSettings):
    """Process configuration. User-facing overrides live in the database."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_prefix="CITEWISE_",
        extra="ignore",
    )

    app_name: str = "CiteWise"
    version: str = "0.1.0"
    data_dir: Path = Path("./data")
    database_url: str = DEFAULT_DATABASE_URL
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:3b"
    embedding_backend: str = "auto"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ollama_embed_model: str = "nomic-embed-text"
    chunk_size: int = 700
    chunk_overlap: int = 100
    top_k: int = 4
    bm25_weight: float = 0.45
    semantic_weight: float = 0.55
    score_threshold: float = 0.2
    max_upload_mb: int = 25
    max_pages: int = 200
    llm_timeout_seconds: float = 120.0
    lexical_rerank: bool = False
    retention_days: int | None = None
    log_level: str = "INFO"
    prompt_passage_tokens: int = 280

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def model_post_init(self, __context: object) -> None:
        data_dir = Path(self.data_dir).expanduser().resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "uploads").mkdir(exist_ok=True)
        (data_dir / "indexes").mkdir(exist_ok=True)
        database_url = self.database_url
        if database_url in {DEFAULT_DATABASE_URL, ""}:
            database_url = "sqlite:///" + (data_dir / "citewise.db").as_posix()
        object.__setattr__(self, "data_dir", data_dir)
        object.__setattr__(self, "database_url", database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
