import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";
import { EvidenceCard } from "../components/EvidenceCard";
import { PdfPane } from "../components/PdfPane";
import { Banner, Button, Card, TextArea, TextField } from "../components/ui";
import { api, downloadReport } from "../lib/api";
import type { AnswerResponse, PassageHit } from "../lib/types";
import { LEGAL_NOTE } from "../lib/utils";

const questionSchema = z.object({
  question: z.string().trim().min(1, "Enter a question").max(4000),
});

export function Research() {
  const params = useParams();
  const [sessionId, setSessionId] = useState(params.sessionId);
  useEffect(() => {
    if (params.sessionId) setSessionId(params.sessionId);
  }, [params.sessionId]);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [viewer, setViewer] = useState<{ id: string; page: number; title: string } | null>(null);
  const [answer, setAnswer] = useState<AnswerResponse | null>(null);
  const [hits, setHits] = useState<PassageHit[]>([]);
  const [pane, setPane] = useState<"ask" | "viewer" | "evidence">("ask");
  const documents = useQuery({ queryKey: ["documents", "ready"], queryFn: () => api.documents("?status=ready") });
  const session = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => api.session(sessionId as string),
    enabled: Boolean(sessionId),
  });
  const form = useForm<{ question: string }>({ resolver: zodResolver(questionSchema), defaultValues: { question: "" } });
  const search = useMutation({
    mutationFn: (query: string) => api.search(query, selectedDocs),
    onSuccess: (result) => setHits(result.passages),
  });
  const ask = useMutation({
    mutationFn: (question: string) => api.ask(question, selectedDocs, sessionId),
    onSuccess: (result) => {
      setAnswer(result);
      setSessionId(result.session_id);
      setHits(result.retrieved);
      setPane("evidence");
    },
  });

  function openPassage(documentId: string, page: number, title: string) {
    setViewer({ id: documentId, page, title });
    setPane("viewer");
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-serif text-4xl text-navy">Research</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{LEGAL_NOTE}</p>
        </div>
        {sessionId && (
          <Button variant="secondary" type="button" onClick={() => downloadReport(sessionId)}>
            Export Markdown report
          </Button>
        )}
      </div>
      {ask.data?.model_metadata.inference_mode === "unavailable" && (
        <Banner tone="warn">The local model is unavailable. Retrieved passages are shown without a generated answer.</Banner>
      )}
      <div className="flex gap-2 lg:hidden" role="tablist" aria-label="Research panes">
        {(["ask", "viewer", "evidence"] as const).map((item) => (
          <button key={item} type="button" role="tab" aria-selected={pane === item} className="rounded-md border border-line px-3 py-1 text-sm" onClick={() => setPane(item)}>
            {item}
          </button>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-[220px_1fr_320px]">
        <Card className={pane === "ask" ? "" : "hidden lg:block"}>
          <h2 className="text-sm font-medium">Documents</h2>
          {documents.isLoading && <p className="mt-2 text-sm">Loading documents</p>}
          {documents.data?.length === 0 && <p className="mt-2 text-sm text-muted">No ready documents.</p>}
          <ul className="mt-2 space-y-2">
            {documents.data?.map((document) => (
              <li key={document.id}>
                <label className="flex gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selectedDocs.includes(document.id)}
                    onChange={(event) =>
                      setSelectedDocs((current) =>
                        event.target.checked ? [...current, document.id] : current.filter((id) => id !== document.id),
                      )
                    }
                  />
                  <span>{document.filename}</span>
                </label>
              </li>
            ))}
          </ul>
          {session.data && (
            <div className="mt-4 border-t border-line pt-3">
              <h2 className="text-sm font-medium">History</h2>
              <ul className="mt-2 space-y-2">
                {session.data.turns.map((turn) => (
                  <li key={turn.id}>
                    <Link className="text-xs text-teal" to={`/app/verify/${turn.id}`}>
                      {turn.question}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
        <div className={`${pane === "viewer" ? "" : "hidden"} min-h-[480px] overflow-hidden rounded-lg border border-line bg-white lg:block`}>
          <PdfPane url={viewer ? api.fileUrl(viewer.id) : null} page={viewer?.page ?? 1} title={viewer?.title ?? "No document"} />
        </div>
        <div className={`${pane === "ask" || pane === "evidence" ? "" : "hidden"} space-y-4 lg:block`}>
          <Card>
            <form
              className="space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                const query = new FormData(event.currentTarget).get("search");
                if (typeof query === "string" && query.trim()) search.mutate(query.trim());
              }}
            >
              <label htmlFor="search" className="text-sm">
                Search passages
              </label>
              <TextField id="search" name="search" placeholder="Search the selected documents" />
              <Button type="submit" variant="secondary" disabled={search.isPending}>
                {search.isPending ? "Searching…" : "Search"}
              </Button>
            </form>
            {search.isError && (
              <p role="alert" className="mt-2 text-sm text-rose">
                {(search.error as Error).message}
              </p>
            )}
            <ul className="mt-3 space-y-2">
              {hits.map((hit) => (
                <li key={hit.chunk_id}>
                  <button type="button" className="text-left text-sm" onClick={() => openPassage(hit.document_id, hit.page_number, hit.document_name)}>
                    <span className="font-medium text-navy">
                      {hit.document_name} · p. {hit.page_number}
                    </span>
                    <span className="mt-1 block text-xs text-muted">Retrieval score {hit.score.toFixed(2)} (not a probability)</span>
                    <span className="mt-1 block text-muted">{hit.text.slice(0, 220)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </Card>
          <Card>
            <form className="space-y-2" onSubmit={form.handleSubmit((values) => ask.mutate(values.question))}>
              <label htmlFor="question" className="text-sm">
                Ask about the selected documents
              </label>
              <TextArea id="question" rows={4} {...form.register("question")} />
              {form.formState.errors.question && (
                <p role="alert" className="text-sm text-rose">
                  {form.formState.errors.question.message}
                </p>
              )}
              <Button type="submit" disabled={ask.isPending}>
                {ask.isPending ? "Working…" : "Ask"}
              </Button>
            </form>
            {ask.isError && (
              <p role="alert" className="mt-2 text-sm text-rose">
                {(ask.error as Error).message}
              </p>
            )}
          </Card>
          {answer && (
            <Card>
              <p className="text-xs uppercase tracking-wide text-muted">Model answer · {answer.support_status}</p>
              <p className="mt-2 text-sm leading-6">{answer.answer}</p>
              <p className="mt-2 text-xs text-muted">
                Mode: {answer.model_metadata.inference_mode} · Model: {answer.model_metadata.model || "none"} · Embedding:{" "}
                {answer.model_metadata.embedding}
              </p>
              {answer.embedding_notice && <p className="mt-2 text-xs text-muted">{answer.embedding_notice}</p>}
              <ul className="mt-3 list-disc pl-5 text-xs text-muted">
                {answer.limitations.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <Link className="mt-3 inline-block text-sm text-teal" to={`/app/verify/${answer.turn_id}`}>
                Open citation check
              </Link>
              <div className="mt-4 space-y-3">
                {answer.evidence.map((item) => (
                  <EvidenceCard
                    key={`${item.chunk_id}-${item.quotation}`}
                    item={item}
                    onOpen={(id, page) => openPassage(id, page, item.document_name || "Document")}
                  />
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
