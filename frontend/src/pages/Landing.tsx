import { BookOpen, Cpu, FileSearch, Shield } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui";

const apiOrigin = import.meta.env.VITE_API_ORIGIN ?? "http://127.0.0.1:8000";
const repository = import.meta.env.VITE_REPOSITORY_URL;

const features = [
  {
    icon: FileSearch,
    title: "Evidence before eloquence",
    text: "Answers are tied to chunk identifiers, document names, and PDF page numbers from the file you uploaded.",
  },
  {
    icon: Shield,
    title: "Local by default",
    text: "Documents stay in the configured data directory. The app does not call a commercial model API and has no telemetry.",
  },
  {
    icon: Cpu,
    title: "Open-weight models",
    text: "Ollama runs the language model on your machine. Embeddings can use a local model, Ollama, or a clearly labelled hashing fallback.",
  },
  {
    icon: BookOpen,
    title: "Quotation checks",
    text: "Cited quotations are compared with the extracted text. A match is not a ruling that the law is correct or current.",
  },
];

export function Landing() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="border-b border-line bg-navy text-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <p className="font-serif text-2xl">CiteWise</p>
          <nav aria-label="Primary" className="flex gap-4 text-sm">
            <a href="#privacy">Privacy</a>
            <a href="#local-ai">Local AI</a>
            <a href={`${apiOrigin}/docs`}>API docs</a>
            <Link to="/app">Open workspace</Link>
          </nav>
        </div>
      </header>
      <main id="main">
        <section className="mx-auto max-w-6xl px-4 py-16">
          <p className="text-sm tracking-wide text-teal uppercase">Document research</p>
          <h1 className="mt-3 max-w-3xl font-serif text-5xl leading-tight text-navy">
            Every answer should lead back to its evidence.
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-muted">
            CiteWise is a privacy-first research desk for law students, researchers, academics, and small practices.
            Upload documents you are allowed to use, search them, and ask questions that stay attached to the passages
            the application actually retrieved.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/app">
              <Button>Open the workspace</Button>
            </Link>
            <a href={`${apiOrigin}/docs`}>
              <Button variant="secondary">Read the API reference</Button>
            </a>
          </div>
        </section>
        <section className="mx-auto grid max-w-6xl gap-4 px-4 pb-12 md:grid-cols-2">
          {features.map((feature) => (
            <article key={feature.title} className="rounded-lg border border-line bg-card p-5">
              <feature.icon className="h-5 w-5 text-teal" aria-hidden="true" />
              <h2 className="mt-3 font-serif text-2xl text-navy">{feature.title}</h2>
              <p className="mt-2 text-sm leading-6 text-muted">{feature.text}</p>
            </article>
          ))}
        </section>
        <section id="privacy" className="bg-white">
          <div className="mx-auto max-w-6xl px-4 py-12">
            <h2 className="font-serif text-3xl text-navy">Where documents are processed</h2>
            <p className="mt-3 max-w-3xl leading-7 text-muted">
              Uploads, extracted text, indexes, and research sessions are stored on the computer running CiteWise.
              Queries are sent only to the model endpoint you configure, which defaults to Ollama on this machine.
              There is no analytics call and no automatic upload to a third-party AI service.
            </p>
            <p className="mt-3 max-w-3xl leading-7 text-muted">
              Local processing does not make the whole computer secure. Anyone who can use this installation can read
              the documents it stores. This first release is a trusted single-user application, not a multi-tenant
              legal platform.
            </p>
          </div>
        </section>
        <section id="local-ai" className="mx-auto max-w-6xl px-4 py-12">
          <h2 className="font-serif text-3xl text-navy">Local open-weight inference</h2>
          <p className="mt-3 max-w-3xl leading-7 text-muted">
            The default chat model is Llama 3.2 3B through Ollama. Ollama reports that tag at about 2 GB. A practical
            CPU setup is 8 GB of system memory, with 16 GB leaving more room for the browser and the index. A GPU is
            not required. Embeddings default to a local model when one is available: sentence-transformers
            all-MiniLM-L6-v2 if that extra is installed, otherwise Ollama&apos;s nomic-embed-text (about 274 MB in a
            local Ollama library), otherwise deterministic hashing that the interface labels as not semantic.
          </p>
        </section>
        <section className="bg-navy text-white">
          <div className="mx-auto max-w-6xl px-4 py-12">
            <h2 className="font-serif text-3xl">Supported documents</h2>
            <p className="mt-3 max-w-3xl leading-7 text-white/80">
              PDF files only in this release. The file extension, MIME type, PDF signature, size, and page count are
              checked. Text is extracted page by page with PyMuPDF. Scanned pages without a text layer are kept in the
              page list and reported as having no extractable text. OCR is not included, and CiteWise does not invent
              text for those pages.
            </p>
            <h2 className="mt-10 font-serif text-3xl">Limitation</h2>
            <p className="mt-3 max-w-3xl leading-7 text-white/80">
              CiteWise is a document research assistant. It is not a lawyer and it is not a replacement for qualified
              legal advice. It does not contain a database of authorities. It will not treat a matching string as proof
              that a proposition is legally correct. If the uploaded documents do not support an answer, it should say so.
            </p>
          </div>
        </section>
      </main>
      <footer className="mx-auto flex max-w-6xl flex-wrap gap-4 px-4 py-8 text-sm text-muted">
        <a href={`${apiOrigin}/docs`}>API documentation</a>
        <Link to="/app">Demo workspace</Link>
        {repository ? (
          <a href={repository}>Repository</a>
        ) : (
          <span>Repository URL is not configured. The source is this project tree.</span>
        )}
      </footer>
    </div>
  );
}
