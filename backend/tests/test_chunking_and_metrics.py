from app.services.chunking import chunk_id_for, chunk_text
from app.services.metrics import mean, ndcg_at_k, recall_at_k, reciprocal_rank


def test_chunking_preserves_page_offsets_and_overlap():
    text = " ".join(f"token{i}" for i in range(80))
    first = chunk_text(text, chunk_size=30, overlap=10)
    second = chunk_text(text, chunk_size=30, overlap=10)
    assert len(first) >= 3
    assert [chunk.text for chunk in first] == [chunk.text for chunk in second]
    assert first[0].start_offset == 0
    assert first[0].token_count == 30
    overlap_tokens = first[0].text.split()[-10:]
    assert first[1].text.split()[:10] == overlap_tokens
    assert first[0].end_offset > first[0].start_offset


def test_chunk_ids_are_stable():
    left = chunk_id_for("doc", 2, 1, 40)
    right = chunk_id_for("doc", 2, 1, 40)
    other = chunk_id_for("doc", 3, 1, 40)
    assert left == right
    assert left != other


def test_paragraph_boundary_is_preferred():
    paragraph = " ".join(f"alpha{i}" for i in range(20))
    text = paragraph + "\n\n" + " ".join(f"beta{i}" for i in range(20))
    chunks = chunk_text(text, chunk_size=25, overlap=0)
    assert chunks[0].text.endswith("alpha19")
    assert "beta0" not in chunks[0].text


def test_metric_helpers_on_a_known_ranking():
    ranked = ["b", "a", "c"]
    relevant = {"a", "c"}
    assert recall_at_k(ranked, relevant, 1) == 0
    assert recall_at_k(ranked, relevant, 3) == 1
    assert reciprocal_rank(ranked, relevant) == 0.5
    assert ndcg_at_k(ranked, relevant, 3) > 0.5
    assert mean([1, 3]) == 2
