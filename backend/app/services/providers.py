"""Local model providers.

Only Ollama is enabled. There is no client for a commercial inference API and no API-key setting.
"""

import httpx


class ModelUnavailable(RuntimeError):
    pass


class ModelTimeout(ModelUnavailable):
    pass


class InvalidModelOutput(RuntimeError):
    pass


ANSWER_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "chunk_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "chunk_ids"],
            },
        },
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "chunk_id": {"type": "string"},
                    "quotation": {"type": "string"},
                },
                "required": ["chunk_id", "quotation"],
            },
        },
        "limitations": {"type": "array", "items": {"type": "string"}},
        "insufficient_evidence": {"type": "boolean"},
    },
    "required": ["answer", "claims", "evidence", "limitations", "insufficient_evidence"],
}


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> dict:
        try:
            response = httpx.get(f"{self.base_url}/api/version", timeout=2.0)
            response.raise_for_status()
            payload = response.json()
            version = payload.get("version") if isinstance(payload, dict) else None
            return {"reachable": True, "version": version, "error": None}
        except httpx.HTTPError as exc:
            return {"reachable": False, "version": None, "error": type(exc).__name__}

    def list_models(self) -> list[dict]:
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=3.0)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise ModelUnavailable("The local model service is not reachable") from exc
        models = []
        for item in payload.get("models", []) if isinstance(payload, dict) else []:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            models.append(
                {
                    "name": str(item.get("name")),
                    "size": item.get("size"),
                    "modified_at": item.get("modified_at"),
                }
            )
        return models

    def generate(self, model: str, system: str, user: str) -> str:
        payload = {
            "model": model,
            "stream": False,
            "format": ANSWER_JSON_SCHEMA,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"temperature": 0.1, "num_ctx": 4096},
        }
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            raise ModelTimeout("The local model did not respond before the timeout") from exc
        except httpx.HTTPError as exc:
            raise ModelUnavailable("The local model service is not reachable") from exc
        if response.status_code >= 400:
            raise ModelUnavailable(f"Ollama returned HTTP {response.status_code}")
        try:
            body = response.json()
        except ValueError as exc:
            raise InvalidModelOutput("The local model returned a non-JSON envelope") from exc
        content = body.get("message", {}).get("content") if isinstance(body, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise InvalidModelOutput("The local model returned an empty response")
        return content


def get_provider(base_url: str, timeout: float, name: str = "ollama") -> OllamaProvider:
    if name != "ollama":
        raise ValueError("Only the local Ollama provider is enabled")
    return OllamaProvider(base_url, timeout)
