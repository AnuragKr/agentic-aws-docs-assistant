import re

from config.logging import get_logger
from config.settings import Settings
from domain.models import RetrievedChunk

logger = get_logger(__name__)

_RECENCY_HINTS = re.compile(
    r"\b(latest|newest|recent|2024|2025|2026|just released|announcement)\b",
    re.I,
)


class ToolDecisionService:
    """Decide whether Tavily fallback search is required.

    Cross-encoder scores from BGE are logits (often negative); threshold is tuned accordingly.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._score_threshold = settings.retrieval_score_threshold

    def should_use_tavily(self, query: str, reranked_results: list[RetrievedChunk]) -> bool:
        if not self._settings.enable_tavily or not self._settings.tavily_api_key:
            return False

        if not reranked_results:
            logger.info("tool_decision_tavily", reason="no_results")
            return True

        top_score = max(chunk.score for chunk in reranked_results)
        if top_score < self._score_threshold:
            logger.info("tool_decision_tavily", reason="low_rerank_score", top_score=top_score)
            return True

        substantive = [chunk for chunk in reranked_results if len(chunk.content.strip()) >= 80]
        if len(substantive) < 2:
            logger.info("tool_decision_tavily", reason="insufficient_substantive_chunks")
            return True

        if _RECENCY_HINTS.search(query) and top_score < 0.0:
            logger.info("tool_decision_tavily", reason="recency_query_weak_retrieval")
            return True

        logger.info("tool_decision_skip_tavily", top_score=top_score, chunk_count=len(reranked_results))
        return False
