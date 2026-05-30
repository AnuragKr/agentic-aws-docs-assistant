from datetime import datetime, timezone

from config.settings import Settings
from domain.models import PreprocessedDocument
from ingestion.chunkers.hierarchical import HierarchicalChunker
from ingestion.enrichers.metadata import MetadataExtractor


def test_hierarchical_chunker_respects_sections() -> None:
    settings = Settings(chunk_max_tokens=200, chunk_overlap_tokens=20)
    doc = PreprocessedDocument(
        key="lambda/concurrency.md",
        text="# Lambda\n\nBody text here.",
        extension=".md",
        etag="1",
        last_modified=datetime.now(timezone.utc),
        sections=[],
    )
    metadata = MetadataExtractor(settings).extract(doc)
    chunks = HierarchicalChunker(settings).chunk(doc, metadata)
    assert chunks
    assert chunks[0].document_id == metadata.document_id
