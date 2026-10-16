import pytest
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def api(tmp_path):
    data_dir = tmp_path / "data"
    database = tmp_path / "citewise.db"
    settings = Settings(
        data_dir=data_dir,
        database_url="sqlite:///" + database.as_posix(),
        embedding_backend="hash",
        ollama_base_url="http://127.0.0.1:9",
        ollama_model="llama3.2:3b",
        cors_origins="http://localhost:5173",
        score_threshold=0.15,
        chunk_size=120,
        chunk_overlap=20,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        app.state.inline_jobs = True
        yield app, client
