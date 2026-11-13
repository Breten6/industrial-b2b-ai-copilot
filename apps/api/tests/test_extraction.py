import json
from pathlib import Path

import httpx2
import pytest

from app.extraction import DocumentError, Passage, Proposal, grounded_proposals, read_pdf
from app.provider import MockProvider, OpenAIProvider, ProviderError


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
GOLD = json.loads((EXAMPLES / "gold.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("filename", GOLD)
def test_fixture_extraction_matches_gold_values_and_pages(filename):
    _, passages = read_pdf((EXAMPLES / filename).read_bytes())
    grounded = grounded_proposals(passages, MockProvider().extract(passages))
    actual = {(p.key, p.value, passages[p.passage].page) for p in grounded}
    assert actual == {tuple(item) for item in GOLD[filename]}
    assert all(p.quote in passages[p.passage].text for p in grounded)


def test_grounding_rejects_invented_quotes_and_partial_numbers():
    passages = [Passage(1, 1, "Depth rating: 300.5 m")]
    proposals = [
        Proposal(passage=0, key="depth_rating", value="300", quote="Depth rating: 300.5 m"),
        Proposal(passage=0, key="depth_rating", value="300.5", quote="300.5"),
        Proposal(passage=0, key="maximum_range", value="300.5 m", quote="Depth rating: 300.5 m"),
        Proposal(passage=0, key="depth_rating", value="900 m", quote="Depth rating: 900 m"),
        Proposal(passage=-1, key="depth_rating", value="300.5 m", quote="Depth rating: 300.5 m"),
    ]
    assert grounded_proposals(passages, proposals) == []


@pytest.mark.parametrize("data", [b"not a pdf", b"%PDF-invalid"])
def test_bad_pdf_is_rejected(data):
    with pytest.raises(DocumentError):
        read_pdf(data)


def test_openai_rejects_incomplete_or_malformed_structured_output(monkeypatch):
    provider = OpenAIProvider("fixture", "fixture-model")
    outputs = iter([
        {"status": "incomplete"},
        {"status": "completed", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": '{"proposals":[{"key":"imaginary"}]}'},
        ]}]},
    ])
    monkeypatch.setattr(provider, "_post", lambda *_: next(outputs))
    for _ in range(2):
        with pytest.raises(ProviderError):
            provider.extract([Passage(1, 1, "Fixture evidence")])


def test_openai_retries_a_rate_limit_and_validates_embedding_indexes(monkeypatch):
    provider = OpenAIProvider("fixture", "fixture-model")
    calls = []
    responses = iter([
        httpx2.Response(429),
        httpx2.Response(200, json={"data": [
            {"index": 1, "embedding": [0.25] * 256},
            {"index": 0, "embedding": [0.5] * 256},
        ]}),
        httpx2.Response(200, json={"data": [{"index": 1, "embedding": [0.25] * 256}]}),
    ])

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return next(responses)

    monkeypatch.setattr("app.provider.httpx2.post", post)
    monkeypatch.setattr("app.provider.time.sleep", lambda _: None)
    assert provider.embed(["first", "second"]) == [[0.5] * 256, [0.25] * 256]
    assert calls[0] == calls[1]
    assert calls[0][0] == "https://api.openai.com/v1/embeddings"
    assert calls[0][1]["json"]["dimensions"] == 256
    with pytest.raises(ProviderError, match="indexes"):
        provider.embed(["first"])
