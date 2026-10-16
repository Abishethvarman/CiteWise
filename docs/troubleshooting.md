# Troubleshooting

## Ollama is unavailable

The settings page and `GET /api/v1/health` say when the endpoint cannot be reached. Start the Ollama application, or run `ollama serve`, and confirm `ollama list` shows the selected model. Install the default with:

```bash
ollama pull llama3.2:3b
```

A missing model is not replaced with a cloud model. Choose a model that is actually installed, or pull it.

Answers can take a minute on CPU. Raise `CITEWISE_OLLAMA_TIMEOUT_SECONDS` if the model is still loading.

## Embeddings download or memory

`sentence-transformers` uses PyTorch and can use several hundred megabytes of RAM for MiniLM. If the download fails, search still runs on keywords and the response includes a warning. Switch the embedding backend to `ollama` or `hash` in settings. `hash` is deterministic feature hashing, not a neural embedding model.

## PDFs

- A file that does not start with `%PDF-` is rejected.
- Encrypted PDFs are not unlocked.
- Pages with almost no text are listed and are not indexed as searchable text.
- If most pages are empty, the library marks the file as likely scanned. This version does not OCR.
- The default limits are 25 MB and 200 pages. Hard caps default to 50 MB and 500 pages.

## Empty search

The document must be `ready`. A scan with no text layer has nothing to retrieve. A question with no lexical overlap can fall under the score threshold; those passages are not sent to the model.

## Windows and the database

Stop the API before deleting `backend/data`. SQLite may keep a lock while the server is running.

## Docker

The compose file does not attach a GPU. It expects Ollama on the host at `host.docker.internal:11434`. The backend image installs the CPU stack without the optional `sentence-transformers` extra, so it does not download PyTorch. Compose sets the embedding backend to `ollama`.
