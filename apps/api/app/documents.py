import hashlib
import logging
from typing import Literal

import psycopg
from pydantic import BaseModel, Field

from app.database import connect
from app.extraction import LABELS, grounded_proposals, read_pdf, supports_value
from app.provider import LLMProvider, ProviderError, vector_literal
from app.storage import DocumentStorage

logger = logging.getLogger(__name__)


class DocumentConflict(ValueError):
    pass


class DocumentSummary(BaseModel):
    id: int
    sku: str
    title: str
    revision: str
    page_count: int
    is_demo: bool
    archived: bool


class EvidencePassage(BaseModel):
    id: int
    page_number: int
    locator: str
    excerpt: str


class DocumentAssertion(BaseModel):
    id: int
    passage_id: int
    label: str
    value: str
    evidence_quote: str
    review_state: Literal["candidate", "reviewed", "rejected"]


class DocumentDetail(DocumentSummary):
    passages: list[EvidencePassage]
    assertions: list[DocumentAssertion]


class ReviewRequest(BaseModel):
    action: Literal["approve", "correct", "reject"]
    value: str | None = Field(default=None, max_length=160)
    quote: str | None = Field(default=None, max_length=600)


SUMMARY = """
    SELECT d.id, p.sku, d.title, d.revision, d.page_count, d.is_demo,
           d.archived_at IS NOT NULL AS archived
    FROM source_documents d JOIN products p ON p.id = d.product_id
    WHERE d.asset_sha256 IS NOT NULL
"""


def list_documents() -> list[DocumentSummary]:
    with connect() as connection:
        return [
            DocumentSummary.model_validate(row)
            for row in connection.execute(SUMMARY + " ORDER BY d.id DESC LIMIT 100")
        ]


def get_document(document_id: int) -> DocumentDetail | None:
    with connect() as connection:
        summary = connection.execute(SUMMARY + " AND d.id = %s", (document_id,)).fetchone()
        if summary is None:
            return None
        passages = connection.execute(
            "SELECT id, page_number, locator, excerpt FROM source_passages WHERE document_id = %s ORDER BY id",
            (document_id,),
        ).fetchall()
        assertions = connection.execute(
            """
            SELECT id, passage_id, label, value, evidence_quote, review_state
            FROM spec_assertions WHERE document_id = %s ORDER BY id
            """,
            (document_id,),
        ).fetchall()
    return DocumentDetail.model_validate({**summary, "passages": passages, "assertions": assertions})


def matching_document(connection, sku: str, title: str, revision: str, digest: str) -> int | None:
    rows = connection.execute(
        """
        SELECT d.id, d.title, d.revision, d.asset_sha256 FROM source_documents d
        JOIN products p ON p.id = d.product_id WHERE p.sku = %s
        AND (d.asset_sha256 = %s OR (d.title = %s AND d.revision = %s))
        """,
        (sku, digest, title, revision),
    )
    for row in rows:
        if (row["title"], row["revision"], row["asset_sha256"]) != (title, revision, digest):
            raise DocumentConflict("PDF content and revision must match an existing upload or use a new revision.")
        return row["id"]
    return None


