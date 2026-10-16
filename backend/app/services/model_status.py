from app.schemas import InferenceMode, ModelInfo, ModelStatus, StoredSettings
from app.services.providers import ModelUnavailable, get_provider


def describe_models(
    runtime: StoredSettings, base_url: str | None = None, model_name: str | None = None
) -> ModelStatus:
    selected = (model_name or runtime.ollama_model).strip()
    endpoint = (base_url or runtime.ollama_base_url).strip()
    provider = get_provider(endpoint, min(runtime.llm_timeout_seconds, 5))
    health = provider.health()
    if not health["reachable"]:
        return ModelStatus(
            reachable=False,
            inference_mode="unavailable",
            detail="The local Ollama endpoint is not reachable. Answers will not be generated.",
            selected_model=selected,
            selected_model_installed=False,
        )
    try:
        raw_models = provider.list_models()
    except ModelUnavailable:
        raw_models = []
    models = [
        ModelInfo(name=item["name"], size=item.get("size"), modified_at=item.get("modified_at"))
        for item in raw_models
    ]
    installed = selected in {item.name for item in models}
    mode: InferenceMode = "local_ollama" if installed else "model_missing"
    if installed:
        version = health.get("version") or "unknown"
        detail = f"Local Ollama {version} is reachable and {selected} is installed. No commercial API is used."
    else:
        detail = f"Ollama is reachable, but {selected} is not in the local model list."
    return ModelStatus(
        reachable=True,
        inference_mode=mode,
        detail=detail,
        selected_model=selected,
        selected_model_installed=installed,
        models=models,
    )
