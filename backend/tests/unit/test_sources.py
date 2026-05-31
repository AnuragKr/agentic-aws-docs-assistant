from generation.models import SourceReference
from generation.sources import deduplicate_sources, format_source_label


def test_deduplicate_sources_by_document_and_section() -> None:
    sources = [
        SourceReference(document_name="S3 Guide", section_title="Security", page_number=1),
        SourceReference(document_name="S3 Guide", section_title="Security", page_number=2),
        SourceReference(document_name="S3 Guide", section_title="Encryption", page_number=3),
    ]
    unique = deduplicate_sources(sources)
    assert len(unique) == 2


def test_format_source_label_omits_missing_page() -> None:
    source = SourceReference(document_name="S3 Guide", section_title="Security")
    assert format_source_label(source) == "S3 Guide | Security"


def test_format_source_label_includes_page_when_present() -> None:
    source = SourceReference(document_name="S3 Guide", section_title="Security", page_number=12)
    assert format_source_label(source) == "S3 Guide | Security | Page 12"
