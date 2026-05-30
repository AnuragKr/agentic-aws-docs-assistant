from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk
from app.core.config import Settings
from app.observability.logging import get_logger
from app.observability.retry import aws_retry
from app.ingestion.ports.indexer import IVectorIndexer
from app.ingestion.domain.chunk import Chunk

logger = get_logger(__name__)


class OpenSearchIndexer(IVectorIndexer):
    def __init__(self, client: OpenSearch, settings: Settings) -> None:
        self._client = client
        self._settings = settings
        self._index = settings.opensearch_index

    def ensure_index(self, dimension: int) -> None:
        if self._client.indices.exists(index=self._index):
            return

        body = {
            "settings": {"index": {"knn": True}},
            "mappings": {
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "embedding": {"type": "knn_vector", "dimension": dimension},
                    "content": {"type": "text"},
                    "chunk_summary": {"type": "text"},
                    "service": {"type": "keyword"},
                    "section": {"type": "keyword"},
                    "subsection": {"type": "keyword"},
                    "section_hierarchy": {"type": "keyword"},
                    "document_name": {"type": "keyword"},
                    "source_url": {"type": "keyword"},
                    "document_type": {"type": "keyword"},
                    "keywords": {"type": "keyword"},
                    "topics": {"type": "keyword"},
                    "content_type": {"type": "keyword"},
                    "parent_chunk_id": {"type": "keyword"},
                    "chunk_level": {"type": "keyword"},
                    "chunk_index": {"type": "integer"},
                    "ingestion_timestamp": {"type": "date"},
                }
            },
        }
        self._client.indices.create(index=self._index, body=body)
        logger.info("opensearch_index_created", index=self._index, dimension=dimension)

    @aws_retry
    def bulk_upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
        if not chunks:
            return 0

        actions = []
        for chunk, vector in zip(chunks, embeddings, strict=True):
            doc = chunk.model_dump(mode="json")
            doc["embedding"] = vector
            actions.append(
                {
                    "_op_type": "index",
                    "_index": self._index,
                    "_id": chunk.chunk_id,
                    "_source": doc,
                }
            )

        success, errors = bulk(self._client, actions, raise_on_error=False)
        if errors:
            logger.warning("opensearch_bulk_partial_errors", count=len(errors))
        return success
