from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.helpers import bulk
from requests_aws4auth import AWS4Auth

from config.logging import get_logger
from config.settings import Settings
from config.utils import with_retry
from domain.models import ChunkRecord
from ingestion.pipeline_log import log_gap

logger = get_logger(__name__)


def create_opensearch_client(settings: Settings) -> OpenSearch:
    hosts = [{"host": settings.opensearch_host, "port": settings.opensearch_port}]

    if settings.opensearch_auth_mode == "aws_sigv4":
        import boto3

        credentials = boto3.Session().get_credentials()
        auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            settings.aws_region,
            "es",
            session_token=credentials.token,
        )
        return OpenSearch(
            hosts=hosts,
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
        )

    return OpenSearch(
        hosts=hosts,
        http_auth=(settings.opensearch_user, settings.opensearch_password),
        use_ssl=settings.opensearch_use_ssl,
        verify_certs=settings.opensearch_use_ssl,
        connection_class=RequestsHttpConnection,
    )


class OpenSearchIndexer:
    """Index chunks with knn_vector embeddings and filterable keyword metadata."""

    def __init__(self, client: OpenSearch, settings: Settings) -> None:
        self._client = client
        self._index = settings.opensearch_index

    def ensure_index(self, dimension: int) -> None:
        if self._client.indices.exists(index=self._index):
            return

        body = {
            "settings": {"index": {"knn": True}},
            "mappings": {
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "document_id": {"type": "keyword"},
                    "embedding": {"type": "knn_vector", "dimension": dimension},
                    "content": {"type": "text"},
                    "chunk_summary": {"type": "text"},
                    "document_type": {"type": "keyword"},
                    "service": {"type": "keyword"},
                    "service_category": {"type": "keyword"},
                    "section": {"type": "keyword"},
                    "subsection": {"type": "keyword"},
                    "title": {"type": "keyword"},
                    "source_url": {"type": "keyword"},
                    "keywords": {"type": "keyword"},
                    "topics": {"type": "keyword"},
                    "heading_level": {"type": "integer"},
                    "chunk_index": {"type": "integer"},
                    "total_chunks": {"type": "integer"},
                    "content_type": {"type": "keyword"},
                }
            },
        }
        self._client.indices.create(index=self._index, body=body)
        logger.info("opensearch_index_created", index=self._index, dimension=dimension)

    @with_retry()
    def index(self, chunks: list[ChunkRecord], source_key: str) -> int:
        if not chunks:
            log_gap("store", document_key=source_key, reason="no_chunks_for_opensearch")
            return 0

        actions = []
        for chunk in chunks:
            if not chunk.embedding:
                continue
            doc = chunk.model_dump(mode="json")
            actions.append(
                {
                    "_op_type": "index",
                    "_index": self._index,
                    "_id": chunk.chunk_id,
                    "_source": doc,
                }
            )

        if not actions:
            log_gap("store", document_key=source_key, reason="no_embeddings")
            return 0

        success, errors = bulk(self._client, actions, raise_on_error=False)
        if errors:
            log_gap(
                "store",
                document_key=source_key,
                reason="opensearch_bulk_errors",
                error_count=len(errors),
            )
        logger.info("opensearch_indexed", source_key=source_key, indexed=success)
        return success
