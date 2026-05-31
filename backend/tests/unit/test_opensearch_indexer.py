from unittest.mock import MagicMock, patch

from opensearchpy.exceptions import TransportError

from config.settings import Settings
from domain.models import ChunkRecord
from infrastructure.opensearch.indexer import OpenSearchIndexer, IndexResult


def _chunk(chunk_id: str) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=chunk_id,
        document_id="doc1",
        content=f"content for {chunk_id}",
        embedding=[0.1, 0.2, 0.3],
    )


def test_index_batches_by_configured_size() -> None:
    client = MagicMock()
    settings = Settings(
        OPENSEARCH_INDEX="aws-docs",
        OPENSEARCH_BULK_BATCH_SIZE=50,
        RETRY_MAX_ATTEMPTS=3,
    )
    indexer = OpenSearchIndexer(client, settings)
    chunks = [_chunk(f"c{i}") for i in range(120)]

    with patch("infrastructure.opensearch.indexer.bulk") as mock_bulk:
        mock_bulk.return_value = (50, [])
        result = indexer.index(chunks, "lambda/guide.pdf")

    assert mock_bulk.call_count == 3
    assert result.indexed == 150
    assert result.batches_total == 3
    assert result.batches_failed == 0


def test_index_continues_after_batch_failure() -> None:
    client = MagicMock()
    settings = Settings(
        OPENSEARCH_INDEX="aws-docs",
        OPENSEARCH_BULK_BATCH_SIZE=2,
        RETRY_MAX_ATTEMPTS=2,
        RETRY_MIN_WAIT=0,
        RETRY_MAX_WAIT=0,
    )
    indexer = OpenSearchIndexer(client, settings)
    chunks = [_chunk("a"), _chunk("b"), _chunk("c"), _chunk("d"), _chunk("e"), _chunk("f")]

    with patch("infrastructure.opensearch.indexer.bulk") as mock_bulk:
        mock_bulk.side_effect = [
            (2, []),
            TransportError(500, "server error"),
            (2, []),
        ]
        result = indexer.index(chunks, "lambda/guide.pdf")

    assert mock_bulk.call_count == 3
    assert result.indexed == 4
    assert result.failed == 2
    assert result.batches_failed == 1
    assert len(result.batch_errors) == 1


def test_index_retries_on_http_429() -> None:
    client = MagicMock()
    settings = Settings(
        OPENSEARCH_INDEX="aws-docs",
        OPENSEARCH_BULK_BATCH_SIZE=50,
        RETRY_MAX_ATTEMPTS=3,
        RETRY_MIN_WAIT=0,
        RETRY_MAX_WAIT=0,
    )
    indexer = OpenSearchIndexer(client, settings)
    chunks = [_chunk("a")]

    with patch("infrastructure.opensearch.indexer.bulk") as mock_bulk:
        mock_bulk.side_effect = [
            TransportError(429, "Too Many Requests"),
            (1, []),
        ]
        result = indexer.index(chunks, "lambda/guide.pdf")

    assert mock_bulk.call_count == 2
    assert result.indexed == 1
    assert isinstance(result, IndexResult)


def test_index_returns_empty_for_no_embeddings() -> None:
    client = MagicMock()
    settings = Settings(OPENSEARCH_INDEX="aws-docs")
    indexer = OpenSearchIndexer(client, settings)
    chunks = [
        ChunkRecord(chunk_id="x", document_id="doc1", content="no vector"),
    ]
    result = indexer.index(chunks, "lambda/guide.pdf")
    assert result.indexed == 0
    client.indices.exists.assert_not_called()
