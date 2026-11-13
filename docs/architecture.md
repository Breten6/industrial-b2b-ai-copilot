# Industrial B2B AI Copilot architecture

The first release is an evidence-backed sonar knowledge base. It serves industrial sales and sourcing and demonstrates typed extraction, retrieval evaluation, database provenance, and approval workflows. Later phases will use these capabilities to assess technical fit for industrial buyers, ROV integrators, inspection companies, and OEMs.

## Boundaries

```text
Browser -> Next.js -> FastAPI -> PostgreSQL + pgvector
                         |----> private, content-addressed PDF storage
                         +----> local provider or opt-in OpenAI adapter
```

| Location | Responsibility |
| --- | --- |
| `apps/web/app` | Catalog, datasheet and comparison screens, plus an allowlisted same-origin API proxy. |
| `apps/api/app` | PDF parsing and evidence validation, document workflow, retrieval, API schemas, provider and storage adapters. |
| `apps/api/migrations` | Forward-only schema changes and the original labeled demo seed. |
| `apps/api/examples` | Generated synthetic PDFs and gold annotations. |
| `apps/api/tests`, `apps/web/tests` | API, evidence, retrieval, comparison and stack checks. |
| `compose.yaml`, `.github/workflows` | Reproducible local stack and CI. |

The browser never receives provider credentials. Uploaded PDFs are read as data, parsed into page sections, and indexed separately from reviewable specification assertions. Search can show raw page evidence. Comparison only consumes reviewed assertions and explicitly labeled fixtures. A human verifies field meaning, model identity, and qualifiers before approval.

## Data model

| Table | Evidence and integrity |
| --- | --- |
| `product_families`, `products` | Product family and stable SKU. The current upload form creates sonar models. |
| `source_documents` | SKU relationship, title, revision, SHA-256, size, page count, demo flag, and archive state. A matching retry returns the existing revision. |
| `source_passages` | Document, one-based page number, section locator, and extracted text. Original PDFs live in private object storage. |
| `passage_embeddings` | Passage ID, embedding model/version, and 256-dimensional vector. A query only compares vectors from the same model. |
| `spec_assertions` | Canonical specification key, source-written value and qualifiers, exact quote, publication state, and document/passage references. Composite foreign keys prevent cross-product citations. |
| `spec_review_events` | Review action, prior and resulting value and quote, and timestamp. A review locks the candidate and document while applying the change. |
| `schema_migrations` | Applied migration filenames. |

An archive hides the revision's evidence from active search and comparison. Restoring a revision restores its previous review state. Conflicting reviewed values remain visible with their respective sources. The system preserves source-written units and makes no conversion or compatibility decision.

## Core API

| Endpoint | Contract |
| --- | --- |
| `GET /v1/catalog?q=...` | Product and reviewed-value matching, PostgreSQL full-text retrieval, pgvector cosine retrieval, and a cited passage when one matches. |
| `GET /v1/compare?sku=A&sku=B` | Two to four models in request order, with the published assertions used by the comparison matrix. |
| `POST /v1/documents` | Raw `application/pdf` body and `sku`, `name`, `title`, `revision`, optional `is_demo` query parameters. Returns the revision and candidates. |
| `GET /v1/documents`, `GET /v1/documents/{id}` | List revisions or inspect candidates and page sections. |
| `GET /v1/documents/{id}/file` | Download the original PDF as an attachment. |
| `PATCH /v1/documents/{id}` | Archive or restore with `{"archived": true}` or `false`. |
| `POST /v1/assertions/{id}/review` | Approve, reject, or correct a pending assertion. Corrections require the exact value and supporting quote in the same passage. |
| `GET /healthz`, `GET /v1/provider` | Service liveness and provider mode without credentials. |

## Technical decisions

1. **Reuse the monorepo and PostgreSQL.** Next.js handles rendering and same-origin access. FastAPI owns domain and persistence rules. PostgreSQL can provide full-text and vector retrieval together for the initial catalog. Exact scans keep ranking simple at this scale. Measure retrieval quality and latency before adding approximate indexes or a separate search service.
2. **Use pypdf for selectable text and retain the original asset.** Page order and table layout can be ambiguous. Keep the exact extracted text and show it to reviewers. Reject invalid, encrypted, oversized and image-only files. Synchronous ingestion limits request and operational complexity. Before broader deployment, isolate parsing in a resource-limited worker, add malware scanning, and add authentication and authorization.
3. **Separate candidate generation from evidence and approval.** The mock adapter extracts labeled lines and supplies deterministic domain-synonym vectors. The opt-in OpenAI adapter uses Responses Structured Outputs and a separate embeddings request. The server checks passage IDs, quote membership, complete labeled values, and allowed keys. Schema validity alone cannot establish meaning. Human review remains necessary. The phase needs neither tool calling nor an orchestration framework. [Official OpenAI documentation for Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
4. **Keep storage and provider seams small.** Storage uses content hashes and atomic file writes. Revision and index records commit in one database transaction. A failed database transaction can leave an unreferenced blob. There is no automatic purge. OpenAI failures are bounded and sanitized, and search can still use keyword retrieval. Switching providers leaves previous revisions searchable by keyword until their embeddings are rebuilt. Phase 1 has no reindex UI.
5. **Keep Phase 1 single-user and local.** Compose publishes only the web service on loopback. The web service accepts loopback hosts and the upload proxy enforces an origin check and request limits. Downloads use attachment headers. Application event logs carry identifiers and counts. Persisted review events have no authenticated reviewer identity until authentication is added.

## Roadmap

| Phase | Acceptance target |
| --- | --- |
| 1 · Product knowledge base | Upload sonar PDF revisions, extract and review cited specifications, retrieve page evidence, compare models, and reproduce fixture evaluations. |
| 2 · Lead research and technical fit | Add companies, research runs, permitted public source snapshots, application hypotheses, requirement-to-product matches, and evidence-linked reports. Bound URL fetching and block private networks. Report limitations and missing confirmations. |
| 3 · Sales copilot | Add opportunities, research notes, communications, and immutable English draft revisions. Tie human approval to a revision and keep external delivery outside the MVP. |
| 4 · RFQ assistant | Parse PDF, email text and spreadsheet inquiries. Add requirement assertions, clarification questions, and quote drafts with decimal prices, currencies, and explicit cost assumptions from an authorized user. |

See [the upstream review](upstream-review.md) for build-versus-reuse decisions.
