from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app import create_app
from domain.models import RetrievedChunk
from generation.models import GenerationResponse, SourceReference


def test_generate_endpoint_returns_answer() -> None:
    mock_response = GenerationResponse(
        answer="Use IAM roles for least privilege.",
        sources=[
            SourceReference(
                document_name="IAM Guide",
                page_number=4,
                section_title="Roles",
            )
        ],
        model_id="meta.llama3-8b-instruct-v1:0",
        latency_ms=250.0,
    )
    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            content="IAM roles provide temporary credentials.",
            score=0.9,
            title="IAM Guide",
            section="Roles",
        )
    ]

    with patch("api.app.get_container") as mock_container:
        mock_container.return_value.generation_service.generate.return_value = mock_response
        with patch("api.app.warmup_models"):
            client = TestClient(create_app())
            response = client.post(
                "/generate",
                json={"question": "How do IAM roles work?", "chunks": [chunks[0].model_dump()]},
            )

    assert response.status_code == 200
    body = response.json()
    assert "IAM roles" in body["answer"]
    assert body["sources"][0]["document_name"] == "IAM Guide"


def test_generate_endpoint_requires_chunks() -> None:
    with patch("api.app.warmup_models"):
        client = TestClient(create_app())
        response = client.post("/generate", json={"question": "Lambda?", "chunks": []})
    assert response.status_code == 400


def test_ask_endpoint_runs_retrieval_then_generation() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            content="Lambda scales on demand.",
            score=0.9,
            service="Lambda",
            title="Lambda Guide",
        )
    ]
    generation = GenerationResponse(
        answer="Lambda scales automatically.",
        sources=[SourceReference(document_name="Lambda Guide", section_title="Intro")],
        model_id="meta.llama3-8b-instruct-v1:0",
        latency_ms=100.0,
    )

    with patch("api.app.get_container") as mock_container:
        container = mock_container.return_value
        container.retrieval_service.search.return_value = chunks
        container.generation_service.generate.return_value = generation
        with patch("api.app.warmup_models"):
            client = TestClient(create_app())
            response = client.post("/ask", json={"question": "How does Lambda scale?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Lambda scales automatically."
    assert body["retrieval_count"] == 1
    container.retrieval_service.search.assert_called_once()
    container.generation_service.generate.assert_called_once()
