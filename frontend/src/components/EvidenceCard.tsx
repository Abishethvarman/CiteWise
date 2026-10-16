import { Quote } from "lucide-react";
import type { VerifiedEvidence } from "../lib/types";
import { LEGAL_NOTE } from "../lib/utils";

const labels = {
  source_matched: "Source text matched",
  partial_match: "Partial source match",
  unresolved: "Unresolved reference",
};

const tones = {
  source_matched: "bg-teal-soft text-teal",
  partial_match: "bg-amber-soft text-amber",
  unresolved: "bg-rose-soft text-rose",
};

export function EvidenceCard({
  item,
  onOpen,
}: {
  item: VerifiedEvidence;
  onOpen?: (documentId: string, page: number) => void;
}) {
  return (
    <article className="rounded-lg border border-line bg-white p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Quote className="h-4 w-4 text-muted" aria-hidden="true" />
        <span className={`rounded px-2 py-0.5 text-xs font-medium ${tones[item.status]}`}>{labels[item.status]}</span>
        <span className="text-xs text-muted">Not a finding of legal correctness</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-ink">{item.quotation || "No quotation was provided."}</p>
      <dl className="mt-3 grid gap-1 text-xs text-muted">
        <div>Document: {item.document_name || "Unresolved"}</div>
        <div>Page: {item.page_number ?? "Unresolved"}</div>
        <div className="font-mono">Chunk: {item.chunk_id || "none"}</div>
        <div>Supplied to the model: {item.supplied_to_model ? "yes" : "no"}</div>
      </dl>
      {item.notes.map((note) => (
        <p key={note} className="mt-2 text-xs text-muted">
          {note}
        </p>
      ))}
      {item.source_passage && (
        <details className="mt-3">
          <summary className="cursor-pointer text-sm text-teal">Stored source passage</summary>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-6">{item.source_passage}</p>
        </details>
      )}
      {item.document_id && item.page_number && onOpen && (
        <button
          type="button"
          className="mt-3 text-sm text-teal underline"
          onClick={() => onOpen(item.document_id as string, item.page_number as number)}
        >
          Open page {item.page_number}
        </button>
      )}
      <p className="mt-3 text-xs text-muted">{LEGAL_NOTE}</p>
    </article>
  );
}
