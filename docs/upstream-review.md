# Build-versus-reuse review

All four repository identities were resolved as public and unarchived through GitHub. A public repository or visible commit history is evidence of availability and activity. It does not establish a maintenance commitment.

| Project | License and activity observed | Relevant design and decision |
| --- | --- | --- |
| [OpenOutbound](https://github.com/xyluxx/openoutbound) | Apache-2.0. The repository described an early 0.x release and its default branch displayed one commit. | Its engine places approvals, send limits, and suppression outside the agent. Use the same separation of approval from generation as a design reference. Its outbound channel stack is outside Phase 1. |
| [Distill AI](https://github.com/Distill-AI/distill-ai) | MIT. GitHub showed a substantial history on the `dev` default branch. Its documentation describes a hackathon MVP, and a maintenance cadence was not established. | Its pipeline separates intake, extraction, semantic SKU mapping, quotation rules, and human approval. This is a useful RFQ reference. The NestJS quote pipeline and outbound integrations do not provide a sonar datasheet provenance model. |
| [OpenOutreach](https://github.com/eracle/OpenOutreach) | GPL-3.0. The accessible [commit history](https://github.com/eracle/OpenOutreach/commits/main/) showed September 2026 changes to qualification and send tooling. | The finder and sender are separate components. Its lead selection and sending workflow is a poor fit for an evidence-first knowledge base and would add copyleft and delivery dependencies to assess. |
| [AI Machining Pipeline](https://github.com/ismael-joffroy-chandoutis/ai-machining-pipeline) | The README declares the demo files MIT-licensed. A root `LICENSE` lookup returned 404, so broader licensing and ongoing maintenance could not be confirmed. | The field report and sample CAD/CAM outputs illustrate staged verification. The multi-agent manufacturing workflow adds no capability needed for Phase 1. |

The implementation uses original application code. Reused components are the declared framework and libraries, including Next.js, Tailwind, FastAPI, Pydantic, psycopg, pypdf, pgvector, and HTTPX2. No code or artifacts from the four reference projects are bundled.
