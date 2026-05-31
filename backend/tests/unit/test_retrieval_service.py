from unittest.mock import MagicMock

import pytest

from config.settings import Settings
from retrieval.service import RetrievalService


@pytest.fixture
def settings() -> Settings:
    return Settings(
        SEARCH_VECTOR_K=25,
        SEARCH_RERANK_CANDIDATES=10,
        EMBEDDING_DIMENSION=384,
    )


def test_retrieval_service_search_flow(settings: Settings) -> None:
    embeddings = MagicMock()
    embeddings.dimension = 384
    embeddings.embed_query.return_value = [0.1] * 384

    store = MagicMock()
    store.ensure_index.return_value = None
    store.vector_search.return_value = [
        {
            "_score": 0.92,
            "_source": {
                "chunk_id": "c1",
                "document_id": "d1",
                "content": "Lambda concurrency limits scaling.",
                "service": "Lambda",
                "title": "Developer Guide",
                "section": "Configuration",
                "subsection": "Concurrency",
                "source_url": "https://docs.aws.amazon.com/lambda/concurrency.html",
                "chunk_summary": "Concurrency overview",
                "keywords": ["concurrency"],
                "topics": ["Lambda"],
            },
        },
        {
            "_score": 0.81,
            "_source": {
                "chunk_id": "c2",
                "document_id": "d1",
                "content": "Reserved concurrency details.",
                "service": "Lambda",
                "title": "Developer Guide",
                "source_url": "https://docs.aws.amazon.com/lambda/concurrency.html",
            },
        },
    ]

    reranker = MagicMock()
    reranker.rerank.side_effect = lambda query, candidates: [
        c.model_copy(update={"score": 0.99 - index * 0.1})
        for index, c in enumerate(candidates)
    ]

    service = RetrievalService(embeddings, store, reranker, settings)
    results = service.search("How does Lambda concurrency work?", top_k=1)

    embeddings.embed_query.assert_called_once()
    store.vector_search.assert_called_once()
    reranker.rerank.assert_called_once()
    assert len(results) == 1
    assert results[0].chunk_id == "c1"
    assert results[0].citation
    assert "Developer Guide" in results[0].citation


def test_retrieval_service_empty_query(settings: Settings) -> None:
    service = RetrievalService(MagicMock(), MagicMock(), MagicMock(), settings)
    assert service.search("   ", top_k=5) == []
