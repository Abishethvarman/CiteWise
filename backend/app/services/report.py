from app.models import ResearchSession, ResearchTurn


def _quote_block(text: str) -> str:
    lines = (text or "").splitlines() or [""]
    return "\n".join(f"> {line}" for line in lines)


def render_report(session: ResearchSession, turns: list[ResearchTurn]) -> str:
    lines = [
        "# CiteWise research report",
        "",
        "This report was produced by a local document research assistant. It is not legal advice. "
        "A source match means the quotation was found in the extracted upload. It does not establish "
        "that a legal proposition is correct, binding, or current.",
        "",
        f"- Session: {session.title}",
        f"- Session id: `{session.id}`",
        "",
    ]
    if not turns:
        lines.append("No questions have been asked in this session.")
        return "\n".join(lines) + "\n"
    for index, turn in enumerate(turns, start=1):
        payload = turn.payload or {}
        lines.extend(
            [
                f"## Question {index}",
                "",
                payload.get("question") or turn.question,
                "",
                "### Answer",
                "",
                payload.get("answer") or "",
                "",
                f"- Support status: {payload.get('support_status', 'unknown')}",
                f"- Insufficient evidence flag: {payload.get('insufficient_evidence')}",
                f"- Inference: {(payload.get('model_metadata') or {}).get('inference_mode')}",
                f"- Model: {(payload.get('model_metadata') or {}).get('model')}",
                f"- Embedding: {(payload.get('model_metadata') or {}).get('embedding')}",
                "",
                "### Evidence",
                "",
            ]
        )
        evidence = payload.get("evidence") or []
        if not evidence:
            lines.append("No model evidence was accepted for this question.")
            lines.append("")
        for item_index, item in enumerate(evidence, start=1):
            lines.extend(
                [
                    f"#### Evidence {item_index}: {item.get('status')}",
                    "",
                    f"- Document: {item.get('document_name') or 'unresolved'}",
                    f"- Page: {item.get('page_number') if item.get('page_number') is not None else 'unresolved'}",
                    f"- Chunk: `{item.get('chunk_id')}`",
                    f"- Supplied to model: {item.get('supplied_to_model')}",
                    "",
                    "Quotation:",
                    "",
                    _quote_block(item.get("quotation") or ""),
                    "",
                    "Source passage:",
                    "",
                    _quote_block(item.get("source_passage") or ""),
                    "",
                ]
            )
            for note in item.get("notes") or []:
                lines.append(f"- Note: {note}")
            lines.append("")
        lines.append("### Limitations")
        lines.append("")
        for limitation in payload.get("limitations") or []:
            lines.append(f"- {limitation}")
        lines.append("")
    return "\n".join(lines)
