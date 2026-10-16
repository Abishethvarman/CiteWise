export type DocumentSummary = {
  id: string;
  filename: string;
  size_bytes: number;
  page_count: number;
  mime_type: string;
  status: string;
  index_status: string;
  error_message: string | null;
  extraction_notes: string | null;
  jurisdiction: string | null;
  jurisdiction_source: "user_supplied" | "not_specified";
  synthetic: boolean;
  likely_scanned: boolean;
  uploaded_at: string;
  processed_at: string | null;
  chunk_count: number;
  sha256: string;
};

export type PagePreview = {
  page_number: number;
  char_count: number;
  is_empty: boolean;
  preview: string;
};

export type DocumentDetail = DocumentSummary & { pages: PagePreview[] };

export type PassageHit = {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  text: string;
  score: number;
  bm25_score: number;
  semantic_score: number;
};

export type VerifiedEvidence = {
  chunk_id: string;
  quotation: string;
  document_id: string | null;
  document_name: string | null;
  page_number: number | null;
  source_passage: string | null;
  status: "source_matched" | "partial_match" | "unresolved";
  supplied_to_model: boolean;
  chunk_exists: boolean;
  page_exists: boolean;
  notes: string[];
};

export type Claim = {
  text: string;
  chunk_ids: string[];
  support: "supported" | "partial" | "unsupported";
};

export type AnswerResponse = {
  turn_id: string;
  session_id: string;
  question: string;
  answer: string;
  claims: Claim[];
  evidence: VerifiedEvidence[];
  limitations: string[];
  insufficient_evidence: boolean;
  support_status: string;
  has_unresolved_citations: boolean;
  model_metadata: {
    provider?: string;
    model?: string | null;
    embedding?: string | null;
    inference_mode?: string;
    retrieval?: Record<string, unknown>;
    external_providers_enabled?: boolean;
  };
  retrieved: PassageHit[];
  embedding_notice: string;
};

export type SessionSummary = {
  id: string;
  title: string;
  document_ids: string[];
  created_at: string;
  updated_at: string;
  turn_count: number;
};

export type TurnSummary = {
  id: string;
  question: string;
  created_at: string;
  support_status: string;
  model_name: string | null;
  insufficient_evidence: boolean;
};

export type SessionDetail = SessionSummary & { turns: TurnSummary[] };

export type SettingsResponse = {
  ollama_base_url: string;
  ollama_model: string;
  embedding_backend: "auto" | "sentence-transformers" | "ollama" | "hash";
  embedding_model: string;
  ollama_embed_model: string;
  top_k: number;
  bm25_weight: number;
  semantic_weight: number;
  score_threshold: number;
  chunk_size: number;
  chunk_overlap: number;
  max_upload_mb: number;
  max_pages: number;
  retention_days: number | null;
  lexical_rerank: boolean;
  llm_timeout_seconds: number;
  prompt_passage_tokens: number;
  local_processing_only: true;
  embedding_active: string;
  embedding_notice: string;
  inference_mode: "local_ollama" | "model_missing" | "unavailable";
  inference_detail: string;
  external_providers_enabled: false;
  data_dir: string;
  reindex_required: boolean;
};

export type ModelStatus = {
  reachable: boolean;
  inference_mode: "local_ollama" | "model_missing" | "unavailable";
  detail: string;
  selected_model: string;
  selected_model_installed: boolean;
  models: { name: string; size: number | null; modified_at: string | null }[];
  external_providers_enabled: false;
  provider: "ollama";
};

export type HealthResponse = {
  status: string;
  version: string;
  database: string;
  inference: ModelStatus;
  external_providers_enabled: false;
};
