# Architecture

```mermaid
flowchart LR
  UI[React workspace] --> API[FastAPI /api/v1]
  API --> DB[(SQLite)]
  API --> Files[Upload directory]
  API --> Extract[PyMuPDF page text]
  Extract --> Chunks[Page-bounded chunks]
  Chunks --> BM25[BM25]
  Chunks --> Vectors[FAISS or NumPy vectors]
  BM25 --> Retrieve[Hybrid retrieval]
  Vectors --> Retrieve
  Retrieve --> Prompt[System prompt plus untrusted evidence]
  Prompt --> Ollama[Ollama local model]
  Ollama --> Check[Quotation and chunk checks]
  Check --> UI
```

Document text never becomes the system prompt. The model provider implementation is Ollama only. Embeddings prefer sentence-transformers, then a local Ollama embedding model, then a labelled hashed bag-of-words fallback.

SQLite stores documents, pages, chunks, sessions, turns, and settings. The vector index can be rebuilt from the chunk table.
