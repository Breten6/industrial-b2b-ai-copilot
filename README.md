# Industrial B2B AI Copilot

An evidence-first internal workspace for industrial sales, technical product matching, and sourcing. The first release is a sonar knowledge base for teams that need to trace specifications to the original datasheet before making a product recommendation.

## Start locally

Install Docker with Compose v2. On Windows, use Docker Desktop with Linux containers. Run from the repository root.

```powershell
docker compose up --build -d
docker compose ps
```

Open [the local workspace](http://127.0.0.1:3000). Compose applies database migrations and enables pgvector. Only the web service is published on loopback. The API, database, and private PDF storage stay behind it. The default mock provider requires no key and makes no external requests.

Copy `.env.example` to `.env` to configure a fresh database or select an AI provider. For optional live OpenAI extraction and semantic search, set `COPILOT_PROVIDER=openai` and `OPENAI_API_KEY` in that file and recreate the API service. This mode sends extracted document text and search queries to OpenAI. Use it only for material you are authorized to share with that provider. The mock provider keeps processing local. [Official OpenAI documentation for embeddings](https://developers.openai.com/api/docs/guides/embeddings)

```powershell
docker compose logs migrate api web
docker compose down
```

The named database and PDF volumes survive `docker compose down`. Back them up together. The Compose project name retains its original value so existing Phase 1 starter volumes still resolve.

## Try the Phase 1 workflow

1. In **Datasheets**, upload [fixture-s2.pdf](apps/api/examples/fixture-s2.pdf) as SKU `FIXTURE-S2`, with model name `Synthetic Inspection Sonar`, document title `Synthetic Inspection Datasheet`, and revision `A`. Check **Synthetic or demonstration data**.
2. Check the page and exact quote for each candidate. Approve the operating frequency and interface, or reject a candidate to keep it out of comparison. The original PDF is available as a download.
3. Upload [fixture-s4.pdf](apps/api/examples/fixture-s4.pdf) as `FIXTURE-S4` with its own model name and title, mark it synthetic, and review its candidates.
4. Search **Catalog** for `fixture-beacon-alpha` to find a page by keyword. Try `network power` for a vector match to the interface and supply-voltage passage in the mock provider.
5. Select both SKUs in **Compare**. Missing approvals appear as missing reviewed evidence. Conflicting reviewed values retain their own citations. Archive a revision in **Datasheets** to remove its passages and assertions from active retrieval.

The fixture measurements are synthetic. The [demo scenarios and evaluation](docs/evaluation.md) explain their expected outcomes.

## Run the checks

With the local stack running, execute the backend tests against a disposable demo database. CI uses a fresh Compose project.

```powershell
docker compose run --rm --no-deps -e COPILOT_PROVIDER=mock -e COVERAGE_FILE=/tmp/copilot.coverage api python -m pytest --cov=app --cov-report=term-missing
```

From `apps/web`, with Node.js 24 installed.

```powershell
npm ci
npm run typecheck
npm test
npm run build
```

From `apps/api`, with Python 3.12 installed, run the tests that require neither a database nor an API key.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -m "not integration"
```

## Scope and implementation

- [Architecture, data model, REST API, decisions, and roadmap](docs/architecture.md)
- [Reference repositories and build-versus-reuse decisions](docs/upstream-review.md)
- [Synthetic evaluation and results](docs/evaluation.md)
- [Engineering conventions](AGENTS.md)

The codebase implements PDF ingestion, source validation, review, hybrid retrieval, and side-by-side comparison. Phase 1 handles one sonar model per selectable-text PDF, with an 8 MiB and 20-page limit. Image-only PDFs need OCR before upload, and complex tables require human validation. It is a single-user local application. Authentication, parser isolation, and malware scanning are prerequisites for shared deployment.

Lead research and technical fit, outreach approval, and RFQ assistance are Phases 2–4. No delivery or automated messaging integration is included.
