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
