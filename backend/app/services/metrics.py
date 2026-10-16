import math


def recall_at_k(ranked_ids: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    found = set(ranked_ids[:k]) & relevant
    return len(found) / len(relevant)


def reciprocal_rank(ranked_ids: list[str], relevant: set[str]) -> float:
    for index, item_id in enumerate(ranked_ids, start=1):
        if item_id in relevant:
            return 1.0 / index
    return 0.0


def _dcg(relevances: list[int]) -> float:
    total = 0.0
    for index, relevance in enumerate(relevances):
        total += relevance / math.log2(index + 2)
    return total


def ndcg_at_k(ranked_ids: list[str], relevant: set[str], k: int) -> float:
    if not relevant or k < 1:
        return 0.0
    gains = [1 if item_id in relevant else 0 for item_id in ranked_ids[:k]]
    ideal_hits = min(k, len(relevant))
    ideal = [1] * ideal_hits + [0] * max(0, k - ideal_hits)
    ideal_dcg = _dcg(ideal[:k])
    if ideal_dcg == 0:
        return 0.0
    return _dcg(gains) / ideal_dcg


def mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)
