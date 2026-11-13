"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import type { DocumentDetail } from "../../lib/catalog";

async function request(path: string, init: RequestInit) {
  const response = await fetch(`/api/kb/${path}`, init);
  if (!response.ok) {
    const { detail } = await response.json().catch(() => ({}));
    throw new Error(typeof detail === "string" ? detail : "Check the form values and try again.");
  }
  return response;
}

function message(error: unknown) {
  return error instanceof Error ? error.message : "The request could not be completed.";
}

export function UploadForm() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    const pdf = fields.get("pdf");
    if (!(pdf instanceof File) || !pdf.size || pdf.size > 8 * 1024 * 1024) {
      setError("Choose a PDF that is 8 MiB or smaller.");
      return;
    }
    const params = new URLSearchParams({
      sku: String(fields.get("sku")).trim().toUpperCase(),
      name: String(fields.get("name")),
      title: String(fields.get("title")),
      revision: String(fields.get("revision")),
      is_demo: String(fields.get("is_demo") === "on"),
    });
    setBusy(true);
    setError("");
    try {
      const response = await request(`documents?${params}`, {
        method: "POST", headers: { "Content-Type": "application/pdf" }, body: pdf,
      });
      const document: DocumentDetail = await response.json();
      router.push(`/documents/${document.id}`);
      router.refresh();
    } catch (error) {
      setError(message(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="product workflow-form" onSubmit={upload}>
      <h2>Upload a datasheet</h2>
      <p className="description">Use a selectable-text PDF with one model, up to 20 pages and 8 MiB.</p>
      <fieldset disabled={busy} className="form-grid">
        <label>Model SKU<input name="sku" required pattern="[A-Za-z0-9][A-Za-z0-9._\-]{0,39}" placeholder="e.g. FIXTURE-S2" /></label>
        <label>Model name<input name="name" required maxLength={120} placeholder="e.g. Synthetic Inspection Sonar" /></label>
        <label>Document title<input name="title" required maxLength={120} /></label>
        <label>Revision<input name="revision" required maxLength={40} placeholder="e.g. Rev A" /></label>
        <label className="wide">PDF file<input name="pdf" type="file" accept="application/pdf,.pdf" required /></label>
        <label className="check wide"><input type="checkbox" name="is_demo" /> Synthetic or demonstration data</label>
        <div className="wide"><button className="primary-button" type="submit">{busy ? "Processing PDF…" : "Upload and extract"}</button></div>
      </fieldset>
      {error && <p className="form-error" role="alert">{error}</p>}
    </form>
  );
}

export function ArchiveButton({ id, archived }: { id: number; archived: boolean }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function toggle() {
    setBusy(true);
    setError("");
    try {
      await request(`documents/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ archived: !archived }),
      });
      router.refresh();
    } catch (error) {
      setError(message(error));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div>
      <button className="secondary-button" onClick={toggle} disabled={busy}>{archived ? "Restore revision" : "Archive revision"}</button>
      {error && <p className="form-error" role="alert">{error}</p>}
    </div>
  );
}

export function ReviewControls({ assertion }: { assertion: DocumentDetail["assertions"][number] }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function review(action: "approve" | "reject" | "correct", form?: HTMLFormElement) {
    const fields = form ? new FormData(form) : null;
    setBusy(true);
    setError("");
    try {
      await request(`assertions/${assertion.id}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          ...(fields && { value: fields.get("value"), quote: fields.get("quote") }),
        }),
      });
      router.refresh();
    } catch (error) {
      setError(message(error));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="review-controls">
      <div className="flex flex-wrap gap-2">
        <button className="primary-button" disabled={busy} onClick={() => review("approve")}>Approve</button>
        <button className="secondary-button" disabled={busy} onClick={() => review("reject")}>Reject</button>
      </div>
      <details>
        <summary>Correct and approve</summary>
        <form className="form-grid" onSubmit={(event) => { event.preventDefault(); void review("correct", event.currentTarget); }}>
          <label className="wide">Exact corrected value<input name="value" required maxLength={160} defaultValue={assertion.value} /></label>
          <label className="wide">Exact quote from this section<textarea name="quote" required maxLength={600} defaultValue={assertion.evidence_quote} /></label>
          <div><button className="primary-button" disabled={busy}>Save correction</button></div>
        </form>
      </details>
      {error && <p className="form-error" role="alert">{error}</p>}
    </div>
  );
}
