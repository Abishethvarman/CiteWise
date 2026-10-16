import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { EvidenceCard } from "../components/EvidenceCard";
import { Banner, Card } from "../components/ui";
import { api } from "../lib/api";
import { LEGAL_NOTE } from "../lib/utils";

export function Verify() {
  const { turnId = "" } = useParams();
  const turn = useQuery({ queryKey: ["turn", turnId], queryFn: () => api.turn(turnId), enabled: Boolean(turnId) });
  const check = useQuery({ queryKey: ["verify", turnId], queryFn: () => api.verify(turnId), enabled: Boolean(turnId) });

  return (
    <div className="space-y-4">
      <h1 className="font-serif text-4xl text-navy">Citation check</h1>
      <Banner tone="warn">{LEGAL_NOTE} Automated checks are incomplete. They do not confirm that an authority is binding or still good law.</Banner>
      {turn.isLoading && <p aria-busy="true">Loading answer</p>}
      {turn.isError && (
        <p role="alert" className="text-sm text-rose">
          {(turn.error as Error).message}
        </p>
      )}
      {turn.data && (
        <Card>
          <p className="text-sm text-muted">Question</p>
          <p className="mt-1">{turn.data.question}</p>
          <p className="mt-4 text-sm text-muted">Answer kept for inspection</p>
          <p className="mt-1 text-sm leading-6">{turn.data.answer}</p>
          <p className="mt-3 text-xs text-muted">
            Support status: {check.data?.support_status || turn.data.support_status}. Status labels describe source
            matching only.
          </p>
          <Link className="mt-3 inline-block text-sm text-teal" to={`/app/research/${turn.data.session_id}`}>
            Back to the research session
          </Link>
        </Card>
      )}
      {check.isLoading && <p>Checking citations…</p>}
      <div className="space-y-3">
        {check.data?.evidence.map((item) => (
          <EvidenceCard key={`${item.chunk_id}-${item.quotation}`} item={item} />
        ))}
        {check.data && check.data.evidence.length === 0 && <p className="text-sm text-muted">This answer has no evidence items to check.</p>}
      </div>
    </div>
  );
}
