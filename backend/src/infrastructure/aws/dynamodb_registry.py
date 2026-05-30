import boto3

from config.logging import ConfigurationError, get_logger
from config.utils import with_retry
from domain.models import DocumentRegistryEntry, RegistryStatus, SourceObject

logger = get_logger(__name__)


class DynamoDBProcessingRegistry:
    """Tracks processed documents for incremental ingestion."""

    def __init__(self, table_name: str, region: str) -> None:
        if not table_name:
            raise ConfigurationError("DYNAMODB_REGISTRY_TABLE is not configured")
        self._table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    @with_retry()
    def get(self, source_key: str) -> DocumentRegistryEntry | None:
        response = self._table.get_item(Key={"source_key": source_key})
        item = response.get("Item")
        return DocumentRegistryEntry.model_validate(item) if item else None

    @with_retry()
    def upsert(self, entry: DocumentRegistryEntry) -> None:
        self._table.put_item(Item=entry.model_dump(mode="json"))

    def is_unchanged(self, source: SourceObject) -> bool:
        existing = self.get(source.key)
        if existing is None:
            return False
        return (
            existing.etag == source.etag
            and existing.last_modified == source.last_modified.isoformat()
            and existing.status == RegistryStatus.COMPLETED
        )
