"""Score the synthetic development corpus.

This is not a legal benchmark. The default ranker is keyword-only so the
result does not depend on a downloaded embedding model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.embeddings import HashEmbedder  # noqa: E402
from app.services.metrics import mean, ndcg_at_k, recall_at_k, reciprocal_rank  # noqa: E402
from app.services.retrieval import rank_corpus  # noqa: E402


def main() -> None:
    corpus_path = ROOT / "tests" / "eval_corpus.json"
    payload = json.loads(corpus_path.read_text(encoding="utf-8"))
    corpus = [(item["id"], item["text"]) for item in payload["passages"]]
    rows = []
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
        ids = [hit.item_id for hit in ranked]
        relevant = set(item["relevant"])
        rows.append(
            {
                "id": item.get("id") or item["query"],
                "recall_at_5": recall_at_k(ids, relevant, 5),
                "mrr": reciprocal_rank(ids, relevant),
                "ndcg_at_5": ndcg_at_k(ids, relevant, 5),
            }
        )
    print(
        json.dumps(
            {
                "label": payload.get("label"),
                "ranker": "bm25",
                "embedder": "hash",
                "mean_recall_at_5": mean([row["recall_at_5"] for row in rows]),
                "mrr": mean([row["mrr"] for row in rows]),
                "mean_ndcg_at_5": mean([row["ndcg_at_5"] for row in rows]),
                "queries": rows,
                "note": "Development fixture only. Not a legal-retrieval benchmark.",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
