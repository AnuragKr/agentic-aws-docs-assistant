from datetime import datetime, timezone

from config.settings import Settings
from domain.models import PreprocessedDocument
from ingestion.enrichers.metadata import MetadataExtractor


def test_metadata_extraction() -> None:
    settings = Settings()
    doc = PreprocessedDocument(
        key="lambda/latest/dg/concurrency.md",
        text="# Concurrency",
        extension=".md",
        etag="x",
        last_modified=datetime.now(timezone.utc),
        sections=[],
    )
    meta = MetadataExtractor(settings).extract(doc)
    assert meta.document_id
    assert meta.service == "Lambda"
    assert meta.source_url.endswith(doc.key)
