import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { randomBytes } from "node:crypto";

const base = "http://127.0.0.1:3000";
const sku = `SMOKE-${randomBytes(4).toString("hex").toUpperCase()}`;
const pdf = await readFile(new URL("../../api/examples/fixture-s2.pdf", import.meta.url));
const params = new URLSearchParams({
  sku, name: "Synthetic smoke test sonar", title: "Synthetic test sheet", revision: "A", is_demo: "true",
});
const uploadPath = `/api/kb/documents?${params}`;

function request(path, options = {}) {
  return fetch(base + path, { signal: AbortSignal.timeout(30_000), ...options });
}

const crossOrigin = await request(uploadPath, {
  method: "POST", body: pdf, headers: { Origin: "http://example.invalid", "Content-Type": "application/pdf" },
});
assert.equal(crossOrigin.status, 403);

const upload = await request(uploadPath, {
  method: "POST", body: pdf, headers: { Origin: base, "Content-Type": "application/pdf" },
});
assert.equal(upload.status, 201, await upload.clone().text());
const document = await upload.json();
const frequency = document.assertions.find((assertion) => assertion.label === "Operating frequency");
assert.equal(frequency.review_state, "candidate");
try {
  const review = await request(`/api/kb/assertions/${frequency.id}/review`, {
    method: "POST",
    headers: { Origin: base, "Content-Type": "application/json" },
    body: JSON.stringify({ action: "approve" }),
  });
  assert.equal(review.status, 204, await review.text());
  const comparison = await request(`/compare?sku=${sku}&sku=DEMO-IMG`);
  assert.equal(comparison.status, 200);
  const html = await comparison.text();
  assert.match(html, /Operating frequency: 900 kHz/);
  assert.match(html, /No reviewed evidence/);
} finally {
  await request(`/api/kb/documents/${document.id}`, {
    method: "PATCH",
    headers: { Origin: base, "Content-Type": "application/json" },
    body: JSON.stringify({ archived: true }),
  });
}
