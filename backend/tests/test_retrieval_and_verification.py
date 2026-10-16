from app.services.embeddings import HashEmbedder
from app.services.normalize import quotation_match
from app.services.retrieval import rank_corpus


def test_hash_embedder_prefers_shared_tokens():
    embedder = HashEmbedder()
    related = embedder.embed(["oak timber delivery delay"])[0]
    query = embedder.embed(["oak timber delivery"])[0]
    unrelated = embedder.embed(["fishing licence renewal forms"])[0]
    assert float(related @ query) > float(unrelated @ query)


def test_hybrid_rank_places_keyword_passage_first():
    corpus = [
        ("a", "Northwind delivered oak timber twelve days after the contractual date."),
        ("b", "A business record may be admitted when the witness is unavailable."),
        ("c", "The lease prohibited subletting without prior written consent."),
    ]
    ranked = rank_corpus(
        "oak timber contractual date",
        corpus,
        HashEmbedder(),
        top_k=3,
        bm25_weight=0.45,
        semantic_weight=0.55,
        score_threshold=0.05,
    )
    assert ranked
    assert ranked[0].item_id == "a"


def test_zero_keyword_score_stays_below_threshold():
    corpus = [("a", "Northwind delivered oak timber twelve days late.")]
    ranked = rank_corpus(
        "cryptocurrency wallet custody rules",
        corpus,
        HashEmbedder(),
        top_k=3,
        bm25_weight=1,
        semantic_weight=0,
        score_threshold=0.15,
    )
    assert ranked == []


def test_quotation_normalisation():
    source = (
        "The measure of loss is the difference between the contract price and the market price."
    )
    assert quotation_match("  The measure of loss is the difference  ", source) == "source_matched"
    assert quotation_match("market price of satellite spectrum", source) == "unresolved"
    assert (
        quotation_match("measure loss difference contract price market", source) == "partial_match"
    )
