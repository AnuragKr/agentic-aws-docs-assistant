from collections.abc import Iterator

import boto3
from botocore.exceptions import ClientError

from app.core.config import Settings
from app.observability.logging import get_logger
from app.observability.retry import aws_retry

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".html", ".htm"}


class S3Repository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = boto3.client("s3", region_name=settings.aws_region)

    @aws_retry
    def list_keys(self, prefix: str) -> Iterator[str]:
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._settings.s3_bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                key = item["Key"]
                if key.endswith("/"):
                    continue
                ext = "." + key.rsplit(".", 1)[-1].lower() if "." in key else ""
                if ext not in SUPPORTED_EXTENSIONS:
                    logger.debug("s3_skip_unsupported", key=key, extension=ext)
                    continue
                if item.get("Size", 0) == 0:
                    continue
                yield key

    @aws_retry
    def get_object_text(self, key: str) -> str:
        try:
            response = self._client.get_object(
                Bucket=self._settings.s3_bucket,
                Key=key,
            )
            body = response["Body"].read()
            return body.decode("utf-8", errors="replace")
        except ClientError:
            logger.exception("s3_get_object_failed", key=key)
            raise
