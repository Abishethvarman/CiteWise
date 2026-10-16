import re
import unicodedata

_PUNCT = re.compile(r"[^a-z0-9'\s]+")
_SPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "")
    value = value.replace("\u2019", "'").replace("\u2018", "'")
    value = value.replace("\u201c", " ").replace("\u201d", " ")
    value = value.lower()
    value = _PUNCT.sub(" ", value)
    value = _SPACE.sub(" ", value).strip()
    return value


def word_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalize_text(text))


def quotation_match(quotation: str, source: str) -> str:
    """Return source_matched, partial_match, or unresolved against source text."""
    quote = normalize_text(quotation)
    body = normalize_text(source)
    if not quote or not body:
        return "unresolved"
    if quote in body:
        return "source_matched"
    quote_tokens = quote.split()
    if len(quote_tokens) < 4:
        return "unresolved"
    source_tokens = set(body.split())
    overlap = sum(1 for token in quote_tokens if token in source_tokens) / len(quote_tokens)
    if overlap >= 0.8:
        return "partial_match"
    return "unresolved"
