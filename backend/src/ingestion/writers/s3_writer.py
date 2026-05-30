import boto3

from config.logging import ConfigurationError, get_logger, to_json, utc_now_iso
from config.utils import with_retry
from domain.models import ChunkRecord, DocumentMetadata, PreprocessedDocument

logger = get_logger(__name__)


class S3ProcessedDocumentWriter:
    """Write processed metadata, documents, and chunks to S3."""

    def __init__(self, bucket: str, region: str, prefix: str = "processed/") -> None:
        if not bucket:
            raise ConfigurationError("S3_PROCESSED_BUCKET is not configured")
        self._client = boto3.client("s3", region_name=region)
        self._bucket = bucket
        self._prefix = prefix.rstrip("/") + "/"

    @with_retry()
    def _put_json(self, key: str, payload: object) -> None:
        body = to_json(payload)
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("s3_artifact_written", key=key)

    def write(
        self,
        document: PreprocessedDocument,
        metadata: DocumentMetadata,
        chunks: list[ChunkRecord],
    ) -> int:
        doc_id = metadata.document_id
        self._put_json(f"{self._prefix}metadata/{doc_id}.json", metadata)
        self._put_json(
            f"{self._prefix}documents/{doc_id}.json",
            {
                "document_id": doc_id,
                "source_key": document.key,
                "title": metadata.title,
                "text": document.text,
                "sections": [s.model_dump() for s in document.sections],
                "processed_at": utc_now_iso(),
            },
        )
        if chunks:
            self._put_json(
                f"{self._prefix}chunks/{doc_id}.json",
                [c.model_dump(mode="json") for c in chunks],
            )
        return len(chunks)
