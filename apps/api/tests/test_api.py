import psycopg
import pytest
from fastapi.testclient import TestClient

from app.main import app, create_app
from app.provider import ProviderCapabilities


client = TestClient(app)


def test_health_and_keyless_mock_provider():
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/v1/provider").json() == {"name": "mock", "external_requests": False}


def test_provider_can_be_replaced():
    class TestProvider:
        def capabilities(self) -> ProviderCapabilities:
            return ProviderCapabilities(name="test-provider", external_requests=False)

    assert TestClient(create_app(TestProvider())).get("/v1/provider").json()["name"] == "test-provider"


@pytest.mark.parametrize("query", ["a" * 121, "a\x00b"])
def test_invalid_search_returns_validation_error(query):
    assert client.get("/v1/catalog", params={"q": query}).status_code == 422


def test_database_error_is_sanitized(monkeypatch):
    def unavailable(query, provider):
        raise psycopg.OperationalError("private connection details")

    monkeypatch.setattr("app.main.search_catalog", unavailable)
    response = client.get("/v1/catalog")
    assert response.status_code == 503
    assert response.json() == {"detail": "Catalog temporarily unavailable"}
