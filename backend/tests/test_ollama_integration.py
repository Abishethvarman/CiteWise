import os

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.integration
def test_optional_ollama_round_trip():
    """Calls a local Ollama server only when CITEWISE_RUN_OLLAMA=1."""
    if os.environ.get("CITEWISE_RUN_OLLAMA") != "1":
        pytest.skip("Set CITEWISE_RUN_OLLAMA=1 to run the optional Ollama check")
    base = os.environ.get("CITEWISE_OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    version = httpx.get(f"{base}/api/version", timeout=5)
    assert version.status_code == 200
    tags = httpx.get(f"{base}/api/tags", timeout=5)
    assert tags.status_code == 200
    names = [item.get("name") for item in tags.json().get("models", [])]
    model = os.environ.get("CITEWISE_OLLAMA_MODEL", "llama3.2:3b")
    if model not in names:
        pytest.skip(f"{model} is not installed")
    response = httpx.post(
        f"{base}/api/chat",
        json={
            "model": model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": "Return JSON with key ok."},
                {"role": "user", "content": 'Reply with {"ok": true} and nothing else.'},
            ],
            "options": {"temperature": 0, "num_ctx": 1024},
        },
        timeout=180,
    )
    assert response.status_code == 200
    assert response.json().get("message", {}).get("content")
