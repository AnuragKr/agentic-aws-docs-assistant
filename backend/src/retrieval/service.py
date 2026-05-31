"""
Retrieval orchestration — read this file to understand the full search flow.

    User Query → Query Embedding → OpenSearch kNN (Top 20–30)
        → Cross-Encoder Rerank (Top 10) → Top K Results with Citations
"""

import time

from config.logging import get_logger
from config.settings import Settings
from domain.models import RetrievedChunk
from infrastructure.opensearch.store import OpenSearchStore
from ingestion.embeddings.provider import EmbeddingProvider
from retrieval.citations import attach_citations
from retrieval.filters import SearchFilters
from retrieval.reranker import CrossEncoderReranker

logger = get_logger(__name__)


class RetrievalService:
    """Single orchestration class for semantic search over ingested AWS docs."""

    def __init__(
        self,
        embeddings: EmbeddingProvider,
        store: OpenSearchStore,
        reranker: CrossEncoderReranker | None,
        settings: Settings,
    ) -> None:
        self._embeddings = embeddings
        self._store = store
        self._reranker = reranker
        self._vector_k = settings.search_vector_k
        self._rerank_candidates = settings.search_rerank_candidates
        self._reranker_enabled = settings.reranker_enabled

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: SearchFilters | None = None,
    ) -> list[RetrievedChunk]:
        started = time.perf_counter()
        query = query.strip()
        if not query:
            return []

        self._store.ensure_index(self._embeddings.dimension)

        logger.info("search_embed_query_start", query_len=len(query))
        query_vector = self._embeddings.embed_query(query)

        logger.info("search_vector_start", k=self._vector_k)
        hits = self._store.vector_search(
            query_vector,
            k=self._vector_k,
            filters=filters,
        )
        candidates = [_hit_to_chunk(hit) for hit in hits]

        if self._reranker_enabled and self._reranker is not None and candidates:
            pool = candidates[: self._rerank_candidates]
            logger.info("search_rerank_start", pool_size=len(pool))
            reranked = self._reranker.rerank(query, pool)
        else:
            reranked = candidates

        results = attach_citations(reranked[:top_k])

        logger.info(
            "retrieval_complete",
            query_len=len(query),
            vector_hits=len(candidates),
            rerank_enabled=self._reranker_enabled,
            returned=len(results),
            top_k=top_k,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return results

    def retrieve_vector_candidates(
        self,
        query: str,
        *,
        filters: SearchFilters | None = None,
    ) -> list[RetrievedChunk]:
        """Vector search only — used by agent retriever node before cross-encoder rerank."""
        query = query.strip()
        if not query:
            return []

        self._store.ensure_index(self._embeddings.dimension)
        query_vector = self._embeddings.embed_query(query)
        hits = self._store.vector_search(
            query_vector,
            k=self._vector_k,
            filters=filters,
        )
        return [_hit_to_chunk(hit) for hit in hits]


def _hit_to_chunk(hit: dict) -> RetrievedChunk:
    source = hit.get("_source", {})
    return RetrievedChunk(
        chunk_id=source.get("chunk_id", hit.get("_id", "")),
        document_id=source.get("document_id", ""),
        content=source.get("content", ""),
        score=float(hit.get("_score") or 0.0),
        service=source.get("service"),
        service_category=source.get("service_category"),
        title=source.get("title", ""),
        document_title=source.get("document_title") or source.get("title", ""),
        source_file=source.get("source_file", ""),
        section=source.get("section"),
        subsection=source.get("subsection"),
        page_number=source.get("page_number"),
        source_url=source.get("source_url", ""),
        chunk_summary=source.get("chunk_summary", ""),
        keywords=source.get("keywords") or [],
        topics=source.get("topics") or [],
    )
