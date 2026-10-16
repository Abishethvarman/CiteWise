import math
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from app.services.embeddings import Embedder
from app.services.normalize import word_tokens

BM25_SATURATION = 1.5


class SmallCorpusBM25(BM25Okapi):
    """BM25Okapi with Lucene's IDF.

    rank-bm25 uses log((N - df + 0.5) / (df + 0.5)). On a two-passage
    collection that value is zero for a term that appears in one passage,
    so a keyword match contributes nothing. Lucene's form stays positive.
    """

    def _calc_idf(self, nd):
        for word, freq in nd.items():
            self.idf[word] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))
        self.average_idf = sum(self.idf.values()) / len(self.idf) if self.idf else 0.0


@dataclass
class RankedItem:
    item_id: str
    text: str
    score: float
    bm25_score: float
    semantic_score: float


def _bm25_norm(score: float) -> float:
    if score <= 0:
        return 0.0
    return score / (score + BM25_SATURATION)


def _cosine_norm(score: float) -> float:
    return max(0.0, min(1.0, score))


def rank_corpus(
    query: str,
    corpus: list[tuple[str, str]],
    embedder: Embedder,
    *,
    top_k: int,
    bm25_weight: float,
    semantic_weight: float,
    score_threshold: float,
    lexical_rerank: bool = False,
    semantic_scores: dict[str, float] | None = None,
) -> list[RankedItem]:
    """Rank (id, text) pairs. Scores are fused retrieval scores, not probabilities."""
    if top_k < 1 or not corpus:
        return []
    query_tokens = word_tokens(query)
    if not query_tokens and semantic_weight <= 0:
        return []

    ids = [item_id for item_id, _text in corpus]
    texts = [text for _item_id, text in corpus]
    tokenized = [word_tokens(text) or ["empty"] for text in texts]

    bm25_raw = {item_id: 0.0 for item_id in ids}
    if query_tokens and bm25_weight > 0:
        model = SmallCorpusBM25(tokenized)
        for item_id, score in zip(ids, model.get_scores(query_tokens), strict=True):
            bm25_raw[item_id] = float(score)

    semantic_raw = {item_id: 0.0 for item_id in ids}
    if semantic_scores is not None:
        for item_id in ids:
            semantic_raw[item_id] = float(semantic_scores.get(item_id, 0.0))
    elif semantic_weight > 0 and texts:
        query_vector = embedder.embed([query])
        document_vectors = embedder.embed(texts)
        if query_vector.size and document_vectors.size:
            scores = document_vectors @ query_vector[0]
            for item_id, score in zip(ids, scores, strict=True):
                semantic_raw[item_id] = float(score)

    weight_sum = bm25_weight + semantic_weight
    if weight_sum <= 0:
        bm25_weight, semantic_weight, weight_sum = 0.5, 0.5, 1.0

    ranked: list[RankedItem] = []
    seen: set[str] = set()
    for item_id, text in corpus:
        fingerprint = " ".join(word_tokens(text)[:80])
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        bm25_score = _bm25_norm(bm25_raw[item_id])
        semantic_score = _cosine_norm(semantic_raw[item_id])
        fused = (bm25_weight * bm25_score + semantic_weight * semantic_score) / weight_sum
        if lexical_rerank and query_tokens:
            chunk_tokens = set(word_tokens(text))
            overlap = len(set(query_tokens) & chunk_tokens) / len(set(query_tokens))
            fused = min(1.0, fused * (0.75 + 0.25 * overlap))
        if fused < score_threshold:
            continue
        ranked.append(
            RankedItem(
                item_id=item_id,
                text=text,
                score=fused,
                bm25_score=bm25_score,
                semantic_score=semantic_score,
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[:top_k]
