import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_index, get_settings
from app.config import Settings
from app.models import ResearchSession, ResearchTurn
from app.schemas import (
    AnswerRequest,
    AnswerResponse,
    EvidenceIn,
    SearchRequest,
    SearchResponse,
    SessionCreate,
    SessionDetail,
    SessionSummary,
    TurnSummary,
    VerifyRequest,
    VerifyResponse,
)
from app.services.answering import answer_question, hits_from, list_session_turns
from app.services.files import UUID_RE
from app.services.index_store import IndexStore
from app.services.report import render_report
from app.services.settings_store import load_runtime, utcnow
from app.services.verification import LEGAL_LIMITATION, summarise_support, verify_evidence

router = APIRouter()


def _session_or_404(db: Session, session_id: str) -> ResearchSession:
    if not UUID_RE.fullmatch(session_id or ""):
        raise HTTPException(status_code=422, detail="Invalid session id")
    session = db.get(ResearchSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def _turn_count(db: Session, session_id: str) -> int:
    value = db.scalar(
        select(func.count()).select_from(ResearchTurn).where(ResearchTurn.session_id == session_id)
    )
    return int(value or 0)


def _session_summary(db: Session, session: ResearchSession) -> SessionSummary:
    return SessionSummary(
        id=session.id,
        title=session.title,
        document_ids=list(session.document_ids or []),
        created_at=session.created_at,
        updated_at=session.updated_at,
        turn_count=_turn_count(db, session.id),
    )


@router.post("/search", response_model=SearchResponse)
def search(
    body: SearchRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    index_store: IndexStore = Depends(get_index),
) -> SearchResponse:
    from app.services.answering import _require_ready_documents

    runtime = load_runtime(db, settings)
    _require_ready_documents(db, body.document_ids)
    pairs = index_store.search(body.query, runtime, body.document_ids or None, top_k=body.top_k)
    return SearchResponse(
        query=body.query,
        passages=hits_from(pairs),
        embedding_active=index_store.embedder.name if index_store.embedder else "not-built",
        embedding_notice=index_store.embedding_notice,
        retrieval={
            "top_k": body.top_k or runtime.top_k,
            "bm25_weight": runtime.bm25_weight,
            "semantic_weight": runtime.semantic_weight,
            "score_threshold": runtime.score_threshold,
            "lexical_rerank": runtime.lexical_rerank,
        },
    )


@router.post("/answers", response_model=AnswerResponse)
def create_answer(
    body: AnswerRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    index_store: IndexStore = Depends(get_index),
) -> AnswerResponse:
    complete = getattr(request.app.state, "test_complete", None)
    return answer_question(
        db,
        settings,
        index_store,
        question=body.question,
        document_ids=body.document_ids,
        session_id=body.session_id,
        top_k=body.top_k,
        complete=complete,
    )


@router.get("/sessions", response_model=list[SessionSummary])
def list_sessions(db: Session = Depends(get_db)) -> list[SessionSummary]:
    sessions = db.scalars(
        select(ResearchSession).order_by(ResearchSession.updated_at.desc()).limit(200)
    ).all()
    return [_session_summary(db, session) for session in sessions]


@router.post("/sessions", response_model=SessionSummary, status_code=201)
def create_session(body: SessionCreate, db: Session = Depends(get_db)) -> SessionSummary:
    from app.services.answering import _require_ready_documents

    _require_ready_documents(db, body.document_ids)
    now = utcnow()
    session = ResearchSession(
        id=str(uuid.uuid4()),
        title=(body.title or "Research session").strip()[:200] or "Research session",
        document_ids=body.document_ids,
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    db.commit()
    return _session_summary(db, session)


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session(session_id: str, db: Session = Depends(get_db)) -> SessionDetail:
    session = _session_or_404(db, session_id)
    turns = []
    for turn in list_session_turns(db, session.id):
        payload = turn.payload or {}
        metadata = payload.get("model_metadata") or {}
        turns.append(
            TurnSummary(
                id=turn.id,
                question=turn.question,
                created_at=turn.created_at,
                support_status=str(payload.get("support_status") or "unknown"),
                model_name=metadata.get("model"),
                insufficient_evidence=bool(payload.get("insufficient_evidence")),
            )
        )
    summary = _session_summary(db, session)
    return SessionDetail(**summary.model_dump(), turns=turns)


@router.get("/sessions/{session_id}/report", response_class=PlainTextResponse)
def export_report(session_id: str, db: Session = Depends(get_db)) -> PlainTextResponse:
    session = _session_or_404(db, session_id)
    markdown = render_report(session, list_session_turns(db, session.id))
    return PlainTextResponse(markdown, media_type="text/markdown; charset=utf-8")


@router.get("/turns/{turn_id}", response_model=AnswerResponse)
def get_turn(turn_id: str, db: Session = Depends(get_db)) -> AnswerResponse:
    if not UUID_RE.fullmatch(turn_id or ""):
        raise HTTPException(status_code=422, detail="Invalid turn id")
    turn = db.get(ResearchTurn, turn_id)
    if turn is None:
        raise HTTPException(status_code=404, detail="Turn not found")
    return AnswerResponse.model_validate(turn.payload)


@router.post("/verify", response_model=VerifyResponse)
def verify(body: VerifyRequest, db: Session = Depends(get_db)) -> VerifyResponse:
    if body.turn_id:
        if not UUID_RE.fullmatch(body.turn_id):
            raise HTTPException(status_code=422, detail="Invalid turn id")
        turn = db.get(ResearchTurn, body.turn_id)
        if turn is None:
            raise HTTPException(status_code=404, detail="Turn not found")
        payload = turn.payload or {}
        items = [EvidenceIn.model_validate(item) for item in payload.get("evidence") or []]
        supplied = (payload.get("model_metadata") or {}).get("supplied_excerpts") or {}
        evidence = verify_evidence(db, items, supplied)
        extra: list[str] = []
        support, unresolved = summarise_support(
            model_insufficient=bool(payload.get("insufficient_evidence")),
            evidence=evidence,
            extra_unresolved=extra,
            base_status="insufficient" if payload.get("insufficient_evidence") else None,
        )
        return VerifyResponse(
            turn_id=turn.id,
            evidence=evidence,
            has_unresolved_citations=unresolved,
            support_status=support,  # type: ignore[arg-type]
            limitations=list(payload.get("limitations") or []) + [LEGAL_LIMITATION],
            note=LEGAL_LIMITATION,
        )
    if not body.evidence:
        raise HTTPException(status_code=422, detail="Provide a turn_id or evidence to check")
    supplied_ids = set(body.supplied_chunk_ids or [])
    supplied = {chunk_id: "" for chunk_id in supplied_ids}
    for item in body.evidence:
        if item.chunk_id and item.chunk_id not in supplied:
            supplied[item.chunk_id] = ""
    # Ad-hoc checks compare the quotation with the stored chunk. Passing the chunk id in
    # supplied_chunk_ids marks it as supplied; the excerpt is loaded from the chunk text.
    from app.models import Chunk

    for chunk_id in list(supplied):
        chunk = db.get(Chunk, chunk_id)
        if chunk is not None and chunk_id in supplied_ids:
            supplied[chunk_id] = chunk.text
    evidence = verify_evidence(db, body.evidence, supplied if supplied_ids else {})
    support, unresolved = summarise_support(
        model_insufficient=False,
        evidence=evidence,
        extra_unresolved=[],
    )
    return VerifyResponse(
        turn_id=None,
        evidence=evidence,
        has_unresolved_citations=unresolved,
        support_status=support,  # type: ignore[arg-type]
        limitations=[LEGAL_LIMITATION],
        note=LEGAL_LIMITATION,
    )


@router.post("/indexes/rebuild")
def rebuild_indexes(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    index_store: IndexStore = Depends(get_index),
) -> dict:
    runtime = load_runtime(db, settings)
    index_store.rebuild(db, runtime)
    return {
        "status": "ready",
        "chunks": len(index_store.chunks),
        "embedding_active": index_store.embedder.name if index_store.embedder else None,
        "embedding_notice": index_store.embedding_notice,
    }
