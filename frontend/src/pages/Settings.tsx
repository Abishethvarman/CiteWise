import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Banner, Button, Card, TextField } from "../components/ui";
import { api } from "../lib/api";
import type { SettingsResponse } from "../lib/types";

const schema = z.object({
  ollama_base_url: z.string().min(1),
  ollama_model: z.string().min(1),
  embedding_backend: z.enum(["auto", "sentence-transformers", "ollama", "hash"]),
  embedding_model: z.string().min(1),
  ollama_embed_model: z.string().min(1),
  top_k: z.number().min(1).max(20),
  bm25_weight: z.number().min(0).max(1),
  semantic_weight: z.number().min(0).max(1),
  score_threshold: z.number().min(0).max(1),
  chunk_size: z.number().min(50).max(2000),
  chunk_overlap: z.number().min(0).max(500),
  max_upload_mb: z.number().min(1).max(100),
  max_pages: z.number().min(1).max(2000),
  retention_days: z.string(),
  lexical_rerank: z.boolean(),
  llm_timeout_seconds: z.number().min(5).max(600),
});

type FormValues = z.infer<typeof schema>;

function toForm(settings: SettingsResponse): FormValues {
  return {
    ollama_base_url: settings.ollama_base_url,
    ollama_model: settings.ollama_model,
    embedding_backend: settings.embedding_backend,
    embedding_model: settings.embedding_model,
    ollama_embed_model: settings.ollama_embed_model,
    top_k: settings.top_k,
    bm25_weight: settings.bm25_weight,
    semantic_weight: settings.semantic_weight,
    score_threshold: settings.score_threshold,
    chunk_size: settings.chunk_size,
    chunk_overlap: settings.chunk_overlap,
    max_upload_mb: settings.max_upload_mb,
    max_pages: settings.max_pages,
    retention_days: settings.retention_days ? String(settings.retention_days) : "",
    lexical_rerank: settings.lexical_rerank,
    llm_timeout_seconds: settings.llm_timeout_seconds,
  };
}

