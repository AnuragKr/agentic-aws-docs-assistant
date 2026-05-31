from domain.models import DocumentRegistryEntry, RegistryStatus, SourceObject


class InMemoryProcessingRegistry:
    """Test double for DynamoDB registry."""

    def __init__(self) -> None:
        self._entries: dict[str, DocumentRegistryEntry] = {}

    def get(self, source_key: str) -> DocumentRegistryEntry | None:
        return self._entries.get(source_key)

    def upsert(self, entry: DocumentRegistryEntry) -> None:
        self._entries[entry.source_key] = entry

    def is_unchanged(self, source: SourceObject, document_hash: str | None = None) -> bool:
        existing = self.get(source.key)
        if existing is None:
            return False
        if existing.status not in RegistryStatus.fully_processed():
            return False
        if document_hash and existing.document_hash:
            return existing.document_hash == document_hash
        return (
            existing.etag == source.etag
            and existing.last_modified == source.last_modified.isoformat()
        )
