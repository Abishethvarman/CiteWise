# API

FastAPI publishes the live contract at `http://127.0.0.1:8000/docs`. This page is the human summary. All routes are under `/api/v1`.

The application has no authentication. Errors use `{"detail": ...}` with status 400, 404, 409, 413, 415, 422, or 500.

## Health and models

`GET /health` returns version, database status, and whether Ollama is reachable. `inference.mode` is `local` or `unavailable`.

`GET /models` lists models from the configured Ollama `/api/tags` endpoint.

`POST /models/check` body `{"retry_embedding": false}` checks the selected chat model and, when `retry_embedding` is true, loads the embedding backend again.

## Documents

`POST /documents` multipart field `file` (PDF) and optional form field `jurisdiction`.

Validation:

- Filename must end in `.pdf`.
- Content type must be `application/pdf`, `application/x-pdf`, `application/octet-stream`, or empty.
- The first bytes must be `%PDF-`.
- Size and page count must be within the configured limits.
- A repeated SHA-256 returns 409 with the existing document id.

Processing is asynchronous unless `CITEWISE_INLINE_PROCESSING=true`. Poll `GET /documents`.

`GET /documents` supports `q`, `status`, `sort` (`created_at`, `filename`, `size_bytes`, `page_count`, `status`), `order`, `limit`, and `offset`.

`GET /documents/{id}` includes per-page character counts and a short preview. Empty pages are listed.

`GET /documents/{id}/pages/{page_number}` returns extracted text. Page numbers start at 1.

`GET /documents/{id}/file` returns the stored PDF.

`PATCH /documents/{id}` body `{"jurisdiction": "text or null"}` stores only the supplied label.

`POST /documents/{id}/reindex` runs extraction again.

`DELETE /documents/{id}` removes the file, pages, chunks, and rebuilds the vector index.

## Search and answers

`POST /search` body `{"query", "document_ids", "top_k"}`. Results include BM25, semantic, and combined scores, plus `sent_to_model`. Passages below the threshold are returned only as a short weak set and are not sent to the model.

`POST /answers` body `{"question", "document_ids", "session_id", "top_k"}`. Creates a session when `session_id` is omitted. The response separates the displayed answer, evidence checks, retrieved passages, limitations, and model metadata.

`source_support` is `matched`, `partial`, `none`, or `not_generated`. `matched` means a quotation was found in a supplied chunk. It does not mean the legal statement is correct.

## Sessions and verification

`GET /sessions`, `POST /sessions`, `GET /sessions/{id}`, `DELETE /sessions/{id}`.

`DELETE /sessions?confirm=true` deletes every session.

`GET /sessions/{id}/report` returns Markdown.

`GET /turns/{id}` returns one turn and its stored payload.

`POST /verify` accepts `{"turn_id"}` or an ad-hoc `answer`, `evidence`, `claims`, and `supplied_chunk_ids`.

## Settings and demo

`GET /settings` and `PUT /settings`. The update schema rejects unknown fields. Upload and page limits cannot exceed the environment hard caps.

`POST /demo/seed` writes three fictional PDFs and indexes them. The response notice says they are not law.

## Configuration

Environment variables use the prefix `CITEWISE_`. See `.env.example`. Chunk size is an approximate token count of about four characters per token, not a model BPE count.