export function SettingsPage() {
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const models = useQuery({ queryKey: ["models"], queryFn: api.models });
  const form = useForm<FormValues>({ resolver: zodResolver(schema) });
  useEffect(() => {
    if (settings.data) form.reset(toForm(settings.data));
  }, [settings.data, form]);
  const save = useMutation({
    mutationFn: (values: FormValues) =>
      api.saveSettings({
        ...values,
        retention_days: values.retention_days ? Number(values.retention_days) : null,
        prompt_passage_tokens: settings.data?.prompt_passage_tokens ?? 280,
        local_processing_only: true,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings"] }),
  });
  const check = useMutation({
    mutationFn: () => api.checkModel(form.getValues("ollama_base_url"), form.getValues("ollama_model")),
  });
  const rebuild = useMutation({ mutationFn: api.rebuild });

  return (
    <div className="space-y-4">
      <h1 className="font-serif text-4xl text-navy">Settings</h1>
      <Banner tone={settings.data?.inference_mode === "local_ollama" ? "info" : "warn"}>
        Current inference mode: {settings.data?.inference_mode ?? "loading"}. {settings.data?.inference_detail} External
        commercial providers are disabled.
      </Banner>
      {settings.data?.embedding_notice && <p className="text-sm text-muted">{settings.data.embedding_notice}</p>}
      <p className="text-sm text-muted">Active embedding: {settings.data?.embedding_active}. Data directory: {settings.data?.data_dir}</p>
      {settings.isLoading && <p aria-busy="true">Loading settings</p>}
      {settings.isError && (
        <p role="alert" className="text-sm text-rose">
          {(settings.error as Error).message}
        </p>
      )}
      <Card>
        <form className="grid gap-3 md:grid-cols-2" onSubmit={form.handleSubmit((values) => save.mutate(values))}>
          <label className="text-sm">
            Model endpoint
            <TextField className="mt-1" {...form.register("ollama_base_url")} />
          </label>
          <label className="text-sm">
            Local model
            <TextField className="mt-1" list="model-names" {...form.register("ollama_model")} />
            <datalist id="model-names">
              {models.data?.models.map((model) => (
                <option key={model.name} value={model.name} />
              ))}
            </datalist>
          </label>
          <label className="text-sm">
            Embedding backend
            <select className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2 text-sm" {...form.register("embedding_backend")}>
              <option value="auto">Automatic local choice</option>
              <option value="sentence-transformers">sentence-transformers</option>
              <option value="ollama">Ollama embeddings</option>
              <option value="hash">Deterministic hash (not semantic)</option>
            </select>
          </label>
          <label className="text-sm">
            Sentence-transformer model
            <TextField className="mt-1" {...form.register("embedding_model")} />
          </label>
          <label className="text-sm">
            Ollama embedding model
            <TextField className="mt-1" {...form.register("ollama_embed_model")} />
          </label>
          <label className="text-sm">
            Top passages
            <TextField className="mt-1" type="number" {...form.register("top_k", { valueAsNumber: true })} />
          </label>
          <label className="text-sm">
            Keyword weight
            <TextField className="mt-1" type="number" step="0.05" {...form.register("bm25_weight", { valueAsNumber: true })} />
          </label>
          <label className="text-sm">
            Semantic weight
            <TextField className="mt-1" type="number" step="0.05" {...form.register("semantic_weight", { valueAsNumber: true })} />
          </label>
          <label className="text-sm">
            Score threshold
            <TextField className="mt-1" type="number" step="0.05" {...form.register("score_threshold", { valueAsNumber: true })} />
          </label>
          <label className="text-sm">
            Chunk size (whitespace tokens)
            <TextField className="mt-1" type="number" {...form.register("chunk_size", { valueAsNumber: true })} />
          </label>
          <label className="text-sm">
            Chunk overlap
            <TextField className="mt-1" type="number" {...form.register("chunk_overlap", { valueAsNumber: true })} />
          </label>
          <label className="text-sm">
            Max upload MB
            <TextField className="mt-1" type="number" {...form.register("max_upload_mb", { valueAsNumber: true })} />
          </label>
          <label className="text-sm">
            Max pages
            <TextField className="mt-1" type="number" {...form.register("max_pages", { valueAsNumber: true })} />
          </label>
          <label className="text-sm">
            Retention days, blank to keep
            <TextField className="mt-1" {...form.register("retention_days")} />
          </label>
          <label className="text-sm">
            Model timeout seconds
            <TextField className="mt-1" type="number" {...form.register("llm_timeout_seconds", { valueAsNumber: true })} />
          </label>
          <label className="flex items-center gap-2 text-sm md:col-span-2">
            <input type="checkbox" {...form.register("lexical_rerank")} />
            Apply an optional lexical overlap adjustment. This is not a neural reranker.
          </label>
          <div className="flex flex-wrap gap-2 md:col-span-2">
            <Button type="submit" disabled={save.isPending}>
              {save.isPending ? "Saving…" : "Save settings"}
            </Button>
            <Button type="button" variant="secondary" onClick={() => check.mutate()} disabled={check.isPending}>
              {check.isPending ? "Checking…" : "Check model connection"}
            </Button>
            <Button type="button" variant="secondary" onClick={() => rebuild.mutate()} disabled={rebuild.isPending}>
              {rebuild.isPending ? "Rebuilding…" : "Rebuild indexes"}
            </Button>
          </div>
        </form>
        {save.isError && (
          <p role="alert" className="mt-3 text-sm text-rose">
            {(save.error as Error).message}
          </p>
        )}
        {save.data?.reindex_required && <p className="mt-3 text-sm">Chunk or embedding settings changed. Rebuild indexes before the next search.</p>}
        {check.data && (
          <p role="status" className="mt-3 text-sm">
            {check.data.detail} Mode: {check.data.inference_mode}.
          </p>
        )}
        {check.isError && (
          <p role="alert" className="mt-3 text-sm text-rose">
            {(check.error as Error).message}
          </p>
        )}
        {rebuild.data && (
          <p role="status" className="mt-3 text-sm">
            Index rebuilt with {rebuild.data.chunks} chunks. {rebuild.data.embedding_notice}
          </p>
        )}
      </Card>
    </div>
  );
}
