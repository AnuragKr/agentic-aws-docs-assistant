from retrieval.filters import SearchFilters


def test_search_filters_to_opensearch_clauses() -> None:
    filters = SearchFilters(
        service="Lambda",
        service_category="Compute",
        section="Configuration",
        subsection="Concurrency",
        topics=["scaling"],
        keywords=["provisioned"],
    )
    clauses = filters.to_opensearch_clauses()
    assert {"term": {"service": "Lambda"}} in clauses
    assert {"term": {"topics": "scaling"}} in clauses
    assert len(clauses) == 6


def test_search_filters_empty() -> None:
    assert SearchFilters().is_empty() is True
    assert SearchFilters(service="S3").is_empty() is False
