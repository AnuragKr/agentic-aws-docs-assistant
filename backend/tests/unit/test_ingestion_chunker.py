from datetime import datetime, timezone

from config.settings import Settings
from domain.models import PreprocessedDocument, SectionNode
from ingestion.chunkers.hierarchical import HierarchicalChunker
from ingestion.enrichers.metadata import MetadataExtractor


def test_hierarchical_chunker_only_chunks_leaf_sections() -> None:
    settings = Settings(
        CHUNK_MIN_TOKENS=1,
        CHUNK_MAX_TOKENS=200,
        CHUNK_OVERLAP_TOKENS=20,
    )
    doc = PreprocessedDocument(
        key="lambda/concurrency.md",
        text="# Lambda\n\nRoot body.",
        extension=".md",
        etag="1",
        last_modified=datetime.now(timezone.utc),
        sections=[
            SectionNode(
                title="Lambda",
                level=1,
                content="",
                children=[
                    SectionNode(title="Intro", level=2, content="Intro paragraph."),
                    SectionNode(title="Limits", level=2, content="Limits paragraph."),
                ],
            )
        ],
    )
    metadata = MetadataExtractor(settings).extract(doc)
    chunks = HierarchicalChunker(settings).chunk(doc, metadata)
    assert len(chunks) == 2
    assert {chunk.section for chunk in chunks} == {"Intro", "Limits"}


def test_hierarchical_chunker_merges_small_chunks() -> None:
    settings = Settings(
        CHUNK_MIN_TOKENS=50,
        CHUNK_MAX_TOKENS=200,
        CHUNK_OVERLAP_TOKENS=10,
    )
    doc = PreprocessedDocument(
        key="lambda/short.md",
        text="Short sections.",
        extension=".md",
        etag="1",
        last_modified=datetime.now(timezone.utc),
        sections=[
            SectionNode(title="Chapter", level=1, content="Tiny section A.\n\nTiny section B."),
        ],
    )
    metadata = MetadataExtractor(settings).extract(doc)
    chunks = HierarchicalChunker(settings).chunk(doc, metadata)
    assert len(chunks) == 1


def test_hierarchical_chunker_caps_at_max_chunks() -> None:
    settings = Settings(
        CHUNK_MIN_TOKENS=1,
        CHUNK_MAX_TOKENS=10,
        CHUNK_OVERLAP_TOKENS=0,
        CHUNK_MAX_CHUNKS_PER_DOCUMENT=3,
    )
    sections = [
        SectionNode(title=f"Section {index}", level=1, content=f"Paragraph {index}.")
        for index in range(5)
    ]
    doc = PreprocessedDocument(
        key="large/doc.pdf",
        text="Large document",
        extension=".pdf",
        etag="1",
        last_modified=datetime.now(timezone.utc),
        sections=sections,
    )
    metadata = MetadataExtractor(settings).extract(doc)
    chunks = HierarchicalChunker(settings).chunk(doc, metadata)
    assert len(chunks) == settings.chunk_max_chunks_per_document
    assert chunks[-1].chunk_index == settings.chunk_max_chunks_per_document - 1
    assert all(chunk.total_chunks == settings.chunk_max_chunks_per_document for chunk in chunks)


def test_hierarchical_chunker_sets_best_practice_metadata() -> None:
    settings = Settings(
        CHUNK_MIN_TOKENS=1,
        CHUNK_MAX_TOKENS=500,
        CHUNK_OVERLAP_TOKENS=10,
    )
    doc = PreprocessedDocument(
        key="well-architected/ops.pdf",
        text="Operations guidance",
        extension=".pdf",
        etag="1",
        last_modified=datetime.now(timezone.utc),
        document_title="AWS Well-Architected Framework",
        sections=[
            SectionNode(
                title="Organization",
                level=1,
                chapter="Organization",
                content="",
                children=[
                    SectionNode(
                        title="OPS01-BP03 Define organizational objectives",
                        level=2,
                        section="OPS01-BP03 Define organizational objectives",
                        best_practice_id="OPS01-BP03",
                        best_practice_title="Define organizational objectives",
                        content="Use AWS Organizations and AWS Config.",
                        page_start=17,
                    )
                ],
            )
        ],
    )
    metadata = MetadataExtractor(settings).extract(doc)
    chunks = HierarchicalChunker(settings).chunk(doc, metadata)
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.best_practice_id == "OPS01-BP03"
    assert chunk.hierarchy_path == ["Organization", "OPS01-BP03"]
    assert chunk.page_number == 17
    assert chunk.document_title == "AWS Well-Architected Framework"
