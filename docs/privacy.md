# Privacy

CiteWise keeps uploads, extracted text, embeddings, and research sessions in the configured data directory. The default is `backend/data`.

- No telemetry is implemented.
- Ordinary logs record document ids and status, not page text.
- The chat client speaks only to the configured Ollama-compatible endpoint. The default is `http://127.0.0.1:11434`.
- There is no OpenAI, Azure, or other commercial chat client in this codebase.
- `auto` embeddings may download `sentence-transformers/all-MiniLM-L6-v2` once. That is a model download. Document text is encoded locally after the weights are present.
- Set `CITEWISE_EMBEDDING_BACKEND=ollama` to use a model you already pulled, such as `nomic-embed-text`, and avoid that download.
- Set `CITEWISE_EMBEDDING_BACKEND=hash` for deterministic feature hashing with no download. The interface labels it as a fallback, not as a neural model.
- Retention deletes documents older than `retention_days` when the API starts. Empty means keep them until you delete them.

Local processing does not encrypt the database, lock the screen, or stop another program on the computer from reading the data directory.
