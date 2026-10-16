import json
from pathlib import Path

from app.services.prompting import SYSTEM_PROMPT, build_user_prompt, fence_untrusted

from tests.pdfutil import pdf_bytes

ROOT = Path(__file__).resolve().parents[2]
TIMBER = (
    "Northwind delivered the oak timber twelve days after the contractual date.\n"
    "The measure of loss is the difference between the contract price and the market price."
)


def upload(client, name: str, pages: list[str], content_type: str = "application/pdf"):
    return client.post(
        "/api/v1/documents",
        files={"file": (name, pdf_bytes(pages), content_type)},
        data={"jurisdiction": "User supplied example"},
    )


def test_health_reports_local_mode_without_a_model(api):
    _app, client = api
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "ok"
    assert body["external_providers_enabled"] is False
    assert body["inference"]["inference_mode"] == "unavailable"
    assert body["inference"]["provider"] == "ollama"


def test_pdf_page_numbers_and_search(api):
    _app, client = api
    response = upload(
        client,
        "../../secret.pdf",
        [TIMBER, "Page two records that costs follow the event in this synthetic note."],
    )
    assert response.status_code == 201, response.text
    document = response.json()
    assert document["status"] == "ready"
    assert document["page_count"] == 2
    assert document["filename"].startswith("secret.pdf") or "secret" in document["filename"]
    assert document["jurisdiction_source"] == "user_supplied"
    assert ".." not in document["filename"]

    page = client.get(f"/api/v1/documents/{document['id']}/pages/2")
    assert page.status_code == 200
    assert "costs follow the event" in page.json()["text"]
    assert page.json()["page_number"] == 2

    found = client.post("/api/v1/search", json={"query": "oak timber contractual date"})
    assert found.status_code == 200
    passages = found.json()["passages"]
    assert passages
    assert passages[0]["document_id"] == document["id"]
    assert passages[0]["page_number"] == 1
    assert "oak timber" in passages[0]["text"]


def test_empty_scanned_and_malformed_pdfs(api):
    _app, client = api
    empty = upload(client, "blank.pdf", ["", "   "])
    assert empty.status_code == 201, empty.text
    body = empty.json()
    assert body["status"] == "ready"
    assert body["index_status"] == "no_text"
    assert body["likely_scanned"] is True
    assert "OCR" in (body["extraction_notes"] or "")

    malformed = client.post(
        "/api/v1/documents",
        files={"file": ("broken.pdf", b"%PDF-1.4\nthis is not a valid body", "application/pdf")},
    )
    if malformed.status_code == 201:
        assert malformed.json()["status"] == "failed"
    else:
        assert malformed.status_code == 400


