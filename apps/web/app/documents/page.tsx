import Link from "next/link";
import { listDocuments } from "../../lib/catalog";
import { UploadForm } from "./actions";

export default async function Datasheets() {
  const documents = await listDocuments();
  return (
    <main className="frame workflow-page">
      <p className="eyebrow">02 / EVIDENCE LIBRARY</p>
      <h1>Datasheets</h1>
      <p className="description">Upload a revision, inspect extracted passages, and review candidates against the original source.</p>
      <div className="workflow-split">
        <UploadForm />
        <section className="product" aria-labelledby="revision-list">
          <h2 id="revision-list">Document revisions</h2>
          {documents === null ? (
            <p role="alert" className="description">The document library is temporarily unavailable.</p>
          ) : documents.length === 0 ? (
            <p className="description">Uploaded PDF revisions will appear here.</p>
          ) : (
            <ul className="revision-list">
              {documents.map((document) => (
                <li key={document.id}>
                  <Link className="text-link" href={`/documents/${document.id}`}>{document.title}</Link>
                  <p className="description">{document.sku} · {document.revision} · {document.page_count} pages</p>
                  <div className="flex flex-wrap gap-2">
                    <span className="badge">{document.archived ? "Archived" : "Active"}</span>
                    {document.is_demo && <span className="badge">Synthetic</span>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
