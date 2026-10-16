import hashlib
import re
from dataclasses import dataclass

import httpx
import numpy as np

_TOKEN = re.compile(r"[a-z0-9]+")


class EmbedderError(RuntimeError):
    pass


@dataclass
class EmbedderInfo:
    embedder: "Embedder"
    notice: str


class Embedder:
    name: str
    dim: int

    def embed(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError


class HashEmbedder(Embedder):
    """Deterministic feature hashing. This is not a neural semantic model."""

    def __init__(self, dim: int = 384) -> None:
        self.name = "deterministic-hash-v1"
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for token in _TOKEN.findall((text or "").lower()):
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                bucket = int.from_bytes(digest[:4], "little") % self.dim
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vectors[row, bucket] += sign
            norm = float(np.linalg.norm(vectors[row]))
            if norm > 0:
                vectors[row] /= norm
        return vectors


class OllamaEmbedder(Embedder):
    def __init__(self, base_url: str, model: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.name = f"ollama:{model}"
        probe = self.embed(["citewise embedding probe"])
        self.dim = int(probe.shape[1])

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, getattr(self, "dim", 0)), dtype=np.float32)
        rows: list[np.ndarray] = []
        for start in range(0, len(texts), 16):
            batch = texts[start : start + 16]
            try:
                response = httpx.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": batch},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPError as exc:
                raise EmbedderError(
                    f"Ollama embeddings are unavailable ({type(exc).__name__})"
                ) from exc
            vectors = payload.get("embeddings")
            if not isinstance(vectors, list) or len(vectors) != len(batch):
                raise EmbedderError("Ollama returned an unexpected embedding payload")
            rows.append(np.asarray(vectors, dtype=np.float32))
        stacked = np.vstack(rows)
        norms = np.linalg.norm(stacked, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return stacked / norms


class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbedderError(
                "sentence-transformers is not installed. Install the semantic extra: "
                'pip install -e ".[semantic]"'
            ) from exc
        try:
            self._model = SentenceTransformer(model_name)
        except Exception as exc:
            raise EmbedderError(
                f"Could not load embedding model {model_name} ({type(exc).__name__})"
            ) from exc
        self.name = model_name
        self.dim = int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vectors = self._model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)


def _ollama_reachable(base_url: str) -> bool:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/api/version", timeout=1.5)
        return response.status_code < 500
    except httpx.HTTPError:
        return False


def resolve_embedder(
    backend: str,
    embedding_model: str,
    ollama_base_url: str,
    ollama_embed_model: str,
) -> EmbedderInfo:
    if backend == "hash":
        return EmbedderInfo(HashEmbedder(), "")
    if backend == "sentence-transformers":
        return EmbedderInfo(SentenceTransformerEmbedder(embedding_model), "")
    if backend == "ollama":
        return EmbedderInfo(OllamaEmbedder(ollama_base_url, ollama_embed_model), "")

    notices: list[str] = []
    try:
        import sentence_transformers  # noqa: F401

        try:
            embedder = SentenceTransformerEmbedder(embedding_model)
            return EmbedderInfo(embedder, "Using a local sentence-transformers model.")
        except EmbedderError as exc:
            notices.append(str(exc))
    except ImportError:
        notices.append("sentence-transformers is not installed.")

    if _ollama_reachable(ollama_base_url):
        try:
            embedder = OllamaEmbedder(ollama_base_url, ollama_embed_model)
            notices.append(f"Using local Ollama embeddings ({ollama_embed_model}).")
            return EmbedderInfo(embedder, " ".join(notices))
        except EmbedderError as exc:
            notices.append(str(exc))
    else:
        notices.append("Ollama embeddings are not reachable.")

    notices.append(
        "Semantic embeddings are unavailable. Keyword search is active with deterministic hashing, "
        "which is not a neural model."
    )
    return EmbedderInfo(HashEmbedder(), " ".join(notices))
