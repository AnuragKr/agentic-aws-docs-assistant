"""End-to-end contract: sentence chunks + full retrieval metadata."""

from datetime import datetime, timezone

from config.settings import Settings
from config.token_utils import count_tokens, get_token_encoder
from domain.models import PreprocessedDocument, SectionNode
from ingestion.chunkers.hierarchical import HierarchicalChunker
from ingestion.enrichers.chunks import ChunkEnricher
from ingestion.enrichers.metadata import MetadataExtractor
from ingestion.parsers.best_practices import parse_best_practice

REQUIRED_CHUNK_FIELDS = {
    "chunk_id",
    "document_id",
    "document_title",
    "source_file",
    "page_number",
    "total_pages",
    "chapter",
    "section",
    "hierarchy_path",
    "best_practice_id",
    "best_practice_title",
    "chunk_order",
    "total_chunks",
    "prev_chunk_id",
    "next_chunk_id",
    "services",
    "content",
    "chunk_summary",
    "keywords",
    "topics",
}


def test_enriched_chunk_metadata_contract() -> None:
    settings = Settings(
        CHUNK_MIN_TOKENS=500,
        CHUNK_TARGET_TOKENS=800,
        CHUNK_MAX_TOKENS=1200,
        CHUNK_OVERLAP_TOKENS=100,
    )
    sentence = (
        "AWS Organizations helps you centrally govern multiple accounts at scale. "
        "AWS Config continuously records resource configuration for compliance. "
    )
    content = " ".join([sentence] * 25)
    bp_title = "OPS01-BP03 Define organizational objectives"
    bp_id, bp_name = parse_best_practice(bp_title)

    doc = PreprocessedDocument(
        key="well-architected/framework.pdf",
        text=content,
        extension=".pdf",
        etag="1",
        last_modified=datetime.now(timezone.utc),
        document_title="AWS Well-Architected Framework",
        total_pages=226,
        sections=[
            SectionNode(
                title="Organization",
                level=1,
                chapter="Organization",
                content="",
                children=[
                    SectionNode(
                        title=bp_title,
                        level=2,
                        chapter="Organization",
                        section=bp_title,
                        best_practice_id=bp_id,
                        best_practice_title=bp_name,
                        content=content,
                        page_start=17,
                        page_end=20,
                    )
                ],
            )
        ],
    )

    metadata = MetadataExtractor(settings).extract(doc)
    chunks = HierarchicalChunker(settings).chunk(doc, metadata)
    chunks = ChunkEnricher().enrich(chunks, metadata)

    assert chunks
    encoder = get_token_encoder()

    for index, chunk in enumerate(chunks):
        payload = chunk.model_dump()
        missing = REQUIRED_CHUNK_FIELDS - payload.keys()
        assert not missing, f"chunk {index} missing keys: {missing}"

        assert chunk.document_title == "AWS Well-Architected Framework"
        assert chunk.source_file == "framework.pdf"
        assert chunk.page_number == 17
        assert chunk.total_pages == 226
        assert chunk.chapter == "Organization"
        assert chunk.best_practice_id == "OPS01-BP03"
        assert chunk.hierarchy_path == ["Organization", "OPS01-BP03"]
        assert chunk.chunk_order == index
        assert chunk.total_chunks == len(chunks)

        tokens = count_tokens(chunk.content, encoder)
        assert tokens <= settings.chunk_max_tokens
        if len(chunks) == 1 or index < len(chunks) - 1:
            assert tokens >= settings.chunk_min_tokens or len(chunks) == 1

        assert chunk.content.rstrip()[-1] in ".!?"
        assert chunk.chunk_summary
        assert chunk.keywords
        assert chunk.services

    assert chunks[0].prev_chunk_id is None
    if len(chunks) > 1:
        assert chunks[1].prev_chunk_id == chunks[0].chunk_id
        assert chunks[0].next_chunk_id == chunks[1].chunk_id
