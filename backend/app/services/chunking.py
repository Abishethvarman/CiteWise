import re
import uuid
from dataclasses import dataclass

CHUNK_NAMESPACE = uuid.UUID("6f0c1a4e-9b3d-4e2a-8c55-1a2b3c4d5e6f")
_TOKEN = re.compile(r"\S+")


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    text: str
    token_count: int
    start_offset: int
    end_offset: int


def chunk_id_for(document_id: str, page_number: int, chunk_index: int, start_offset: int) -> str:
    material = f"{document_id}:{page_number}:{chunk_index}:{start_offset}"
    return str(uuid.uuid5(CHUNK_NAMESPACE, material))


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[TextChunk]:
    """Split text on whitespace tokens, preferring paragraph breaks near the window end."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    overlap = max(0, min(overlap, chunk_size - 1))
    tokens = list(_TOKEN.finditer(text or ""))
    if not tokens:
        return []

    paragraph_ends: set[int] = set()
    for index in range(len(tokens) - 1):
        gap = text[tokens[index].end() : tokens[index + 1].start()]
        if "\n\n" in gap or gap.count("\n") >= 2:
            paragraph_ends.add(index)

    chunks: list[TextChunk] = []
    start_i = 0
    while start_i < len(tokens):
        hard_end = min(len(tokens) - 1, start_i + chunk_size - 1)
        end_i = hard_end
        window = hard_end - start_i + 1
        if window >= chunk_size:
            threshold = start_i + int(chunk_size * 0.6)
            candidates = [point for point in range(threshold, hard_end) if point in paragraph_ends]
            if candidates:
                end_i = candidates[-1]
        start_offset = tokens[start_i].start()
        end_offset = tokens[end_i].end()
        chunks.append(
            TextChunk(
                chunk_index=len(chunks),
                text=text[start_offset:end_offset],
                token_count=end_i - start_i + 1,
                start_offset=start_offset,
                end_offset=end_offset,
            )
        )
        if end_i >= len(tokens) - 1:
            break
        next_start = end_i + 1 - overlap
        if next_start <= start_i:
            next_start = end_i + 1
        start_i = next_start
    return chunks


def truncate_tokens(text: str, max_tokens: int) -> str:
    matches = list(_TOKEN.finditer(text or ""))
    if max_tokens < 1 or len(matches) <= max_tokens:
        return text or ""
    return text[: matches[max_tokens - 1].end()]
