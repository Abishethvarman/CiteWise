import { useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";

pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();

export function PdfPane({ url, page, title }: { url: string | null; page: number; title: string }) {
  const [pages, setPages] = useState(0);
  const [failed, setFailed] = useState("");
  if (!url) {
    return <p className="p-6 text-sm text-muted">Select a document to open the PDF at its extracted page.</p>;
  }
  return (
    <div className="h-full overflow-auto bg-white">
      <p className="border-b border-line px-4 py-2 text-xs text-muted">
        {title} · PDF page {page}
        {pages ? ` of ${pages}` : ""}
      </p>
      {failed && (
        <p role="alert" className="p-4 text-sm text-rose">
          {failed}
        </p>
      )}
      <Document
        file={url}
        onLoadSuccess={(info) => {
          setPages(info.numPages);
          setFailed("");
        }}
        onLoadError={() => setFailed("The PDF could not be displayed. The extracted text is still available in the evidence panel.")}
        loading={<p className="p-4 text-sm">Loading PDF…</p>}
      >
        <Page pageNumber={page} width={640} renderTextLayer={false} renderAnnotationLayer={false} />
      </Document>
    </div>
  );
}
