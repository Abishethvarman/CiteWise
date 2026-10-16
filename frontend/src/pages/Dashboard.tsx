import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Banner, Button, Card } from "../components/ui";
import { api } from "../lib/api";
import { formatWhen } from "../lib/utils";

export function Dashboard() {
  const queryClient = useQueryClient();
  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.documents(),
    refetchInterval: (query) =>
      query.state.data?.some((item) => item.status === "pending" || item.status === "processing") ? 2000 : false,
  });
  const sessions = useQuery({ queryKey: ["sessions"], queryFn: api.sessions });
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });
  const seed = useMutation({
    mutationFn: api.seedDemo,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
  const docs = documents.data ?? [];
  const processing = docs.filter((item) => item.status === "pending" || item.status === "processing").length;
  const failed = docs.filter((item) => item.status === "failed").length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-4xl text-navy">Workspace</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Counts below come from this installation&apos;s library. Start by uploading a PDF you are allowed to process,
          or load the labelled synthetic demo.
        </p>
      </div>
      {health.data && (
        <Banner tone={health.data.inference.inference_mode === "local_ollama" ? "info" : "warn"}>
          Inference: {health.data.inference.detail}
        </Banner>
      )}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <p className="text-sm text-muted">Documents</p>
          <p className="mt-2 font-serif text-4xl text-navy">{documents.isLoading ? "…" : docs.length}</p>
        </Card>
        <Card>
          <p className="text-sm text-muted">Still processing</p>
          <p className="mt-2 font-serif text-4xl text-navy">{processing}</p>
        </Card>
        <Card>
          <p className="text-sm text-muted">Extraction failures</p>
          <p className="mt-2 font-serif text-4xl text-navy">{failed}</p>
        </Card>
      </div>
      {docs.length === 0 && !documents.isLoading && (
        <Card>
          <h2 className="font-serif text-2xl text-navy">First use</h2>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-6">
            <li>Upload a PDF, or load the synthetic demo documents.</li>
            <li>Wait until extraction and indexing finish. Empty or scanned pages are reported, not invented.</li>
            <li>Search the library, then ask a question about the selected documents.</li>
            <li>Open the cited page and read the verification status. A match is not legal advice.</li>
          </ol>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link to="/app/library">
              <Button>Upload a PDF</Button>
            </Link>
            <Button variant="secondary" onClick={() => seed.mutate()} disabled={seed.isPending}>
              {seed.isPending ? "Loading demo…" : "Load synthetic demo"}
            </Button>
          </div>
          <p className="mt-3 text-xs text-muted">
            Demo files are fictional text generated inside CiteWise. They are not judgments, statutes, or advice.
          </p>
          {seed.isError && (
            <p role="alert" className="mt-2 text-sm text-rose">
              {(seed.error as Error).message}
            </p>
          )}
        </Card>
      )}
      <Card>
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-serif text-2xl text-navy">Recent sessions</h2>
          <Link to="/app/research" className="text-sm text-teal">
            New research
          </Link>
        </div>
        {sessions.isLoading && <p className="mt-3 text-sm">Loading sessions…</p>}
        {sessions.isError && (
          <p role="alert" className="mt-3 text-sm text-rose">
            {(sessions.error as Error).message}
          </p>
        )}
        {sessions.data && sessions.data.length === 0 && <p className="mt-3 text-sm text-muted">No research sessions yet.</p>}
        <ul className="mt-3 divide-y divide-line">
          {sessions.data?.map((session) => (
            <li key={session.id} className="flex items-center justify-between gap-3 py-3">
              <div>
                <Link to={`/app/research/${session.id}`} className="text-sm font-medium text-navy">
                  {session.title}
                </Link>
                <p className="text-xs text-muted">
                  {session.turn_count} questions · updated {formatWhen(session.updated_at)}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
