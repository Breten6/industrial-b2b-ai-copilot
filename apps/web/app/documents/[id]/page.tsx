import Link from "next/link";
import { notFound } from "next/navigation";
import { readDocument } from "../../../lib/catalog";
import { ArchiveButton, ReviewControls } from "../actions";

export default async function Datasheet({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^\d{1,10}$/.test(id)) notFound();
  const document = await readDocument(id);
  if (!document) {
    return <main className="frame workflow-page"><p role="alert">This revision is missing or temporarily unavailable.</p><Link className="text-link" href="/documents">Back to datasheets</Link></main>;
  }
  const passages = new Map(document.passages.map((passage) => [passage.id, passage]));
  return (
    <main className="frame workflow-page">
      <Link href="/documents" className="text-link">← Datasheets</Link>
      <h1>{document.title}</h1>
      <div className="flex flex-wrap items-center gap-2">
        <p className="description">{document.sku} · {document.revision} · {document.page_count} pages</p>
        {document.is_demo && <span className="badge">Synthetic evidence</span>}
        {document.archived && <span className="badge">Archived</span>}
      </div>
      <div className="document-actions">
        <a className="secondary-button" href={`/api/kb/documents/${id}/file`}>Download original PDF</a>
        <ArchiveButton id={document.id} archived={document.archived} />
      </div>
      <div className="workflow-split">
        <section aria-labelledby="candidates-title">
          <h2 id="candidates-title">Specification review</h2>
          <p className="description">Check the value, model, and qualifying conditions against the source before approval.</p>
          {!document.assertions.length && <p className="empty">No specification candidates found. Page evidence is still available.</p>}
          <div className="workflow-stack">
            {document.assertions.map((assertion) => (
              <article className="product" key={assertion.id}>
                <div className="flex items-start justify-between gap-3">
                  <div><h3>{assertion.label}</h3><p>{assertion.value}</p></div>
                  <span className="badge">{assertion.review_state === "candidate" ? "Pending review" : assertion.review_state}</span>
                </div>
                <blockquote className="citation">{assertion.evidence_quote}</blockquote>
                <a className="text-link" href={`#passage-${assertion.passage_id}`}>{passages.get(assertion.passage_id)?.locator}</a>
                {assertion.review_state === "candidate" && !document.archived && <ReviewControls assertion={assertion} />}
              </article>
            ))}
          </div>
        </section>
        <section aria-labelledby="passages-title">
          <h2 id="passages-title">Extracted page evidence</h2>
          <p className="description">Page numbers refer to the uploaded PDF. Check the original when text order is ambiguous.</p>
          <div className="workflow-stack">
            {document.passages.map((passage) => (
              <article className="product" key={passage.id} id={`passage-${passage.id}`}>
                <h3>{passage.locator}</h3>
                <pre className="passage">{passage.excerpt}</pre>
              </article>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
