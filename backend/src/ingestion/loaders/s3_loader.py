from collections.abc import Iterator

import boto3

from config.logging import ConfigurationError, get_logger
from config.utils import with_retry
from domain.models import RawDocument, SourceObject

logger = get_logger(__name__)

SUPPORTED = {".html", ".htm", ".md", ".markdown", ".txt", ".pdf"}


class S3DocumentLoader:
    """Load documents from the raw S3 bucket."""

    def __init__(self, bucket: str, region: str, prefix: str = "") -> None:
        if not bucket:
            raise ConfigurationError("S3_BUCKET is not configured")
        self._bucket = bucket
        self._prefix = prefix
        self._client = boto3.client("s3", region_name=region)

    @with_retry()
    def list_documents(self, prefix: str | None = None) -> Iterator[SourceObject]:
        effective = prefix if prefix is not None else self._prefix
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=effective):
            for item in page.get("Contents", []):
                key = item["Key"]
                if key.endswith("/"):
                    continue
                ext = "." + key.rsplit(".", 1)[-1].lower()
                if ext not in SUPPORTED:
                    continue
                yield SourceObject(
                    key=key,
                    etag=item["ETag"].strip('"'),
                    last_modified=item["LastModified"],
                    size=item.get("Size", 0),
                )

    @with_retry()
    def load(self, source: SourceObject) -> RawDocument:
        logger.info("document_load", key=source.key, size=source.size)
        response = self._client.get_object(Bucket=self._bucket, Key=source.key)
        body = response["Body"].read()
        ext = "." + source.key.rsplit(".", 1)[-1].lower()
        return RawDocument(
            key=source.key,
            content=body,
            extension=ext,
            etag=source.etag,
            last_modified=source.last_modified,
        )
