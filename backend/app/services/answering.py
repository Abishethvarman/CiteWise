import json
import logging
import re
import uuid

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Document, ResearchSession, ResearchTurn
from app.schemas import (
    AnswerDraft,
    AnswerResponse,
    ClaimOut,
    PassageHit,
    StoredSettings,
    VerifiedEvidence,
)
from app.services.chunking import truncate_tokens
from app.services.index_store import IndexStore
from app.services.prompting import SYSTEM_PROMPT, build_user_prompt
from app.services.providers import InvalidModelOutput, ModelUnavailable, get_provider
from app.services.settings_store import load_runtime, utcnow
from app.services.verification import (
    LEGAL_LIMITATION,
    claim_support,
    summarise_support,
    unresolved_ids_in_answer,
    verify_evidence,
)

logger = logging.getLogger("citewise.answers")
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_draft(raw: str) -> AnswerDraft:
    text = _FENCE.sub("", raw.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match is None:
            raise InvalidModelOutput("Model output was not valid JSON")
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise InvalidModelOutput("Model output was not a JSON object")
    try:
        return AnswerDraft.model_validate(data)
    except ValidationError as exc:
        raise InvalidModelOutput("Model output did not match the required schema") from exc


def hits_from(pairs) -> list[PassageHit]:
    hits = []
    for chunk, ranked in pairs:
        hits.append(
            PassageHit(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_name=chunk.document_name,
                page_number=chunk.page_number,
                text=chunk.text,
                score=ranked.score,
                bm25_score=ranked.bm25_score,
                semantic_score=ranked.semantic_score,
            )
        )
    return hits


def answer_question(
    db: Session,
    settings: Settings,
    index_store: IndexStore,
    *,
    question: str,
    document_ids: list[str],
    session_id: str | None,
    top_k: int | None,
    complete=None,
) -> AnswerResponse:
    runtime = load_runtime(db, settings)
    _require_ready_documents(db, document_ids)
    pairs = index_store.search(question, runtime, document_ids or None, top_k=top_k)
    supplied_rows = []
    supplied: dict[str, str] = {}
    for chunk, ranked in pairs:
        excerpt = truncate_tokens(chunk.text, runtime.prompt_passage_tokens)
        supplied[chunk.chunk_id] = excerpt
        supplied_rows.append((chunk, ranked, excerpt))
    session = _session_for(db, session_id, question, document_ids)
    retrieved = hits_from(pairs)
    logger.info(
        "answer requested session=%s documents=%s hits=%s",
        session.id,
        len(document_ids),
        len(retrieved),
    )

    if not pairs:
        return _persist(
            db,
            session,
            question,
            runtime,
            index_store,
            retrieved,
            answer="No retrieved passage met the score threshold, so CiteWise did not generate an answer.",
            claims=[],
            evidence=[],
            limitations=[
                "Nothing in the selected documents scored highly enough to send to the model.",
                LEGAL_LIMITATION,
            ],
            insufficient=True,
            support_status="insufficient",
            unresolved=True,
            inference_mode="not_called",
            supplied=supplied,
        )

    draft, inference_mode, failure = _complete(runtime, question, supplied_rows, complete)
    if failure == "model_unavailable":
        return _persist(
            db,
            session,
            question,
            runtime,
            index_store,
            retrieved,
            answer=(
                "The local model is unavailable, so CiteWise did not generate an answer. "
                "Any passages below were retrieved from your documents and were not written by a model."
            ),
            claims=[],
            evidence=[],
            limitations=["The configured Ollama endpoint could not be used.", LEGAL_LIMITATION],
            insufficient=True,
            support_status="model_unavailable",
            unresolved=True,
            inference_mode="unavailable",
            supplied=supplied,
        )
    if failure == "invalid_model_output" or draft is None:
        return _persist(
            db,
            session,
            question,
            runtime,
            index_store,
            retrieved,
            answer="The model response did not match the required structure, so it was not accepted.",
            claims=[],
            evidence=[],
            limitations=[
                "The raw model response was discarded because it failed schema validation.",
                LEGAL_LIMITATION,
            ],
            insufficient=True,
            support_status="invalid_model_output",
            unresolved=True,
            inference_mode=inference_mode,
            supplied=supplied,
        )

    draft.evidence = draft.evidence[:12]
    draft.claims = draft.claims[:12]
    evidence = verify_evidence(db, draft.evidence, supplied)
    claims = [claim_support(claim, evidence) for claim in draft.claims]
    extra = unresolved_ids_in_answer(draft.answer, set(supplied))
    support, unresolved = summarise_support(
        model_insufficient=draft.insufficient_evidence,
        evidence=evidence,
        extra_unresolved=extra,
        base_status="insufficient" if draft.insufficient_evidence else None,
    )
    limitations = list(draft.limitations)
    if extra:
        limitations.append(
            "The answer text mentions chunk IDs that were not supplied to the model."
        )
    if LEGAL_LIMITATION not in limitations:
        limitations.append(LEGAL_LIMITATION)
    return _persist(
        db,
        session,
        question,
        runtime,
        index_store,
        retrieved,
        answer=draft.answer.strip(),
        claims=claims,
        evidence=evidence,
        limitations=limitations,
        insufficient=draft.insufficient_evidence or support in {"insufficient", "unsupported"},
        support_status=support,
        unresolved=unresolved,
        inference_mode=inference_mode,
        supplied=supplied,
    )


def _complete(runtime: StoredSettings, question: str, rows, complete):
    system = SYSTEM_PROMPT
    user = build_user_prompt(question, rows)
    if complete is not None:
        try:
            raw = complete(system, user)
            return parse_draft(raw), "local_test_double", None
        except (InvalidModelOutput, json.JSONDecodeError, ValueError):
            return None, "local_test_double", "invalid_model_output"
    provider = get_provider(runtime.ollama_base_url, runtime.llm_timeout_seconds)
    if not provider.health()["reachable"]:
        return None, "unavailable", "model_unavailable"
    last_error: InvalidModelOutput | None = None
    try:
        for _attempt in range(2):
            try:
                raw = provider.generate(runtime.ollama_model, system, user)
                return parse_draft(raw), "local_ollama", None
            except InvalidModelOutput as exc:
                last_error = exc
    except ModelUnavailable:
        return None, "unavailable", "model_unavailable"
    logger.info("model output rejected after retry: %s", last_error)
    return None, "local_ollama", "invalid_model_output"


def _require_ready_documents(db: Session, document_ids: list[str]) -> None:
    from fastapi import HTTPException

    from app.services.files import UUID_RE

    for document_id in document_ids:
        if not UUID_RE.fullmatch(document_id):
            raise HTTPException(status_code=422, detail="Invalid document id")
        document = db.get(Document, document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        if document.status != "ready":
            raise HTTPException(
                status_code=409, detail=f"{document.filename} is not ready for research"
            )


def _session_for(
    db: Session, session_id: str | None, question: str, document_ids: list[str]
) -> ResearchSession:
    from fastapi import HTTPException

    from app.services.files import UUID_RE

    if session_id:
        if not UUID_RE.fullmatch(session_id):
            raise HTTPException(status_code=422, detail="Invalid session id")
        session = db.get(ResearchSession, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        if document_ids:
            session.document_ids = document_ids
        session.updated_at = utcnow()
        return session
    now = utcnow()
    session = ResearchSession(
        id=str(uuid.uuid4()),
        title=(question.strip()[:80] or "Research session"),
        document_ids=document_ids,
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    db.commit()
    return session


def _persist(
    db: Session,
    session: ResearchSession,
    question: str,
    runtime: StoredSettings,
    index_store: IndexStore,
    retrieved: list[PassageHit],
    *,
    answer: str,
    claims: list[ClaimOut],
    evidence: list[VerifiedEvidence],
    limitations: list[str],
    insufficient: bool,
    support_status: str,
    unresolved: bool,
    inference_mode: str,
    supplied: dict[str, str] | None = None,
) -> AnswerResponse:
    metadata = {
        "provider": "ollama" if inference_mode == "local_ollama" else "none",
        "model": runtime.ollama_model if inference_mode == "local_ollama" else None,
        "embedding": index_store.embedder.name if index_store.embedder else None,
        "prompt_version": "citewise-prompt-1",
        "inference_mode": inference_mode,
        "external_providers_enabled": False,
        "supplied_excerpts": supplied or {},
        "retrieval": {
            "top_k": runtime.top_k,
            "bm25_weight": runtime.bm25_weight,
            "semantic_weight": runtime.semantic_weight,
            "score_threshold": runtime.score_threshold,
            "lexical_rerank": runtime.lexical_rerank,
            "chunk_size": runtime.chunk_size,
            "chunk_overlap": runtime.chunk_overlap,
        },
    }
    response = AnswerResponse(
        turn_id=str(uuid.uuid4()),
        session_id=session.id,
        question=question,
        answer=answer,
        claims=claims,
        evidence=evidence,
        limitations=limitations,
        insufficient_evidence=insufficient,
        support_status=support_status,  # type: ignore[arg-type]
        has_unresolved_citations=unresolved,
        model_metadata=metadata,
        retrieved=retrieved,
        embedding_notice=index_store.embedding_notice,
    )
    session.updated_at = utcnow()
    db.add(
        ResearchTurn(
            id=response.turn_id,
            session_id=session.id,
            question=question,
            payload=response.model_dump(mode="json"),
            created_at=utcnow(),
        )
    )
    db.commit()
    return response


def get_turn_payload(db: Session, turn_id: str) -> dict | None:
    turn = db.get(ResearchTurn, turn_id)
    if turn is None:
        return None
    return turn.payload


def list_session_turns(db: Session, session_id: str) -> list[ResearchTurn]:
    return list(
        db.scalars(
            select(ResearchTurn)
            .where(ResearchTurn.session_id == session_id)
            .order_by(ResearchTurn.created_at)
        ).all()
    )
