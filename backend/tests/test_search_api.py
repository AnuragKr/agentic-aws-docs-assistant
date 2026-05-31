from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app import create_app
from domain.models import RetrievedChunk


def test_search_endpoint_returns_results() -> None:
    mock_results = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            content="Lambda concurrency controls scaling.",
            score=0.95,
            service="Lambda",
            title="Developer Guide",
            section="Configuration",
            subsection="Concurrency",
            source_url="https://docs.aws.amazon.com/lambda/concurrency.html",
            citation="Developer Guide > Configuration > Concurrency (...)",
        )
    ]

    with patch("api.app.get_container") as mock_container:
        mock_container.return_value.retrieval_service.search.return_value = mock_results
        with patch("api.app.warmup_models"):
            client = TestClient(create_app())
            response = client.post(
                "/search",
                json={"query": "How does Lambda concurrency work?", "top_k": 5},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "How does Lambda concurrency work?"
    assert len(body["results"]) == 1
    assert body["results"][0]["service"] == "Lambda"
    assert body["results"][0]["score"] == 0.95


def test_search_endpoint_rejects_empty_query() -> None:
    with patch("api.app.warmup_models"):
        client = TestClient(create_app())
        response = client.post("/search", json={"query": "", "top_k": 5})
    assert response.status_code == 422


def test_search_endpoint_handles_backend_error() -> None:
    with patch("api.app.get_container") as mock_container:
        mock_container.return_value.retrieval_service.search.side_effect = RuntimeError("boom")
        with patch("api.app.warmup_models"):
            client = TestClient(create_app())
            response = client.post("/search", json={"query": "Lambda", "top_k": 3})

    assert response.status_code == 503
