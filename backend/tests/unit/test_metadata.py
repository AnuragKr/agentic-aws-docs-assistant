from app.core.config import Settings
from app.ingestion.domain.chunk import Chunk
from app.ingestion.pipeline.metadata import MetadataExtractor


def test_document_metadata_from_key() -> None:
    extractor = MetadataExtractor(Settings())
    meta = extractor.document_metadata("lambda/best-practices/concurrency.md")
    assert meta.service == "Lambda"
    assert meta.document_type == "best-practices"


def test_chunk_keywords() -> None:
    extractor = MetadataExtractor(Settings())
    chunks = extractor.enrich_chunks(
        [Chunk(chunk_id="1", content="Lambda concurrency reserved capacity limits")]
    )
    assert chunks[0].keywords
    assert chunks[0].ingestion_timestamp is not None
