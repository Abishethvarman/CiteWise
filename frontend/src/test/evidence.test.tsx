import { render, screen } from "@testing-library/react";
import { EvidenceCard } from "../components/EvidenceCard";
import type { VerifiedEvidence } from "../lib/types";

function item(status: VerifiedEvidence["status"]): VerifiedEvidence {
  return {
    chunk_id: "chunk-1",
    quotation: "The oak timber arrived twelve days late.",
    document_id: "doc-1",
    document_name: "SYNTHETIC demo.pdf",
    page_number: 2,
    source_passage: "The oak timber arrived twelve days late.",
    status,
    supplied_to_model: status !== "unresolved",
    chunk_exists: status !== "unresolved",
    page_exists: status !== "unresolved",
    notes: ["Checked against the extract."],
  };
}

describe("evidence states", () => {
  it("labels a source match without calling it legally correct", () => {
    render(<EvidenceCard item={item("source_matched")} />);
    expect(screen.getByText("Source text matched")).toBeInTheDocument();
    expect(screen.getByText(/Not a finding of legal correctness/)).toBeInTheDocument();
    expect(screen.queryByText("✓")).not.toBeInTheDocument();
  });

  it("labels a partial match", () => {
    render(<EvidenceCard item={item("partial_match")} />);
    expect(screen.getByText("Partial source match")).toBeInTheDocument();
  });

  it("labels an unresolved reference", () => {
    render(<EvidenceCard item={item("unresolved")} />);
    expect(screen.getByText("Unresolved reference")).toBeInTheDocument();
  });
});
