# Phase 1 evaluation

The fixtures represent fictional sonar models. They are intended to test software behavior and provide no product or customer evidence.

## Reproduce the evaluation

The checked-in [gold annotations](../apps/api/examples/gold.json) specify the expected key, exact displayed value, and one-based PDF page for each extracted assertion. Run the backend tests in the [README](../README.md). To regenerate the PDFs after editing the fixture definitions, run `python examples/make_pdfs.py` from `apps/api`.

| Measure | Deterministic fixture result |
| --- | --- |
| Exact key and value precision | 6 of 6 emitted assertions matched gold. |
| Exact key and value recall | 6 of 6 expected assertions were emitted. |
| Citation page accuracy | 6 of 6 matched the expected PDF page. |
| Grounding rejection | Synthetic wrong-page, invented-quote, partial-number, incomplete-unit and wrong-field proposals are rejected. |
| Retrieval checks | The keyword anchor and vector synonym query both returned the expected second page in the integration suite. |
| Review and comparison | Pending and rejected candidates stay out of published specifications. The comparison helper preserves conflicts and represents missing evidence explicitly. |

These results apply to the labeled-line mock adapter and the small synthetic dataset. They do not estimate performance on real vendor PDFs or live OpenAI extraction. The test suite exercises malformed and incomplete OpenAI responses using stubs.

## Synthetic technical-fit scenarios

- **Inspection integrator.** A fictional ROV team requests an Ethernet interface and a 400 m rating. Fixture S2's reviewed Ethernet value addresses the interface question, and its synthetic 300 m rating falls short. Connector, protocol, and operating conditions remain open.
- **Survey OEM.** A fictional survey platform asks for bathymetric mapping support and a specific beam width. Fixture S4 provides a search match for the application language. A missing reviewed beam width blocks a compatibility conclusion. A human would ask for the beam width and the measurement conditions.

These scenarios describe the expected interpretation by a reviewer. Automated technical-fit analysis is a Phase 2 feature.
