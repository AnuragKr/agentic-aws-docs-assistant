from unittest.mock import MagicMock

from agent.tool_decision import ToolDecisionService
from domain.models import RetrievedChunk


def _chunk(score: float, content: str = "x" * 100) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="c1",
        document_id="d1",
        content=content,
        score=score,
        title="Doc",
    )


def test_tool_decision_requests_tavily_when_no_results() -> None:
    settings = MagicMock()
    settings.enable_tavily = True
    settings.tavily_api_key = "test-key"
    settings.retrieval_score_threshold = -3.0
    service = ToolDecisionService(settings)
    assert service.should_use_tavily("Lambda cold start", []) is True


def test_tool_decision_skips_tavily_for_strong_results() -> None:
    settings = MagicMock()
    settings.enable_tavily = True
    settings.tavily_api_key = "test-key"
    settings.retrieval_score_threshold = -3.0
    service = ToolDecisionService(settings)
    chunks = [_chunk(2.5), _chunk(1.8)]
    assert service.should_use_tavily("Lambda scaling", chunks) is False
