import json
from pathlib import Path

from app.services.embeddings import HashEmbedder
from app.services.metrics import mean, recall_at_k
from app.services.retrieval import rank_corpus

ROOT = Path(__file__).resolve().parents[2]


def test_development_corpus_keyword_recall():
    payload = json.loads((ROOT / "tests" / "eval_corpus.json").read_text(encoding="utf-8"))
    assert "Not a legal benchmark" in payload["label"]
    corpus = [(item["id"], item["text"]) for item in payload["passages"]]
    recalls = []
    for item in payload["queries"]:
        ranked = rank_corpus(
            item["query"],
            corpus,
            HashEmbedder(),
            top_k=5,
            bm25_weight=1,
            semantic_weight=0,
            score_threshold=0,
        )
        recalls.append(recall_at_k([hit.item_id for hit in ranked], set(item["relevant"]), 5))
    assert mean(recalls) == 1
