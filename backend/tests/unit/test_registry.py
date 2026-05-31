from datetime import datetime, timezone

from domain.models import DocumentRegistryEntry, RegistryStatus, SourceObject
from infrastructure.storage.memory_registry import InMemoryProcessingRegistry


def test_registry_skips_unchanged_indexed_documents() -> None:
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
            status=RegistryStatus.INDEXED,
            processed_at="2026-01-01T00:00:00+00:00",
            document_hash="abc123",
        )
    )
    assert registry.is_unchanged(source) is True
    assert registry.is_unchanged(source, document_hash="abc123") is True

    source.etag = "etag-2"
    assert registry.is_unchanged(source) is False
    assert registry.is_unchanged(source, document_hash="abc123") is True


def test_registry_skips_unchanged_completed_documents() -> None:
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


def test_registry_reprocesses_when_last_modified_changes() -> None:
    registry = InMemoryProcessingRegistry()
    modified = datetime(2026, 1, 1, tzinfo=timezone.utc)
    source = SourceObject(key="lambda/guide.md", etag="etag-1", last_modified=modified)
    registry.upsert(
        DocumentRegistryEntry(
            document_id="doc1",
            source_key=source.key,
            etag="etag-1",
            last_modified=modified.isoformat(),
            status=RegistryStatus.COMPLETED,
        )
    )
    source.last_modified = datetime(2026, 1, 2, tzinfo=timezone.utc)
    assert registry.is_unchanged(source) is False


def test_registry_skips_when_document_hash_matches() -> None:
    registry = InMemoryProcessingRegistry()
    source = SourceObject(
        key="well-architected/framework.pdf",
        etag="etag-1",
        last_modified=datetime.now(timezone.utc),
    )
    registry.upsert(
        DocumentRegistryEntry(
            document_id="doc1",
            source_key=source.key,
            etag="etag-old",
            last_modified="2026-01-01T00:00:00+00:00",
            status=RegistryStatus.INDEXED,
            document_hash="hash-v2",
        )
    )
    assert registry.is_unchanged(source, document_hash="hash-v2") is True
    assert registry.is_unchanged(source, document_hash="hash-v1") is False