def ingest(
    storage: DocumentStorage,
    provider: LLMProvider,
    data: bytes,
    *,
    sku: str,
    name: str,
    title: str,
    revision: str,
    is_demo: bool,
) -> int:
    digest = hashlib.sha256(data).hexdigest()
    with connect() as connection:
        product = connection.execute(
            "SELECT name, is_demo FROM products WHERE sku = %s", (sku,)
        ).fetchone()
        if product and (product["name"], product["is_demo"]) != (name, is_demo):
            raise DocumentConflict("Use the existing model name and demo setting for this SKU.")
        existing = matching_document(connection, sku, title, revision, digest)
        if existing is not None:
            storage.store(data)
            return existing

    page_count, passages = read_pdf(data)
    proposals = grounded_proposals(passages, provider.extract(passages))
    vectors = provider.embed([passage.text for passage in passages])
    if len(vectors) != len(passages):
        raise ProviderError("Incorrect embedding count")
    vector_values = [vector_literal(vector) for vector in vectors]
    storage.store(data)

    with connect() as connection:
        connection.execute(
            """
            INSERT INTO products (family_slug, sku, name, description, is_demo)
            VALUES ('sonar', %s, %s, 'Model added from a supplied datasheet.', %s)
            ON CONFLICT (sku) DO NOTHING
            """,
            (sku, name, is_demo),
        )
        product = connection.execute(
            "SELECT id, name, is_demo FROM products WHERE sku = %s FOR UPDATE", (sku,)
        ).fetchone()
        if (product["name"], product["is_demo"]) != (name, is_demo):
            raise DocumentConflict("Use the existing model name and demo setting for this SKU.")
        existing = matching_document(connection, sku, title, revision, digest)
        if existing is not None:
            return existing
        document_id = connection.execute(
            """
            INSERT INTO source_documents (product_id, title, revision, is_demo, asset_sha256, byte_size, page_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (product["id"], title, revision, is_demo, digest, len(data), page_count),
        ).fetchone()["id"]
        passage_ids = []
        for passage, vector in zip(passages, vector_values, strict=True):
            passage_id = connection.execute(
                """
                INSERT INTO source_passages (document_id, locator, excerpt, page_number)
                VALUES (%s, %s, %s, %s) RETURNING id
                """,
                (document_id, passage.locator, passage.text, passage.page),
            ).fetchone()["id"]
            passage_ids.append(passage_id)
            connection.execute(
                "INSERT INTO passage_embeddings VALUES (%s, %s, %s::vector)",
                (passage_id, provider.embedding_model, vector),
            )
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO spec_assertions
                    (product_id, document_id, passage_id, spec_key, label, value, evidence_quote, review_state)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'candidate')
                """,
                [
                    (product["id"], document_id, passage_ids[p.passage], p.key, LABELS[p.key], p.value, p.quote)
                    for p in proposals
                ],
            )
    logger.info(
        "document_ingested",
        extra={"document_id": document_id, "page_count": page_count, "candidate_count": len(proposals)},
    )
    return document_id


def set_archive(document_id: int, archived: bool) -> bool:
    with connect() as connection:
        return connection.execute(
            """
            UPDATE source_documents SET archived_at = CASE WHEN %s THEN COALESCE(archived_at, now()) END
            WHERE id = %s AND asset_sha256 IS NOT NULL
            """,
            (archived, document_id),
        ).rowcount == 1


def download(storage: DocumentStorage, document_id: int) -> bytes | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT asset_sha256 FROM source_documents WHERE id = %s AND asset_sha256 IS NOT NULL",
            (document_id,),
        ).fetchone()
    return None if row is None else storage.read(row["asset_sha256"])


def review(assertion_id: int, request: ReviewRequest) -> bool:
    with connect() as connection:
        current = connection.execute(
            """
            SELECT s.value, s.evidence_quote, s.review_state, s.spec_key, p.excerpt, d.archived_at
            FROM spec_assertions s
            JOIN source_passages p ON p.id = s.passage_id
            JOIN source_documents d ON d.id = s.document_id
            WHERE s.id = %s AND d.asset_sha256 IS NOT NULL
            FOR UPDATE OF s, d
            """,
            (assertion_id,),
        ).fetchone()
        if current is None:
            return False
        if current["review_state"] != "candidate" or current["archived_at"] is not None:
            raise DocumentConflict("Only pending candidates from active documents can be reviewed.")
        value = current["value"]
        quote = current["evidence_quote"]
        if request.action == "correct":
            if not request.value or not request.quote or not supports_value(
                current["excerpt"], request.quote, request.value, current["spec_key"]
            ):
                raise DocumentConflict("Copy the corrected value and an exact supporting quote from the cited section.")
            value, quote = request.value, request.quote
        state = "rejected" if request.action == "reject" else "reviewed"
        connection.execute(
            "UPDATE spec_assertions SET value = %s, evidence_quote = %s, review_state = %s WHERE id = %s",
            (value, quote, state, assertion_id),
        )
        connection.execute(
            """
            INSERT INTO spec_review_events
                (assertion_id, action, prior_value, prior_quote, resulting_value, resulting_quote)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (assertion_id, request.action, current["value"], current["evidence_quote"], value, quote),
        )
    logger.info("assertion_reviewed", extra={"assertion_id": assertion_id, "action": request.action})
    return True
