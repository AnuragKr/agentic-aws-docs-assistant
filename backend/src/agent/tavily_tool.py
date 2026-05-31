from config.logging import get_logger
from config.settings import Settings

from generation.models import ExternalSearchResult

logger = get_logger(__name__)


class TavilySearchTool:
    """Optional external search — max one call per agent run."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._max_results = settings.tavily_max_results

    def search(self, query: str) -> list[ExternalSearchResult]:
        if not self._settings.enable_tavily or not self._settings.tavily_api_key:
            return []

        try:
            from tavily import TavilyClient
        except ImportError as exc:
            logger.warning("tavily_import_failed", error=str(exc))
            return []

        client = TavilyClient(api_key=self._settings.tavily_api_key)
        try:
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=self._max_results,
                include_domains=["aws.amazon.com", "docs.aws.amazon.com"],
            )
        except Exception as exc:
            logger.warning("tavily_search_failed", error=str(exc))
            return []

        results: list[ExternalSearchResult] = []
        for item in response.get("results", []):
            content = (item.get("content") or "").strip()
            if not content:
                continue
            results.append(
                ExternalSearchResult(
                    title=item.get("title") or "AWS documentation",
                    url=item.get("url") or "",
                    content=content,
                )
            )

        logger.info("tavily_search_complete", result_count=len(results))
        return results
