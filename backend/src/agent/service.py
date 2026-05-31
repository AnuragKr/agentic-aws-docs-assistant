import time

from config.logging import get_logger
from config.settings import Settings
from generation.models import SourceReference
from generation.service import GenerationService
from generation.sources import deduplicate_sources
from retrieval.reranker import get_reranker
from retrieval.service import RetrievalService

from agent.conversation_summarizer import ConversationSummarizer
from agent.dependencies import AgentDependencies
from agent.domain_guard import AWSDomainGuardService
from agent.graph import build_agent_graph
from agent.intent import IntentClassifier
from agent.models import AgentResponse
from domain.chat import ChatMessage
from agent.query_expansion import QueryExpansionService
from agent.query_rewriter import ConversationAwareQueryRewriter
from agent.tavily_tool import TavilySearchTool
from agent.tool_decision import ToolDecisionService
from infrastructure.aws.chat_memory import DynamoDBChatMemoryStore

logger = get_logger(__name__)


class AgentService:
    """Runs the LangGraph agent pipeline."""

    def __init__(self, deps: AgentDependencies) -> None:
        self._deps = deps
        self._graph = build_agent_graph(deps)

    @classmethod
    def from_container(
        cls,
        settings: Settings,
        retrieval_service: RetrievalService,
        generation_service: GenerationService,
        generation_provider,
        chat_memory: DynamoDBChatMemoryStore | None = None,
    ) -> "AgentService":
        deps = AgentDependencies(
            settings=settings,
            domain_guard=AWSDomainGuardService(),
            intent_classifier=IntentClassifier(),
            query_rewriter=ConversationAwareQueryRewriter(generation_provider, settings),
            query_expansion=QueryExpansionService(settings),
            conversation_summarizer=ConversationSummarizer(generation_provider),
            retrieval_service=retrieval_service,
            reranker=get_reranker(settings),
            tool_decision=ToolDecisionService(settings),
            tavily_tool=TavilySearchTool(settings),
            generation_service=generation_service,
            chat_memory=chat_memory,
        )
        return cls(deps)

    def run(
        self,
        query: str,
        *,
        conversation_history: list[ChatMessage] | None = None,
        session_id: str | None = None,
        filters: dict | None = None,
    ) -> AgentResponse:
        started = time.perf_counter()
        history = self._resolve_history(session_id, conversation_history or [])
        user_query = query.strip()

        logger.info(
            "agent_run_start",
            original_query=user_query[:200],
            history_turns=len(history),
            session_id=session_id,
        )

        final_state = self._graph.invoke(
            {
                "user_query": user_query,
                "conversation_history": history,
                "session_id": session_id,
                "filters": filters,
                "external_search_used": False,
                "tool_calls": 0,
                "sources": [],
            }
        )

        answer = final_state.get("final_answer") or final_state.get("generated_answer") or ""
        sources = deduplicate_sources(
            [
                SourceReference.model_validate(item)
                for item in (final_state.get("sources") or [])
            ]
        )

        if session_id and self._deps.chat_memory is not None and answer:
            try:
                self._deps.chat_memory.append_turn(session_id, user_query, answer)
            except Exception:
                logger.warning("chat_memory_persist_failed", session_id=session_id)

        logger.info(
            "agent_run_complete",
            original_query=user_query[:200],
            intent=final_state.get("intent"),
            rewritten_query=(final_state.get("rewritten_query") or "")[:200],
            expanded_queries=final_state.get("expanded_queries") or [],
            retrieval_count=len(final_state.get("retrieval_results") or []),
            reranked_count=len(final_state.get("reranked_results") or []),
            external_search_used=bool(final_state.get("external_search_used")),
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )

        return AgentResponse(
            answer=answer,
            sources=sources,
            external_search_used=bool(final_state.get("external_search_used")),
        )

    def _resolve_history(
        self,
        session_id: str | None,
        request_history: list[ChatMessage],
    ) -> list[ChatMessage]:
        # Prefer DynamoDB when it has more context than the client-sent history.
        if session_id and self._deps.chat_memory is not None:
            try:
                stored = self._deps.chat_memory.get_history(session_id)
                if len(stored) >= len(request_history):
                    return stored
            except Exception:
                logger.warning("chat_memory_load_failed", session_id=session_id)
        return request_history
