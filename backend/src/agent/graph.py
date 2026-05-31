import time
from typing import Literal

from langgraph.graph import END, StateGraph

from domain.intent import QueryIntent
from config.logging import get_logger
from domain.models import RetrievedChunk
from generation.models import GenerationRequest, INSUFFICIENT_EVIDENCE_MESSAGE
from retrieval.citations import attach_citations
from retrieval.filters import SearchFilters

from agent.dependencies import AgentDependencies
from generation.models import DOMAIN_REJECTION_MESSAGE
from agent.state import AgentState

logger = get_logger(__name__)


def build_agent_graph(deps: AgentDependencies):
    """Deterministic LangGraph — nodes delegate to services only."""

    def domain_guard_node(state: AgentState) -> AgentState:
        allowed, rejection = deps.domain_guard.evaluate(
            state["user_query"],
            state.get("conversation_history") or [],
        )
        if allowed:
            return {"domain_allowed": True}
        return {
            "domain_allowed": False,
            "final_answer": rejection or DOMAIN_REJECTION_MESSAGE,
            "sources": [],
            "external_search_used": False,
        }

    def classify_intent_node(state: AgentState) -> AgentState:
        history = state.get("conversation_history") or []
        intent = deps.intent_classifier.classify(state["user_query"], history)
        logger.info("intent_classified", intent=intent.value)
        return {"intent": intent.value}

    def rewrite_node(state: AgentState) -> AgentState:
        intent = QueryIntent(state.get("intent") or QueryIntent.EXPLAIN.value)
        rewritten = deps.query_rewriter.rewrite(
            state["user_query"],
            state.get("conversation_history") or [],
            intent=intent,
        )
        return {"rewritten_query": rewritten}

    def summarize_node(state: AgentState) -> AgentState:
        history = state.get("conversation_history") or []
        answer = deps.conversation_summarizer.summarize(history)
        return {
            "generated_answer": answer,
            "final_answer": answer,
            "sources": [],
            "external_search_used": False,
        }

    def expand_node(state: AgentState) -> AgentState:
        query = state.get("rewritten_query") or state["user_query"]
        expanded = deps.query_expansion.expand(query)
        return {"expanded_queries": expanded}

    def retrieve_node(state: AgentState) -> AgentState:
        queries = state.get("expanded_queries") or [state.get("rewritten_query") or state["user_query"]]
        filters = _parse_filters(state.get("filters"))
        merged: dict[str, RetrievedChunk] = {}

        for query in queries:
            for chunk in deps.retrieval_service.retrieve_vector_candidates(query, filters=filters):
                existing = merged.get(chunk.chunk_id)
                if existing is None or chunk.score > existing.score:
                    merged[chunk.chunk_id] = chunk

        ranked = sorted(merged.values(), key=lambda item: item.score, reverse=True)
        top = ranked[: deps.settings.search_vector_k]
        logger.info("agent_retrieval_complete", retrieval_count=len(top))
        return {"retrieval_results": top}

    def rerank_node(state: AgentState) -> AgentState:
        candidates = state.get("retrieval_results") or []
        query = state.get("rewritten_query") or state["user_query"]
        if not candidates:
            return {"reranked_results": []}

        pool = candidates[: deps.settings.search_rerank_candidates]
        if deps.settings.reranker_enabled and deps.reranker is not None:
            reranked = deps.reranker.rerank(query, pool)
        else:
            reranked = pool

        top_k = deps.settings.generation_rerank_top_k
        results = attach_citations(reranked[:top_k])
        logger.info("agent_rerank_complete", reranked_count=len(results))
        return {"reranked_results": results}

    def tool_decision_node(state: AgentState) -> AgentState:
        query = state.get("rewritten_query") or state["user_query"]
        reranked = state.get("reranked_results") or []
        use_tavily = deps.tool_decision.should_use_tavily(query, reranked)
        return {"use_tavily": use_tavily, "tool_calls": 0, "external_search_used": False}

    def tavily_node(state: AgentState) -> AgentState:
        if state.get("tool_calls", 0) >= deps.settings.max_tool_calls:
            return {}
        query = state.get("rewritten_query") or state["user_query"]
        results = deps.tavily_tool.search(query)
        return {
            "external_results": results,
            "external_search_used": bool(results),
            "tool_calls": state.get("tool_calls", 0) + 1,
        }

    def generate_node(state: AgentState) -> AgentState:
        chunks = state.get("reranked_results") or []
        external = state.get("external_results") or []
        question = state.get("rewritten_query") or state["user_query"]
        intent = QueryIntent(state.get("intent") or QueryIntent.EXPLAIN.value)

        if not chunks and not external:
            # Insufficient evidence is decided here — never delegated to the LLM.
            return {
                "generated_answer": INSUFFICIENT_EVIDENCE_MESSAGE,
                "final_answer": INSUFFICIENT_EVIDENCE_MESSAGE,
                "sources": [],
            }

        started = time.perf_counter()
        response = deps.generation_service.generate(
            GenerationRequest(
                question=question,
                retrieved_chunks=chunks,
                external_results=external,
                intent=intent,
            )
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "agent_generation_complete",
            intent=intent.value,
            generation_latency_ms=latency_ms,
            source_count=len(response.sources),
            external_search_used=state.get("external_search_used", False),
        )
        return {
            "generated_answer": response.answer,
            "final_answer": response.answer,
            "sources": [source.model_dump() for source in response.sources],
        }

    def route_after_guard(state: AgentState) -> Literal["classify", "end"]:
        return "end" if not state.get("domain_allowed", True) else "classify"

    def route_after_rewrite(state: AgentState) -> Literal["summarize", "expand"]:
        # Memory-only path: no OpenSearch, reranker, or Tavily.
        intent = state.get("intent")
        if intent == QueryIntent.SUMMARIZE_CONVERSATION.value:
            return "summarize"
        return "expand"

    def route_after_tool(state: AgentState) -> Literal["tavily", "generate"]:
        return "tavily" if state.get("use_tavily") else "generate"

    graph = StateGraph(AgentState)
    graph.add_node("domain_guard", domain_guard_node)
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("rewrite", rewrite_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("expand", expand_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("rerank", rerank_node)
    graph.add_node("tool_decision", tool_decision_node)
    graph.add_node("tavily", tavily_node)
    graph.add_node("generate", generate_node)

    graph.set_entry_point("domain_guard")
    graph.add_conditional_edges("domain_guard", route_after_guard, {"end": END, "classify": "classify_intent"})
    graph.add_edge("classify_intent", "rewrite")
    graph.add_conditional_edges("rewrite", route_after_rewrite, {"summarize": "summarize", "expand": "expand"})
    graph.add_edge("summarize", END)
    graph.add_edge("expand", "retrieve")
    graph.add_edge("retrieve", "rerank")
    graph.add_edge("rerank", "tool_decision")
    graph.add_conditional_edges("tool_decision", route_after_tool, {"tavily": "tavily", "generate": "generate"})
    graph.add_edge("tavily", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


def _parse_filters(raw: dict | None) -> SearchFilters | None:
    if not raw:
        return None
    filters = SearchFilters.model_validate(raw)
    return None if filters.is_empty() else filters
