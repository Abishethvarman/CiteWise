import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Chunk, Document, Page
from app.schemas import ClaimIn, ClaimOut, EvidenceIn, VerifiedEvidence
from app.services.normalize import quotation_match

LEGAL_LIMITATION = (
    "Source matching checks whether a quotation appears in the uploaded extract. "
    "It does not establish legal correctness, binding authority, or that the law is current."
)
UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)


def verify_evidence(
    db: Session,
    items: list[EvidenceIn],
    supplied: dict[str, str],
) -> list[VerifiedEvidence]:
    verified: list[VerifiedEvidence] = []
    for item in items:
        chunk_id = (item.chunk_id or "").strip()
        quotation = item.quotation or ""
        chunk = db.get(Chunk, chunk_id) if chunk_id else None
        document = db.get(Document, chunk.document_id) if chunk else None
        page = None
        if chunk is not None:
            page = db.scalar(
                select(Page).where(
                    Page.document_id == chunk.document_id,
                    Page.page_number == chunk.page_number,
                )
            )
        supplied_to_model = chunk_id in supplied
        notes: list[str] = []
        if chunk is None:
            status = "unresolved"
            notes.append("The cited chunk does not exist in the library.")
        elif page is None:
            status = "unresolved"
            notes.append("The cited page is not in the extracted document.")
        elif not supplied_to_model:
            status = "unresolved"
            notes.append("The cited chunk was not supplied to the model for this answer.")
        else:
            supplied_text = supplied.get(chunk_id, "")
            against_supplied = quotation_match(quotation, supplied_text)
            against_source = quotation_match(quotation, chunk.text)
            if against_supplied == "source_matched":
                status = "source_matched"
                notes.append(
                    "The quotation matches the extracted text that was supplied to the model. "
                    "This is not a finding of legal correctness."
                )
            elif against_source == "source_matched":
                status = "partial_match"
                notes.append(
                    "The quotation matches the stored chunk, but it was outside the excerpt supplied to the model."
                )
            elif against_supplied == "partial_match" or against_source == "partial_match":
                status = "partial_match"
                notes.append(
                    "Most quotation words appear in the source, but the quotation is not an exact normalised match."
                )
            else:
                status = "unresolved"
                notes.append("The quotation does not match the extracted source text.")
        verified.append(
            VerifiedEvidence(
                chunk_id=chunk_id,
                quotation=quotation,
                document_id=document.id if document else None,
                document_name=document.filename if document else None,
                page_number=chunk.page_number if chunk else None,
                source_passage=chunk.text if chunk else None,
                status=status,  # type: ignore[arg-type]
                supplied_to_model=supplied_to_model,
                chunk_exists=chunk is not None,
                page_exists=page is not None,
                notes=notes,
            )
        )
    return verified


def claim_support(claim: ClaimIn, evidence: list[VerifiedEvidence]) -> ClaimOut:
    by_id = {item.chunk_id: item for item in evidence}
    statuses = [by_id[chunk_id].status for chunk_id in claim.chunk_ids if chunk_id in by_id]
    if (
        claim.chunk_ids
        and len(statuses) == len(claim.chunk_ids)
        and all(status == "source_matched" for status in statuses)
    ):
        support = "supported"
    elif any(status in {"source_matched", "partial_match"} for status in statuses):
        support = "partial"
    else:
        support = "unsupported"
    return ClaimOut(text=claim.text, chunk_ids=list(claim.chunk_ids), support=support)  # type: ignore[arg-type]


def unresolved_ids_in_answer(answer: str, supplied_ids: set[str]) -> list[str]:
    found = UUID_RE.findall(answer or "")
    return [item for item in found if item not in supplied_ids]


def summarise_support(
    *,
    model_insufficient: bool,
    evidence: list[VerifiedEvidence],
    extra_unresolved: list[str],
    base_status: str | None = None,
) -> tuple[str, bool]:
    if (
        base_status in {"model_unavailable", "invalid_model_output", "insufficient"}
        and not evidence
    ):
        return base_status, True
    if model_insufficient and base_status == "insufficient":
        unresolved = any(item.status != "source_matched" for item in evidence) or bool(
            extra_unresolved
        )
        return "insufficient", unresolved or any(item.status == "unresolved" for item in evidence)
    if not evidence and model_insufficient:
        return "insufficient", True
    statuses = [item.status for item in evidence]
    has_unresolved = any(status == "unresolved" for status in statuses) or bool(extra_unresolved)
    if not statuses:
        return ("insufficient" if model_insufficient else "unsupported"), True
    if model_insufficient:
        return "insufficient", has_unresolved
    if all(status == "source_matched" for status in statuses) and not extra_unresolved:
        return "supported", False
    if any(status == "source_matched" for status in statuses):
        return "partial", has_unresolved
    if any(status == "partial_match" for status in statuses):
        return "partial", True
    return "unsupported", True
