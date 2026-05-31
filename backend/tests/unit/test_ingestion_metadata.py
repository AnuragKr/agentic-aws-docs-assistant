from datetime import datetime, timezone

from config.settings import Settings
from domain.models import PreprocessedDocument, SectionNode
from ingestion.enrichers.metadata import MetadataExtractor


def test_metadata_extraction() -> None:
    settings = Settings()
    doc = PreprocessedDocument(
        key="lambda/latest/dg/concurrency.md",
        text="# Concurrency\n\nUse IAM and CloudTrail.",
        extension=".md",
        etag="x",
        last_modified=datetime.now(timezone.utc),
        sections=[],
    )
    meta = MetadataExtractor(settings).extract(doc)
    assert meta.document_id
    assert meta.service == "Lambda"
    assert meta.source_file == "concurrency.md"
    assert "IAM" in meta.services
    assert meta.source_url.endswith(doc.key)


def test_metadata_uses_section_title_for_pdfs() -> None:
    settings = Settings()
    doc = PreprocessedDocument(
        key="well-architected/security-pillar.pdf",
        text="Security guidance",
        extension=".pdf",
        etag="x",
        last_modified=datetime.now(timezone.utc),
        total_pages=240,
        sections=[SectionNode(title="Security Pillar", level=1, content="Intro")],
    )
    meta = MetadataExtractor(settings).extract(doc)
    assert meta.title == "Security Pillar"
    assert meta.total_pages == 240
