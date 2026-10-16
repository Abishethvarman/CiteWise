import type {
  AnswerResponse,
  DocumentDetail,
  DocumentSummary,
  HealthResponse,
  ModelStatus,
  PassageHit,
  SessionDetail,
  SessionSummary,
  SettingsResponse,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep status text */
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  const type = response.headers.get("content-type") || "";
  if (type.includes("text/markdown") || type.includes("text/plain")) {
    return (await response.text()) as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  documents: (params = "") => request<DocumentSummary[]>(`/documents${params}`),
  document: (id: string) => request<DocumentDetail>(`/documents/${id}`),
  upload: (file: File, jurisdiction: string) => {
    const body = new FormData();
    body.set("file", file);
    if (jurisdiction.trim()) body.set("jurisdiction", jurisdiction.trim());
    return request<DocumentSummary>("/documents", { method: "POST", body });
  },
  removeDocument: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),
  reindex: (id: string) => request<DocumentSummary>(`/documents/${id}/reindex`, { method: "POST" }),
  seedDemo: () =>
    request<{ documents: DocumentSummary[]; created: number; already_present: number }>(
      "/documents/demo/seed",
      { method: "POST" },
    ),
  search: (query: string, documentIds: string[]) =>
    request<{ passages: PassageHit[]; embedding_active: string; embedding_notice: string }>("/search", {
      method: "POST",
      body: JSON.stringify({ query, document_ids: documentIds }),
    }),
  ask: (question: string, documentIds: string[], sessionId?: string) =>
    request<AnswerResponse>("/answers", {
      method: "POST",
      body: JSON.stringify({ question, document_ids: documentIds, session_id: sessionId }),
    }),
  sessions: () => request<SessionSummary[]>("/sessions"),
  session: (id: string) => request<SessionDetail>(`/sessions/${id}`),
  turn: (id: string) => request<AnswerResponse>(`/turns/${id}`),
  verify: (turnId: string) =>
    request<{ evidence: AnswerResponse["evidence"]; support_status: string; note: string }>("/verify", {
      method: "POST",
      body: JSON.stringify({ turn_id: turnId }),
    }),
  report: (sessionId: string) => request<string>(`/sessions/${sessionId}/report`),
  settings: () => request<SettingsResponse>("/settings"),
  saveSettings: (body: unknown) => request<SettingsResponse>("/settings", { method: "PUT", body: JSON.stringify(body) }),
  checkModel: (ollama_base_url: string, ollama_model: string) =>
    request<ModelStatus>("/models/check", {
      method: "POST",
      body: JSON.stringify({ ollama_base_url, ollama_model }),
    }),
  models: () => request<ModelStatus>("/models"),
  rebuild: () => request<{ status: string; chunks: number; embedding_notice: string }>("/indexes/rebuild", { method: "POST" }),
  fileUrl: (id: string) => `${BASE}/documents/${id}/file`,
};

export async function downloadReport(sessionId: string) {
  const markdown = await api.report(sessionId);
  const blob = new Blob([markdown], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `citewise-report-${sessionId}.md`;
  link.click();
  URL.revokeObjectURL(url);
}
