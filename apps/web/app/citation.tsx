import Link from "next/link";
import type { Citation } from "../lib/catalog";

export function Source({ citation, label = "View source" }: { citation: Citation; label?: string }) {
  return (
    <details>
      <summary>{label}</summary>
      <div className="citation">
        <p className="font-semibold">{citation.document}</p>
        <p>{citation.revision} · {citation.locator}</p>
        <blockquote>{citation.excerpt}</blockquote>
        {citation.document_id !== null && (
          <Link className="text-link" href={`/documents/${citation.document_id}`}>Open datasheet evidence</Link>
        )}
        {citation.is_demo && <p className="text-xs">Synthetic evidence for demonstration.</p>}
      </div>
    </details>
  );
}
