import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Library } from "../pages/Library";

function renderLibrary() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Library />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("library states", () => {
  it("shows a loading state", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    renderLibrary();
    expect(screen.getByText("Loading documents")).toBeInTheDocument();
  });

  it("shows an empty library", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } })),
    );
    renderLibrary();
    expect(await screen.findByText("No documents yet")).toBeInTheDocument();
  });

  it("shows an error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "Library unavailable" }), { status: 500, headers: { "Content-Type": "application/json" } })));
    renderLibrary();
    expect(await screen.findByRole("alert")).toHaveTextContent("Library unavailable");
  });

  it("shows the selected upload filename", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } })),
    );
    renderLibrary();
    const input = await screen.findByLabelText("PDF file");
    const file = new File(["%PDF"], "brief.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(await screen.findByText("Selected: brief.pdf")).toBeInTheDocument();
  });
});
