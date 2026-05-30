from datetime import datetime, timezone

from domain.models import DocumentRegistryEntry, RegistryStatus, SourceObject
from infrastructure.storage.memory_registry import InMemoryProcessingRegistry


def test_registry_skips_unchanged_documents() -> None:
    registry = InMemoryProcessingRegistry()
    source = SourceObject(
        key="lambda/guide.md",
        etag="etag-1",
        last_modified=datetime.now(timezone.utc),
    )
    registry.upsert(
        DocumentRegistryEntry(
            document_id="doc1",
            source_key=source.key,
            etag="etag-1",
            last_modified=source.last_modified.isoformat(),
            status=RegistryStatus.COMPLETED,
            processed_at="2026-01-01T00:00:00+00:00",
        )
    )
    assert registry.is_unchanged(source) is True

    source.etag = "etag-2"
    assert registry.is_unchanged(source) is False
