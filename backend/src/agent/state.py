from typing import TypedDict

from domain.chat import ChatMessage
from domain.models import RetrievedChunk
from generation.models import ExternalSearchResult


class AgentState(TypedDict, total=False):
    user_query: str
    rewritten_query: str
    intent: str
    expanded_queries: list[str]
    retrieval_results: list[RetrievedChunk]
    reranked_results: list[RetrievedChunk]
    external_results: list[ExternalSearchResult]
    generated_answer: str
    final_answer: str
    sources: list[dict]
    external_search_used: bool
    conversation_history: list[ChatMessage]
    session_id: str | None
    domain_allowed: bool
    use_tavily: bool
    tool_calls: int
    filters: dict | None
