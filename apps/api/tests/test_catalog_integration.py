from contextlib import nullcontext

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.database import connect
from app.main import app
from app.migrate import migrate


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def apply_migrations():
    migrate()
    migrate()


def test_catalog_search_returns_traceable_demo_assertions():
    client = TestClient(app)
    result = client.get("/v1/catalog", params={"q": "  DEMO-img  "})
    assert result.status_code == 200
    product, = result.json()["products"]
    assert product["sku"] == "DEMO-IMG"
    assert product["is_demo"] is True
    spec, = product["specifications"]
    assert spec["review_state"] == "demo"
    assert spec["value"] in spec["citation"]["excerpt"]
    assert spec["citation"]["locator"] == "Catalog classification"
    assert spec["citation"]["is_demo"] is True
    assert client.get("/v1/catalog", params={"q": "%"}).json() == {"products": []}


def test_candidates_are_hidden_from_search_and_catalog(monkeypatch):
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO spec_assertions
                (product_id, document_id, passage_id, spec_key, label, value, review_state)
            SELECT s.product_id, s.document_id, s.passage_id,
                   'test_candidate', 'Candidate label', 'Unpublished fixture claim', 'candidate'
            FROM spec_assertions s JOIN products p ON p.id = s.product_id
            WHERE p.sku = 'DEMO-IMG' AND s.spec_key = 'product_category'
            """
        )
        try:
            monkeypatch.setattr("app.catalog.connect", lambda: nullcontext(connection))
            client = TestClient(app)
            product, = client.get("/v1/catalog", params={"q": "DEMO-IMG"}).json()["products"]
            assert [spec["label"] for spec in product["specifications"]] == ["Category"]
            assert client.get("/v1/catalog", params={"q": "Unpublished fixture claim"}).json() == {
                "products": []
            }
        finally:
            connection.rollback()


def test_vector_extension_and_migration_tracking():
    with connect() as connection:
        assert connection.execute("SELECT '[1,2]'::vector::text AS value").fetchone() == {
            "value": "[1,2]"
        }
        assert connection.execute("SELECT count(*) AS count FROM schema_migrations").fetchone() == {
            "count": 3
        }


def test_specification_cannot_cite_a_different_products_document():
    with pytest.raises(psycopg.errors.ForeignKeyViolation), connect() as connection:
        connection.execute(
            """
            INSERT INTO spec_assertions
                (product_id, document_id, passage_id, spec_key, label, value, review_state)
            SELECT product.id, source.document_id, source.passage_id,
                   'invalid_test', 'Invalid test', 'Invalid test', 'candidate'
            FROM products product
            CROSS JOIN spec_assertions source
            JOIN products other ON other.id = source.product_id
            WHERE product.sku = 'DEMO-IMG' AND other.sku = 'DEMO-ALT'
            """
        )
