import time
from dataclasses import dataclass, field

import boto3
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import TransportError
from opensearchpy.helpers import bulk
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from config.logging import ConfigurationError, get_logger
from config.settings import Settings
from domain.models import ChunkRecord
from infrastructure.aws.session import get_boto_session
from infrastructure.opensearch.mappings import index_mappings
from ingestion.pipeline_log import log_gap

logger = get_logger(__name__)


@dataclass
class IndexResult:
    indexed: int = 0
    failed: int = 0
    batches_total: int = 0
    batches_failed: int = 0
    batch_errors: list[str] = field(default_factory=list)


def _normalize_host(host: str) -> str:
    value = host.strip()
    for prefix in ("https://", "http://"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
    return value.rstrip("/")


def _uses_sigv4(auth_mode: str) -> bool:
    normalized = auth_mode.lower().replace("-", "_")
    return normalized in {"aws_sigv4", "sigv4", "aws"}


def _is_rate_limited(exc: BaseException) -> bool:
    return isinstance(exc, TransportError) and exc.status_code == 429


def create_opensearch_client(settings: Settings) -> OpenSearch:
    host = _normalize_host(settings.opensearch_host)
    if not host:
        raise ConfigurationError("OPENSEARCH_HOST is not configured")

    hosts = [{"host": host, "port": settings.opensearch_port}]
    timeout = settings.opensearch_timeout

    if _uses_sigv4(settings.opensearch_auth_mode):
        credentials = get_boto_session(settings.aws_region).get_credentials()
        if credentials is None:
            raise ConfigurationError(
                "AWS credentials not found — OpenSearch requires SigV4 signing on EC2/instance role"
            )

        auth = AWSV4SignerAuth(credentials, settings.aws_region, "es")
        logger.info(
            "opensearch_client",
            host=host,
            port=settings.opensearch_port,
            auth="aws_sigv4",
            region=settings.aws_region,
        )
        return OpenSearch(
            hosts=hosts,
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=timeout,
        )

    logger.info(
        "opensearch_client",
        host=host,
        port=settings.opensearch_port,
        auth="basic",
    )
    return OpenSearch(
        hosts=hosts,
        http_auth=(settings.opensearch_user, settings.opensearch_password),
        use_ssl=settings.opensearch_use_ssl,
        verify_certs=settings.opensearch_use_ssl,
        connection_class=RequestsHttpConnection,
        timeout=timeout,
    )


class OpenSearchIndexer:
    """Index chunks with knn_vector embeddings and filterable keyword metadata."""

    def __init__(self, client: OpenSearch, settings: Settings) -> None:
        self._client = client
        self._index = settings.opensearch_index
        self._batch_size = settings.opensearch_bulk_batch_size
        self._settings = settings

    def ensure_index(self, dimension: int) -> None:
        if self._client.indices.exists(index=self._index):
            return

        self._client.indices.create(index=self._index, body=index_mappings(dimension))
        logger.info("opensearch_index_created", index=self._index, dimension=dimension)

    def index(self, chunks: list[ChunkRecord], source_key: str) -> IndexResult:
        if not chunks:
            log_gap("store", document_key=source_key, reason="no_chunks_for_opensearch")
            return IndexResult()

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
            return IndexResult()

        batches = [
            actions[i : i + self._batch_size]
            for i in range(0, len(actions), self._batch_size)
        ]
        result = IndexResult(batches_total=len(batches))
        indexing_started = time.perf_counter()

        for batch_number, batch in enumerate(batches, start=1):
            batch_started = time.perf_counter()
            try:
                indexed, failed, error = self._index_batch_with_retry(batch)
                result.indexed += indexed
                result.failed += failed
                if error:
                    result.batches_failed += 1
                    result.batch_errors.append(
                        f"batch {batch_number}/{len(batches)}: {error}"
                    )
            except Exception as exc:
                result.batches_failed += 1
                result.failed += len(batch)
                result.batch_errors.append(
                    f"batch {batch_number}/{len(batches)}: {exc}"
                )
                logger.exception(
                    "opensearch_batch_failed",
                    source_key=source_key,
                    batch_number=batch_number,
                    batch_size=len(batch),
                )
                continue

            logger.info(
                "opensearch_batch_indexed",
                source_key=source_key,
                batch_number=batch_number,
                batches_total=len(batches),
                chunks_indexed=indexed,
                chunks_failed=failed,
                indexing_duration_ms=round((time.perf_counter() - batch_started) * 1000, 2),
            )

        logger.info(
            "opensearch_indexed",
            source_key=source_key,
            chunks_indexed=result.indexed,
            chunks_failed=result.failed,
            batches_total=result.batches_total,
            batches_failed=result.batches_failed,
            indexing_duration_ms=round((time.perf_counter() - indexing_started) * 1000, 2),
        )
        return result

    def _index_batch_with_retry(
        self,
        batch: list[dict],
    ) -> tuple[int, int, str | None]:
        cfg = self._settings

        @retry(
            retry=retry_if_exception(_is_rate_limited),
            stop=stop_after_attempt(cfg.retry_max_attempts),
            wait=wait_exponential(
                multiplier=1,
                min=cfg.retry_min_wait,
                max=cfg.retry_max_wait,
            ),
            reraise=True,
        )
        def _send() -> tuple[int, int, str | None]:
            try:
                success, errors = bulk(self._client, batch, raise_on_error=False)
            except TransportError as exc:
                if exc.status_code == 429:
                    logger.warning("opensearch_rate_limited", status=429)
                    raise
                return 0, len(batch), str(exc)

            if not errors:
                return success, 0, None

            rate_limited = any(
                err.get("index", {}).get("status") == 429
                or err.get("create", {}).get("status") == 429
                for err in errors
            )
            if rate_limited:
                raise TransportError(429, "bulk batch rate limited")

            return success, len(errors), f"{len(errors)} bulk item errors"

        return _send()
