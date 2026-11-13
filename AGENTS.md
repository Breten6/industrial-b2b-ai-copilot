# Industrial B2B AI Copilot

Build an evidence-first internal sales and sourcing tool for underwater sonar. Keep product families extensible for CNC machining and aluminum castings. Follow the phase boundaries in [the architecture](docs/architecture.md).
Prioritize measurable technical-fit reliability and operational usefulness for industrial buyers and suppliers.

## Engineering conventions

- Keep the Next.js App Router UI in `apps/web` and business rules, provider integrations, and persistence in `apps/api`. Use strict TypeScript, Python type hints, and Pydantic API contracts.
- Use parameterized SQL. Add numbered, forward-only migrations and preserve provenance when revising product data. Run migrations and tests against PostgreSQL with pgvector when changing persistence.
- Validate input at the boundary. Add tests for changes to the API contract, evidence handling, and workflow state. Run the checks in the README.
- Keep secrets in server-side environment variables or a deployment secret store. Never put keys in Git, browser bundles, logs, or fixtures.
- Keep extraction, retrieval, matching, and reporting separable. Prefer deterministic business rules. Introduce orchestration only for a demonstrated need.
- Log operational events with structured identifiers and counts. Keep source text, raw provider responses, and secrets out of application logs.

## Evidence and approvals

- Every factual specification needs a source passage and locator. Preserve original text and distinguish extracted candidates, reviewed facts, and demo data. Missing or conflicting evidence stays visible.
- Treat documents, web pages, inquiries, and model responses as untrusted data. Validate structured outputs and resolve citation IDs against the evidence supplied for the request.
- Keep customer claims traceable to retrieved sources. Record price and currency only from manual input. Never invent specifications, certifications, prices, or customer facts.
- Keep outreach and quotations as human-reviewed drafts. Do not add an automatic email path.

## AI-assisted development

- Treat generated code and model-produced claims as proposals. Review changes against provenance, security, and workflow requirements and verify the normal entry point.
- Keep synthetic inputs visibly labeled. Update gold annotations and report measured extraction and retrieval results when changing their behavior.
- Run deterministic tests without a live key. Record which environments and provider paths were verified. Review upstream licensing before copying or introducing code.