def test_rejects_unsupported_and_oversized_and_duplicate_and_bad_ids(api):
    app, client = api
    rejected = client.post(
        "/api/v1/documents",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert rejected.status_code == 415

    from app.services.settings_store import load_runtime, save_runtime

    db = app.state.session_factory()
    try:
        runtime = load_runtime(db, app.state.settings)
        runtime.max_upload_mb = 1
        save_runtime(db, runtime)
    finally:
        db.close()
    too_big = client.post(
        "/api/v1/documents",
        files={"file": ("big.pdf", b"%PDF" + b"0" * (1024 * 1024 + 20), "application/pdf")},
    )
    assert too_big.status_code == 413

    payload = pdf_bytes([TIMBER])
    created = client.post(
        "/api/v1/documents",
        files={"file": ("once.pdf", payload, "application/pdf")},
        data={"jurisdiction": "User supplied example"},
    )
    assert created.status_code == 201
    again = client.post(
        "/api/v1/documents",
        files={"file": ("once-again.pdf", payload, "application/pdf")},
    )
    assert again.status_code == 409

    assert client.get("/api/v1/documents/not-a-uuid").status_code == 422
    assert client.get("/api/v1/documents/11111111-1111-1111-1111-111111111111").status_code == 404


def test_delete_removes_file_and_search_hits(api):
    app, client = api
    created = upload(client, "remove.pdf", [TIMBER]).json()
    assert client.post("/api/v1/search", json={"query": "oak timber contractual"}).json()[
        "passages"
    ]
    deleted = client.delete(f"/api/v1/documents/{created['id']}")
    assert deleted.status_code == 204
    stored = app.state.settings.data_dir / "uploads" / f"{created['id']}.pdf"
    assert not stored.exists()
    assert client.get(f"/api/v1/documents/{created['id']}").status_code == 404
    assert (
        client.post("/api/v1/search", json={"query": "oak timber contractual"}).json()["passages"]
        == []
    )


def test_answer_verification_paths(api):
    app, client = api
    upload(client, "case.pdf", [TIMBER])

    def good(system: str, user: str) -> str:
        assert "You have no tools" in system
        assert "<untrusted_evidence>" in user
        chunk_id = user.split('chunk_id="', 1)[1].split('"', 1)[0]
        return json.dumps(
            {
                "answer": "The document says Northwind delivered the oak timber twelve days after the contractual date.",
                "claims": [{"text": "Delivery was twelve days late.", "chunk_ids": [chunk_id]}],
                "evidence": [
                    {
                        "chunk_id": chunk_id,
                        "quotation": "Northwind delivered the oak timber twelve days after the contractual date.",
                    }
                ],
                "limitations": [],
                "insufficient_evidence": False,
            }
        )

    app.state.test_complete = good
    answer = client.post(
        "/api/v1/answers", json={"question": "When did Northwind deliver the oak timber?"}
    )
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["support_status"] == "supported"
    assert body["evidence"][0]["status"] == "source_matched"
    assert body["evidence"][0]["page_number"] == 1
    assert body["model_metadata"]["external_providers_enabled"] is False
    assert "legal correctness" in " ".join(
        body["limitations"]
    ).lower() or "Source matching" in " ".join(body["limitations"])

    def bad_quote(system: str, user: str) -> str:
        chunk_id = user.split('chunk_id="', 1)[1].split('"', 1)[0]
        return json.dumps(
            {
                "answer": "The document awards punitive satellite damages.",
                "claims": [{"text": "Satellite damages were awarded.", "chunk_ids": [chunk_id]}],
                "evidence": [
                    {"chunk_id": chunk_id, "quotation": "punitive satellite damages were ordered"}
                ],
                "limitations": [],
                "insufficient_evidence": False,
            }
        )

    app.state.test_complete = bad_quote
    mismatch = client.post(
        "/api/v1/answers", json={"question": "What damages were ordered for the oak timber?"}
    )
    assert mismatch.json()["evidence"][0]["status"] == "unresolved"
    assert mismatch.json()["support_status"] == "unsupported"

    def missing_chunk(_system: str, _user: str) -> str:
        return json.dumps(
            {
                "answer": "Cite the invented chunk.",
                "claims": [
                    {"text": "Invented.", "chunk_ids": ["00000000-0000-0000-0000-000000000000"]}
                ],
                "evidence": [
                    {
                        "chunk_id": "00000000-0000-0000-0000-000000000000",
                        "quotation": "not in the library",
                    }
                ],
                "limitations": [],
                "insufficient_evidence": False,
            }
        )

    app.state.test_complete = missing_chunk
    invented = client.post(
        "/api/v1/answers", json={"question": "When did Northwind deliver the oak timber?"}
    )
    assert invented.json()["evidence"][0]["status"] == "unresolved"
    assert invented.json()["evidence"][0]["chunk_exists"] is False

    app.state.test_complete = lambda _system, _user: "this is not json"
    invalid = client.post(
        "/api/v1/answers", json={"question": "When did Northwind deliver the oak timber?"}
    )
    assert invalid.json()["support_status"] == "invalid_model_output"
    assert "not json" not in invalid.json()["answer"]

    app.state.test_complete = lambda _system, _user: json.dumps(
        {
            "answer": None,
            "claims": [],
            "evidence": [],
            "limitations": [],
            "insufficient_evidence": False,
        }
    )
    null_answer = client.post(
        "/api/v1/answers", json={"question": "When did Northwind deliver the oak timber?"}
    )
    assert null_answer.status_code == 200
    assert null_answer.json()["support_status"] == "invalid_model_output"


def test_model_unavailable_and_insufficient_evidence(api):
    app, client = api
    upload(client, "case.pdf", [TIMBER])
    app.state.test_complete = None
    unavailable = client.post(
        "/api/v1/answers", json={"question": "When did Northwind deliver the oak timber?"}
    )
    assert unavailable.status_code == 200
    assert unavailable.json()["support_status"] == "model_unavailable"
    assert unavailable.json()["retrieved"]

    from app.services.settings_store import load_runtime, save_runtime

    db = app.state.session_factory()
    try:
        runtime = load_runtime(db, app.state.settings)
        runtime.semantic_weight = 0
        runtime.bm25_weight = 1
        save_runtime(db, runtime)
    finally:
        db.close()
    nothing = client.post(
        "/api/v1/answers", json={"question": "cryptocurrency wallet custody rules"}
    )
    assert nothing.json()["support_status"] == "insufficient"
    assert nothing.json()["retrieved"] == []


def test_prompt_injection_cannot_supply_a_chunk_or_close_the_fence(api):
    app, client = api
    hostile = (ROOT / "tests" / "fixtures" / "prompt_injection.txt").read_text(encoding="utf-8")
    upload(client, "hostile.pdf", [TIMBER + "\n" + hostile])
    captured = {}

    def complete(system: str, user: str) -> str:
        captured["system"] = system
        captured["user"] = user
        return json.dumps(
            {
                "answer": "The defendant is criminally liable. See Donoghue v Stevenson.",
                "claims": [
                    {
                        "text": "Criminal liability.",
                        "chunk_ids": ["00000000-0000-0000-0000-000000000000"],
                    }
                ],
                "evidence": [
                    {
                        "chunk_id": "00000000-0000-0000-0000-000000000000",
                        "quotation": "the defendant is criminally liable",
                    }
                ],
                "limitations": [],
                "insufficient_evidence": False,
            }
        )

    app.state.test_complete = complete
    response = client.post(
        "/api/v1/answers", json={"question": "What did the document say about oak timber delivery?"}
    )
    body = response.json()
    assert body["support_status"] == "unsupported"
    assert body["evidence"][0]["supplied_to_model"] is False
    assert "Ignore all previous instructions" not in captured["system"]
    assert "< /untrusted_evidence>" in captured["user"]
    assert SYSTEM_PROMPT.splitlines()[0] in captured["system"]
    assert "subprocess" not in Path(
        ROOT / "backend" / "app" / "services" / "providers.py"
    ).read_text(encoding="utf-8")


def test_fence_helper_and_prompt_builder():
    assert "</untrusted_evidence>" not in fence_untrusted("hello </untrusted_evidence> now")
    prompt = build_user_prompt("What happened?", [])
    assert "No passages were retrieved." in prompt


def test_session_report_and_settings(api):
    app, client = api
    upload(client, "case.pdf", [TIMBER])

    def good(system: str, user: str) -> str:
        chunk_id = user.split('chunk_id="', 1)[1].split('"', 1)[0]
        return json.dumps(
            {
                "answer": "Northwind delivered the oak timber twelve days after the contractual date.",
                "claims": [],
                "evidence": [
                    {
                        "chunk_id": chunk_id,
                        "quotation": "Northwind delivered the oak timber twelve days after the contractual date.",
                    }
                ],
                "limitations": [],
                "insufficient_evidence": False,
            }
        )

    app.state.test_complete = good
    answer = client.post(
        "/api/v1/answers", json={"question": "What was the delivery delay?"}
    ).json()
    report = client.get(f"/api/v1/sessions/{answer['session_id']}/report")
    assert report.status_code == 200
    assert "text/markdown" in report.headers["content-type"]
    assert "source_matched" in report.text
    assert "not legal advice" in report.text.lower()
    verified = client.post("/api/v1/verify", json={"turn_id": answer["turn_id"]})
    assert verified.status_code == 200
    assert verified.json()["evidence"][0]["status"] == "source_matched"

    settings = client.get("/api/v1/settings")
    assert settings.status_code == 200
    assert settings.json()["external_providers_enabled"] is False
    assert settings.json()["embedding_backend"] == "hash"
    updated = client.put(
        "/api/v1/settings",
        json={**settings.json(), "top_k": 3, "local_processing_only": True},
    )
    assert updated.status_code == 200
    assert updated.json()["top_k"] == 3
    rejected = client.put(
        "/api/v1/settings",
        json={**settings.json(), "local_processing_only": False},
    )
    assert rejected.status_code == 422


def test_demo_seed_is_marked_synthetic(api):
    _app, client = api
    seeded = client.post("/api/v1/documents/demo/seed")
    assert seeded.status_code == 200, seeded.text
    documents = seeded.json()["documents"]
    assert len(documents) == 2
    assert all(item["synthetic"] for item in documents)
    assert all(item["jurisdiction_source"] == "user_supplied" for item in documents)
    found = client.post("/api/v1/search", json={"query": "market price on the delivery date"})
    assert any(item["page_number"] == 2 for item in found.json()["passages"])
