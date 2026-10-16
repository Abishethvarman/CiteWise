import json
import threading
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Chunk, Document
from app.schemas import StoredSettings
from app.services.embeddings import Embedder, EmbedderInfo, resolve_embedder
from app.services.retrieval import RankedItem, rank_corpus


@dataclass
class IndexedChunk:
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    text: str


class IndexStore:
    def __init__(self, index_dir: Path) -> None:
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.chunks: list[IndexedChunk] = []
        self.embedder: Embedder | None = None
        self.embedding_notice = ""
        self._index = None
        self._manifest_path = self.index_dir / "manifest.json"
        self._faiss_path = self.index_dir / "passages.faiss"

    def rebuild(self, db: Session, runtime: StoredSettings) -> None:
        with self._lock:
            rows = db.execute(
                select(Chunk, Document)
                .join(Document, Document.id == Chunk.document_id)
                .where(Document.status == "ready", Chunk.text != "")
                .order_by(Document.uploaded_at, Chunk.page_number, Chunk.chunk_index)
            ).all()
            self.chunks = [
                IndexedChunk(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    document_name=document.filename,
                    page_number=chunk.page_number,
                    text=chunk.text,
                )
                for chunk, document in rows
            ]
            info = self._embedder_for(runtime)
            self.embedder = info.embedder
            self.embedding_notice = info.notice
            self._persist_vectors()

    def _embedder_for(self, runtime: StoredSettings) -> EmbedderInfo:
        if (
            self.embedder is not None
            and self._manifest_matches_backend(runtime)
            and self.embedder.name
        ):
            # A new backend choice still needs a fresh embedder. Always resolve.
            pass
        return resolve_embedder(
            runtime.embedding_backend,
            runtime.embedding_model,
            runtime.ollama_base_url,
            runtime.ollama_embed_model,
        )

    def _manifest_matches_backend(self, runtime: StoredSettings) -> bool:
        if not self._manifest_path.exists():
            return False
        try:
            payload = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        return payload.get("backend") == runtime.embedding_backend

    def _persist_vectors(self) -> None:
        assert self.embedder is not None
        texts = [chunk.text for chunk in self.chunks]
        vectors = (
            self.embedder.embed(texts)
            if texts
            else np.zeros((0, self.embedder.dim), dtype=np.float32)
        )
        if vectors.ndim != 2:
            vectors = np.zeros((0, self.embedder.dim), dtype=np.float32)
        dim = int(vectors.shape[1]) if vectors.shape[0] else self.embedder.dim
        index = faiss.IndexFlatIP(dim)
        if vectors.shape[0]:
            index.add(np.ascontiguousarray(vectors.astype(np.float32)))
        self._index = index
        faiss.write_index(index, str(self._faiss_path))
        manifest = {
            "embedder": self.embedder.name,
            "backend_notice": self.embedding_notice,
            "dim": dim,
            "chunk_ids": [chunk.chunk_id for chunk in self.chunks],
        }
        self._manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def search(
        self,
        query: str,
        runtime: StoredSettings,
        document_ids: list[str] | None,
        top_k: int | None = None,
    ) -> list[tuple[IndexedChunk, RankedItem]]:
        with self._lock:
            if self.embedder is None:
                return []
            allowed = set(document_ids or [])
            chosen = [chunk for chunk in self.chunks if not allowed or chunk.document_id in allowed]
            if not chosen:
                return []
            semantic_scores = self._semantic_scores(query, chosen)
            corpus = [(chunk.chunk_id, chunk.text) for chunk in chosen]
            ranked = rank_corpus(
                query,
                corpus,
                self.embedder,
                top_k=top_k or runtime.top_k,
                bm25_weight=runtime.bm25_weight,
                semantic_weight=runtime.semantic_weight,
                score_threshold=runtime.score_threshold,
                lexical_rerank=runtime.lexical_rerank,
                semantic_scores=semantic_scores,
            )
            by_id = {chunk.chunk_id: chunk for chunk in chosen}
            return [(by_id[item.item_id], item) for item in ranked if item.item_id in by_id]

    def _semantic_scores(self, query: str, chosen: list[IndexedChunk]) -> dict[str, float]:
        scores = {chunk.chunk_id: 0.0 for chunk in chosen}
        if self.embedder is None or self._index is None or self._index.ntotal == 0:
            return scores
        query_vector = self.embedder.embed([query])
        if query_vector.size == 0:
            return scores
        neighbor_count = min(40, int(self._index.ntotal))
        found_scores, found_ids = self._index.search(
            np.ascontiguousarray(query_vector.astype(np.float32)),
            neighbor_count,
        )
        allowed = set(scores)
        for score, position in zip(found_scores[0], found_ids[0], strict=True):
            if int(position) < 0 or int(position) >= len(self.chunks):
                continue
            chunk_id = self.chunks[int(position)].chunk_id
            if chunk_id in allowed:
                scores[chunk_id] = float(score)
        return scores
