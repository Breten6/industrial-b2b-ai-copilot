from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import connect
from app.main import create_app
from app.migrate import migrate
from app.provider import MockProvider
from app.storage import LocalStorage


pytestmark = pytest.mark.integration
EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_upload_review_retrieval_compare_and_archive(tmp_path):
    migrate()
    client = TestClient(create_app(MockProvider(), LocalStorage(tmp_path)))
    sku = f"TEST-{uuid4().hex[:8].upper()}"
    params = {"sku": sku, "name": "Synthetic test sonar", "title": "Synthetic fixture", "revision": "A", "is_demo": "true"}
    pdf = (EXAMPLES / "fixture-s2.pdf").read_bytes()
    headers = {"Content-Type": "application/pdf"}
    route = "/v1/documents"
    try:
        upload = client.post(route, content=pdf, headers=headers, params=params)
        assert upload.status_code == 201, upload.text
        document = upload.json()
        document_url = f"{route}/{document['id']}"
        assert len(document["assertions"]) == 4
        assert client.post(route, content=pdf, headers=headers, params=params).json()["id"] == document["id"]
        assert client.post(route, content=pdf, headers=headers, params={**params, "revision": "B"}).status_code == 409
        download = client.get(document_url + "/file")
        assert download.content == pdf
        assert download.headers["content-disposition"].startswith("attachment")
        assert not client.get("/v1/catalog", params={"q": sku}).json()["products"][0]["specifications"]

        interface = next(a for a in document["assertions"] if a["label"] == "Interface")
        assertion_url = f"/v1/assertions/{interface['id']}/review"
        assert client.post(assertion_url, json={"action": "correct", "value": "Ether", "quote": "Interface: Ethernet"}).status_code == 409
        assert client.post(assertion_url, json={"action": "correct", "value": "Ethernet", "quote": "Interface: Ethernet"}).status_code == 204
        assert client.post(assertion_url, json={"action": "reject"}).status_code == 409
        rejected = next(a for a in document["assertions"] if a["label"] == "Depth rating")
        assert client.post(f"/v1/assertions/{rejected['id']}/review", json={"action": "reject"}).status_code == 204
        query = client.get("/v1/catalog", params={"q": "fixture-beacon-alpha"}).json()["products"]
        hit = next(p for p in query if p["sku"] == sku)
        assert hit["matched_source"]["page_number"] == 2
        assert [spec["value"] for spec in hit["specifications"]] == ["Ethernet"]
        assert hit["specifications"][0]["citation"]["page_number"] == 2
        semantic = client.get("/v1/catalog", params={"q": "network power"}).json()["products"]
        assert any(p["sku"] == sku and p["matched_source"]["page_number"] == 2 for p in semantic)
        comparison = client.get("/v1/compare", params=[("sku", sku), ("sku", "DEMO-IMG")]).json()["products"]
        assert [p["sku"] for p in comparison] == [sku, "DEMO-IMG"]
        assert client.patch(document_url, json={"archived": True}).status_code == 204
        assert not client.get("/v1/catalog", params={"q": sku}).json()["products"]
        assert client.patch(document_url, json={"archived": False}).status_code == 204
        assert client.get(document_url).json()["archived"] is False
        with connect() as connection:
            event = connection.execute(
                "SELECT action, prior_value FROM spec_review_events WHERE assertion_id = %s", (interface["id"],)
            ).fetchone()
            assert event == {"action": "correct", "prior_value": "Ethernet"}
    finally:
        with connect() as connection:
            connection.execute(
                """
                DELETE FROM spec_review_events WHERE assertion_id IN (
                    SELECT s.id FROM spec_assertions s JOIN products p ON p.id = s.product_id WHERE p.sku = %s
                )
                """, (sku,),
            )
            connection.execute("DELETE FROM spec_assertions WHERE product_id IN (SELECT id FROM products WHERE sku = %s)", (sku,))
            connection.execute(
                """
                DELETE FROM passage_embeddings WHERE passage_id IN (
                    SELECT s.id FROM source_passages s JOIN source_documents d ON d.id = s.document_id
                    JOIN products p ON p.id = d.product_id WHERE p.sku = %s
                )
                """, (sku,),
            )
            connection.execute(
                """
                DELETE FROM source_passages WHERE document_id IN (
                    SELECT d.id FROM source_documents d JOIN products p ON p.id = d.product_id WHERE p.sku = %s
                )
                """, (sku,),
            )
            connection.execute("DELETE FROM source_documents WHERE product_id IN (SELECT id FROM products WHERE sku = %s)", (sku,))
            connection.execute("DELETE FROM products WHERE sku = %s", (sku,))
