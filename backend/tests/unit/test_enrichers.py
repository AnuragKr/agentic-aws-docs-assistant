from datetime import datetime, timezone

from domain.models import ChunkRecord, DocumentMetadata, PreprocessedDocument, SectionNode
from ingestion.enrichers.chunks import ChunkEnricher, build_embedding_text
from ingestion.enrichers.document import DocumentEnricher


def test_document_summary_includes_service_and_sections() -> None:
    doc = PreprocessedDocument(
        key="lambda/guide.md",
        text="Lambda scales automatically.",
        extension=".md",
        etag="x",
        last_modified=datetime.now(timezone.utc),
        sections=[SectionNode(title="Introduction", level=1, content="Intro text")],
    )
    metadata = DocumentMetadata(
        document_id="abc",
        title="Developer Guide",
        service="Lambda",
        source_url="https://docs.aws.amazon.com/lambda/guide.md",
        source_key=doc.key,
        last_modified=doc.last_modified,
        etag=doc.etag,
    )
    summary = DocumentEnricher().summarize(doc, metadata)
    assert "Lambda" in summary
    assert "Introduction" in summary


def test_build_embedding_text_prepends_parent_context() -> None:
    metadata = DocumentMetadata(
        document_id="abc",
        title="Developer Guide",
        service="Lambda",
        source_url="https://docs.aws.amazon.com/lambda/guide.md",
        source_key="lambda/guide.md",
        last_modified=datetime.now(timezone.utc),
        etag="x",
    )
    chunk = ChunkRecord(
        chunk_id="c1",
        document_id="abc",
        content="Configure concurrency limits.",
        section="Configuration",
        subsection="Concurrency",
    )
    text = build_embedding_text(chunk, metadata)
    assert text.startswith("Lambda | Developer Guide | Configuration | Concurrency")
    assert "Configure concurrency limits." in text


def test_chunk_enricher_populates_keywords_and_topics() -> None:
    metadata = DocumentMetadata(
        document_id="abc",
        title="Guide",
        service="Lambda",
        service_category="Compute",
        source_url="https://docs.aws.amazon.com/lambda/guide.md",
        source_key="lambda/guide.md",
        last_modified=datetime.now(timezone.utc),
        etag="x",
    )
    chunks = [
        ChunkRecord(
            chunk_id="c1",
            document_id="abc",
            content="Lambda concurrency controls scaling behavior.",
            section="Configuration",
        )
    ]
    enriched = ChunkEnricher().enrich(chunks, metadata)
    assert enriched[0].keywords
    assert "Lambda" in enriched[0].topics
    assert enriched[0].chunk_summary
