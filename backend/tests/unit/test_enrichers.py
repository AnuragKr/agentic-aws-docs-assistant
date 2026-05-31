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


def test_build_embedding_text_prepends_hierarchy_context() -> None:
    metadata = DocumentMetadata(
        document_id="abc",
        title="AWS Security Pillar",
        service="Security",
        services=["IAM", "CloudTrail"],
        source_url="https://docs.aws.amazon.com/security.pdf",
        source_key="security.pdf",
        last_modified=datetime.now(timezone.utc),
        etag="x",
    )
    chunk = ChunkRecord(
        chunk_id="c1",
        document_id="abc",
        content="Configure IAM roles.",
        hierarchy_path=["Security Pillar", "Identity and Access Management", "IAM Roles"],
        section="Identity and Access Management",
        subsection="IAM Roles",
    )
    text = build_embedding_text(chunk, metadata)
    assert "AWS Security Pillar" in text
    assert "IAM Roles" in text
    assert "Configure IAM roles." in text


def test_chunk_enricher_links_neighbors_and_summary() -> None:
    metadata = DocumentMetadata(
        document_id="abc",
        title="Security Pillar",
        service="Security",
        services=["IAM"],
        source_url="https://docs.aws.amazon.com/security.pdf",
        source_file="security.pdf",
        source_key="security.pdf",
        last_modified=datetime.now(timezone.utc),
        etag="x",
        total_pages=240,
    )
    chunks = [
        ChunkRecord(
            chunk_id="c1",
            document_id="abc",
            content="First chunk about IAM roles.",
            hierarchy_path=["Security Pillar", "IAM"],
            page_number=8,
        ),
        ChunkRecord(
            chunk_id="c2",
            document_id="abc",
            content="Second chunk about CloudTrail.",
            hierarchy_path=["Security Pillar", "Logging"],
            page_number=20,
        ),
    ]
    enriched = ChunkEnricher().enrich(chunks, metadata)
    assert enriched[0].prev_chunk_id is None
    assert enriched[0].next_chunk_id == "c2"
    assert enriched[1].prev_chunk_id == "c1"
    assert enriched[1].next_chunk_id is None
    assert enriched[0].chunk_order == 0
    assert enriched[1].chunk_order == 1
    assert enriched[0].total_pages == 240
    assert enriched[0].source_file == "security.pdf"
    assert "IAM" in enriched[0].chunk_summary
    assert enriched[0].services == ["IAM"]


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
