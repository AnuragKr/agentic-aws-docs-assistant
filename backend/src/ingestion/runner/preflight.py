"""Validate AWS configuration before a long ingestion run."""

from config.logging import ConfigurationError, get_logger
from config.settings import Settings
from infrastructure.aws.session import verify_aws_credentials
from infrastructure.opensearch.indexer import _uses_sigv4

logger = get_logger(__name__)


def validate_ingestion_preflight(settings: Settings) -> None:
    """Fail fast with actionable errors when AWS is not configured."""
    if not settings.s3_raw_bucket:
        raise ConfigurationError("S3_BUCKET is not configured in .env")

    identity = verify_aws_credentials(settings.aws_region)
    logger.info(
        "aws_credentials_ok",
        region=settings.aws_region,
        arn=identity.get("Arn"),
        account=identity.get("Account"),
    )

    if _uses_sigv4(settings.opensearch_auth_mode) and not settings.opensearch_host:
        raise ConfigurationError("OPENSEARCH_HOST is not configured in .env")
