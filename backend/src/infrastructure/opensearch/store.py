import time
from typing import Any

from opensearchpy import OpenSearch
from opensearchpy.exceptions import OpenSearchException
from tenacity import retry, stop_after_attempt, wait_exponential

from config.logging import get_logger
from config.settings import Settings
from config.utils import with_retry
from infrastructure.opensearch.mappings import index_mappings
from retrieval.filters import SearchFilters

logger = get_logger(__name__)

_SOURCE_FIELDS = [
    "chunk_id",
    "document_id",
    "content",
    "service",
    "service_category",
    "title",
    "section",
    "subsection",
    "source_url",
    "keywords",
    "topics",
    "chunk_summary",
]


class OpenSearchStore:
    """Lightweight OpenSearch wrapper for vector search and health checks."""

    def __init__(self, client: OpenSearch, settings: Settings) -> None:
        self._client = client
        self._index = settings.opensearch_index
        self._settings = settings

    @property
    def index_name(self) -> str:
        return self._index

    @with_retry()
    def ensure_index(self, dimension: int) -> None:
        if self._client.indices.exists(index=self._index):
            return
        self._client.indices.create(index=self._index, body=index_mappings(dimension))
        logger.info("opensearch_index_created", index=self._index, dimension=dimension)

    def ping(self, timeout: int | None = None) -> dict[str, Any]:
        """Fast connectivity check — avoids slow cluster.health() over long distances."""
        timeout = timeout or self._settings.health_opensearch_timeout
        started = time.perf_counter()
        try:
            ok = self._client.ping(request_timeout=timeout)
            index_exists = (
                self._client.indices.exists(index=self._index, request_timeout=timeout)
                if ok
                else False
            )
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            return {
                "status": "ok" if ok else "error",
                "reachable": ok,
                "index": self._index,
                "index_exists": index_exists,
                "duration_ms": duration_ms,
            }
        except OpenSearchException as exc:
            logger.warning("opensearch_ping_failed", error=str(exc))
            return {
                "status": "error",
                "reachable": False,
                "error": str(exc),
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            }

    def health(self) -> dict[str, Any]:
        """Deep health — cluster status (can be slow remotely; use ping() for liveness)."""
        try:
            timeout = self._settings.health_opensearch_timeout
            cluster = self._client.cluster.health(request_timeout=timeout)
            index_exists = self._client.indices.exists(index=self._index, request_timeout=timeout)
            return {
                "status": "ok" if cluster.get("status") in {"green", "yellow"} else "degraded",
                "cluster_status": cluster.get("status"),
                "index": self._index,
                "index_exists": index_exists,
            }
        except OpenSearchException as exc:
            logger.warning("opensearch_health_failed", error=str(exc))
            return {"status": "error", "error": str(exc)}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def vector_search(
        self,
        query_vector: list[float],
        *,
        k: int,
        filters: SearchFilters | None = None,
    ) -> list[dict[str, Any]]:
        filter_clauses = filters.to_opensearch_clauses() if filters else []
        knn_query: dict[str, Any] = {
            "knn": {
                "embedding": {
                    "vector": query_vector,
                    "k": k,
                }
            }
        }

        if filter_clauses:
            body = {
                "size": k,
                "_source": _SOURCE_FIELDS,
                "query": {
                    "bool": {
                        "must": [knn_query],
                        "filter": filter_clauses,
                    }
                },
            }
        else:
            body = {
                "size": k,
                "_source": _SOURCE_FIELDS,
                "query": knn_query,
            }

        response = self._client.search(
            index=self._index,
            body=body,
            request_timeout=self._settings.opensearch_timeout,
        )
        hits = response.get("hits", {}).get("hits", [])
        logger.info(
            "opensearch_vector_search",
            k=k,
            hits=len(hits),
            filters=bool(filter_clauses),
        )
        return hits
