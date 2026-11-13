import logging
from typing import Literal

from pydantic import BaseModel

from app.database import connect
from app.provider import LLMProvider, ProviderError, vector_literal

logger = logging.getLogger(__name__)


class Citation(BaseModel):
    document: str
    revision: str
    locator: str
    excerpt: str
    is_demo: bool
    document_id: int | None = None
    page_number: int | None = None


class Specification(BaseModel):
    id: int
    key: str
    label: str
    value: str
    unit: str | None
    review_state: Literal["demo", "reviewed"]
    citation: Citation


class Product(BaseModel):
    sku: str
    name: str
    family: str
    description: str
    is_demo: bool
    specifications: list[Specification]
    matched_source: Citation | None = None


def search_catalog(
    query: str, provider: LLMProvider | None = None, *, skus: list[str] | None = None
) -> list[Product]:
    embedding = None
    if query and provider:
        try:
            values, = provider.embed([query])
            if any(values):
                embedding = vector_literal(values)
        except (ProviderError, ValueError):
            logger.warning("search_embedding_unavailable")
    with connect() as connection:
        rows = connection.execute(
            """
            WITH published AS (
                SELECT s.*, d.title, d.revision, d.is_demo, d.asset_sha256, p.locator, p.page_number,
                       COALESCE(s.evidence_quote, p.excerpt) AS excerpt
                FROM spec_assertions s
                JOIN source_documents d ON d.id = s.document_id
                JOIN source_passages p ON p.id = s.passage_id
                JOIN products product ON product.id = s.product_id
                WHERE d.archived_at IS NULL AND d.is_demo = product.is_demo
                  AND (s.review_state = 'reviewed' OR (s.review_state = 'demo' AND d.is_demo))
            ), lexical AS (
                SELECT id AS passage_id,
                       ts_rank(to_tsvector('simple', excerpt), websearch_to_tsquery('simple', %(query)s)) AS keyword
                FROM source_passages
                WHERE %(query)s <> ''
                  AND to_tsvector('simple', excerpt) @@ websearch_to_tsquery('simple', %(query)s)
            ), semantic AS (
                SELECT passage_id, embedding <=> %(embedding)s::vector AS distance
                FROM passage_embeddings
                WHERE model = %(model)s AND %(embedding)s::vector IS NOT NULL
                  AND embedding <=> %(embedding)s::vector < %(distance_limit)s
            ), evidence AS (
                SELECT d.product_id, d.id AS document_id, d.title AS document, d.revision,
                       d.is_demo, p.id, p.page_number, p.locator, left(p.excerpt, 420) AS excerpt,
                       COALESCE(lexical.keyword, 0) AS keyword, semantic.distance
                FROM lexical FULL JOIN semantic USING (passage_id)
                JOIN source_passages p ON p.id = passage_id
                JOIN source_documents d ON d.id = p.document_id
                WHERE d.archived_at IS NULL AND d.asset_sha256 IS NOT NULL
            ), ranked_evidence AS (
                SELECT DISTINCT ON (product_id) * FROM evidence
                ORDER BY product_id, (keyword > 0) DESC,
                         keyword DESC, distance ASC NULLS LAST, id
            )
            SELECT product.sku, product.name, family.name AS family, product.description,
                   product.is_demo,
                   CASE WHEN hit.id IS NOT NULL THEN to_jsonb(hit) END AS matched_source,
                   COALESCE((
                       SELECT jsonb_agg(jsonb_build_object(
                           'id', s.id, 'key', s.spec_key, 'label', s.label, 'value', s.value, 'unit', s.unit,
                           'review_state', s.review_state, 'citation', jsonb_build_object(
                               'document', s.title, 'revision', s.revision, 'locator', s.locator,
                               'excerpt', s.excerpt, 'is_demo', s.is_demo,
                               'page_number', s.page_number,
                               'document_id', CASE WHEN s.asset_sha256 IS NOT NULL THEN s.document_id END
                           )
                       ) ORDER BY s.spec_key, s.id)
                       FROM published s WHERE s.product_id = product.id
                   ), '[]'::jsonb) AS specifications
            FROM products product
            JOIN product_families family ON family.slug = product.family_slug
            LEFT JOIN ranked_evidence hit ON hit.product_id = product.id
            WHERE (%(skus)s::text[] IS NULL OR product.sku = ANY(%(skus)s::text[]))
              AND (%(skus)s::text[] IS NOT NULL OR EXISTS (
                       SELECT 1 FROM source_documents d WHERE d.product_id = product.id AND d.archived_at IS NULL
                   ))
              AND (%(query)s = '' OR hit.id IS NOT NULL
               OR strpos(lower(concat_ws(' ', product.sku, product.name, product.description,
                                         family.name)), lower(%(query)s)) > 0
               OR EXISTS (
                   SELECT 1 FROM published s WHERE s.product_id = product.id
                   AND strpos(lower(concat_ws(' ', s.label, s.value, s.unit)), lower(%(query)s)) > 0
               ))
            ORDER BY (lower(product.sku) = lower(%(query)s)) DESC,
                     COALESCE(hit.keyword, 0) DESC, hit.distance ASC NULLS LAST,
                     product.name, product.sku
            LIMIT 50
            """,
            {
                "query": query,
                "embedding": embedding,
                "model": provider.embedding_model if provider else None,
                "distance_limit": 0.70 if provider and not provider.capabilities().external_requests else 0.62,
                "skus": skus,
            },
        )
        return [Product.model_validate(row) for row in rows]
