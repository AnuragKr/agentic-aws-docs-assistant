from unittest.mock import patch

from fastapi.testclient import TestClient

from agent.models import AgentResponse
from generation.models import SourceReference


def test_chat_endpoint_returns_agent_response() -> None:
    mock_response = AgentResponse(
        answer="S3 provides object storage.",
        sources=[SourceReference(document_name="S3 Guide", section_title="Overview", page_number=3)],
        external_search_used=False,
    )

    with patch("api.app.get_container") as mock_container:
        mock_container.return_value.settings.agent_enabled = True
        mock_container.return_value.agent_service.run.return_value = mock_response
        with patch("api.app.warmup_models"):
            from api.app import create_app

            client = TestClient(create_app())
            response = client.post(
                "/chat",
                json={
                    "query": "What is S3?",
                    "conversation_history": [],
                },
            )

    assert response.status_code == 200
    body = response.json()
    assert "S3" in body["answer"]
    assert body["sources"][0]["document_name"] == "S3 Guide"
    assert body["external_search_used"] is False


def test_chat_endpoint_rejects_when_agent_disabled() -> None:
    with patch("api.app.get_container") as mock_container:
        mock_container.return_value.settings.agent_enabled = False
        with patch("api.app.warmup_models"):
            from api.app import create_app

            client = TestClient(create_app())
            response = client.post("/chat", json={"query": "What is Lambda?"})

    assert response.status_code == 503
