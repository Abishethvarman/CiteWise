import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Banner, Button, Card, TextField } from "../components/ui";
import { api } from "../lib/api";
import { formatBytes, formatWhen } from "../lib/utils";

const uploadSchema = z.object({
  jurisdiction: z.string().max(160),
});

export function Library() {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState("uploaded_at");
  const [selected, setSelected] = useState<string | null>(null);
  const form = useForm<{ jurisdiction: string }>({
    resolver: zodResolver(uploadSchema),
    defaultValues: { jurisdiction: "" },
  });
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  if (status) params.set("status", status);
  params.set("sort", sort);
  params.set("order", "desc");
  const documents = useQuery({
    queryKey: ["documents", params.toString()],
    queryFn: () => api.documents(`?${params.toString()}`),
    refetchInterval: (current) =>
      current.state.data?.some((item) => item.status === "pending" || item.status === "processing") ? 2000 : false,
  });
  const detail = useQuery({
    queryKey: ["document", selected],
    queryFn: () => api.document(selected as string),
    enabled: Boolean(selected),
  });
  const upload = useMutation({
    mutationFn: (values: { jurisdiction: string }) => {
      if (!file) throw new Error("Choose a PDF first");
      return api.upload(file, values.jurisdiction);
    },
    onSuccess: () => {
      setFile(null);
      form.reset();
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
  const remove = useMutation({
    mutationFn: api.removeDocument,
    onSuccess: () => {
      setSelected(null);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-4xl text-navy">Library</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Jurisdiction is stored only when you type it. CiteWise does not infer a jurisdiction from the file name.
        </p>
      </div>
      <Card>
        <form
          className="grid gap-3 md:grid-cols-[1fr_1fr_auto]"
          onSubmit={form.handleSubmit((values) => upload.mutate(values))}
        >
          <div>
            <label htmlFor="pdf" className="mb-1 block text-sm">
              PDF file
            </label>
            <input
              id="pdf"
              type="file"
              accept="application/pdf,.pdf"
              className="block w-full text-sm"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
            {file && <p className="mt-1 text-xs text-muted">Selected: {file.name}</p>}
          </div>
          <div>
            <label htmlFor="jurisdiction" className="mb-1 block text-sm">
              Jurisdiction label, optional
            </label>
            <TextField id="jurisdiction" {...form.register("jurisdiction")} placeholder="Typed by you, not verified" />
          </div>
          <div className="flex items-end">
            <Button type="submit" disabled={upload.isPending || !file}>
              {upload.isPending ? "Uploading…" : "Upload"}
            </Button>
          </div>
        </form>
        {upload.isError && (
          <p role="alert" className="mt-3 text-sm text-rose">
            {(upload.error as Error).message}
          </p>
        )}
      </Card>
      <div className="flex flex-wrap gap-2">
        <label className="text-sm">
          Search filenames
          <TextField value={query} onChange={(event) => setQuery(event.target.value)} className="mt-1" />
        </label>
        <label className="text-sm">
          Status
          <select className="mt-1 block rounded-md border border-line bg-white px-3 py-2 text-sm" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">All</option>
            <option value="ready">Ready</option>
            <option value="processing">Processing</option>
            <option value="failed">Failed</option>
          </select>
        </label>
        <label className="text-sm">
          Sort
          <select className="mt-1 block rounded-md border border-line bg-white px-3 py-2 text-sm" value={sort} onChange={(event) => setSort(event.target.value)}>
            <option value="uploaded_at">Upload date</option>
            <option value="filename">Filename</option>
            <option value="size_bytes">Size</option>
            <option value="page_count">Pages</option>
          </select>
        </label>
      </div>
      {documents.isLoading && (
        <p aria-busy="true" className="text-sm">
          Loading documents
        </p>
      )}
      {documents.isError && (
        <p role="alert" className="text-sm text-rose">
          {(documents.error as Error).message}
        </p>
      )}
      {documents.data && documents.data.length === 0 && (
        <Card>
          <h2 className="font-serif text-2xl text-navy">No documents yet</h2>
          <p className="mt-2 text-sm text-muted">Upload a PDF to extract each page and build the local index.</p>
        </Card>
      )}
      <ul className="space-y-3">
        {documents.data?.map((document) => (
          <li key={document.id}>
            <Card>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-medium text-navy">{document.filename}</h2>
                  <p className="mt-1 text-xs text-muted">
                    {formatBytes(document.size_bytes)} · {document.page_count} pages · {document.chunk_count} chunks ·{" "}
                    {formatWhen(document.uploaded_at)}
                  </p>
                  <p className="mt-1 text-xs">
                    Processing: {document.status} · Index: {document.index_status}
                    {document.synthetic ? " · Synthetic demo" : ""}
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    Jurisdiction: {document.jurisdiction ? `${document.jurisdiction} (user supplied)` : "Not specified"}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button variant="secondary" type="button" onClick={() => setSelected(document.id)}>
                    Inspect
                  </Button>
                  <Button
                    variant="danger"
                    type="button"
                    onClick={() => {
                      if (window.confirm(`Delete ${document.filename} and its index entries?`)) remove.mutate(document.id);
                    }}
                  >
                    Delete
                  </Button>
                </div>
              </div>
              {document.error_message && <Banner tone="error">{document.error_message}</Banner>}
              {document.extraction_notes && <p className="mt-3 text-sm text-amber">{document.extraction_notes}</p>}
            </Card>
          </li>
        ))}
      </ul>
      {detail.data && (
        <Card>
          <h2 className="font-serif text-2xl text-navy">Page extract: {detail.data.filename}</h2>
          <ul className="mt-3 space-y-3">
            {detail.data.pages.map((page) => (
              <li key={page.page_number} className="border-t border-line pt-3 text-sm">
                <p className="font-medium">
                  Page {page.page_number} · {page.char_count} characters {page.is_empty ? "· no extractable text" : ""}
                </p>
                <p className="mt-1 whitespace-pre-wrap text-muted">{page.preview || "This page was recorded and left empty."}</p>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
