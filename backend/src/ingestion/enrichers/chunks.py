from config.logging import get_logger
from domain.models import ChunkRecord, DocumentMetadata
from ingestion.enrichers.metadata import MetadataExtractor

logger = get_logger(__name__)


def build_embedding_text(chunk: ChunkRecord, metadata: DocumentMetadata) -> str:
    """Prepend parent context before embedding for better retrieval."""
    path = chunk.hierarchy_path or [p for p in [chunk.section, chunk.subsection] if p]
    context = [p for p in [metadata.title, *path] if p]
    if metadata.services:
        context.append(", ".join(metadata.services[:5]))
    if not context:
        return chunk.content
    return f"{' | '.join(context)}\n\n{chunk.content}"


class ChunkEnricher:
    """Chunk-level enrichment for Agentic RAG."""

    def enrich(self, chunks: list[ChunkRecord], metadata: DocumentMetadata) -> list[ChunkRecord]:
        total = len(chunks)
        for index, chunk in enumerate(chunks):
            chunk.chunk_index = index
            chunk.chunk_order = index
            chunk.total_chunks = total
            chunk.document_id = metadata.document_id
            chunk.title = metadata.title
            chunk.service = metadata.service
            chunk.service_category = metadata.service_category
            chunk.services = list(metadata.services)
            chunk.source_url = metadata.source_url
            chunk.source_file = metadata.source_file
            chunk.document_type = metadata.document_type
            chunk.total_pages = metadata.total_pages
            chunk.prev_chunk_id = chunks[index - 1].chunk_id if index > 0 else None
            chunk.next_chunk_id = (
                chunks[index + 1].chunk_id if index + 1 < total else None
            )
            if not chunk.keywords:
                chunk.keywords = MetadataExtractor.keywords(chunk.content)
            if not chunk.topics:
                chunk.topics = _topics(chunk, metadata)
            chunk.chunk_summary = self._summary(chunk, metadata)

        logger.info("chunks_enriched", count=len(chunks))
        return chunks

    @staticmethod
    def _summary(chunk: ChunkRecord, metadata: DocumentMetadata) -> str:
        path = " > ".join(chunk.hierarchy_path) if chunk.hierarchy_path else ""
        if not path and chunk.section:
            path = chunk.section
            if chunk.subsection:
                path = f"{path} > {chunk.subsection}"

        lead = chunk.content.strip().replace("\n", " ")[:140]
        page = f"p.{chunk.page_number}" if chunk.page_number else ""
        prefix = " | ".join(p for p in [path, page] if p)

        if prefix:
            return f"{prefix}: {lead}"[:220]
        return f"{metadata.title}: {lead}"[:220]


def _topics(chunk: ChunkRecord, metadata: DocumentMetadata) -> list[str]:
    values = [
        metadata.service,
        metadata.service_category,
        *chunk.hierarchy_path,
        *chunk.services[:3],
    ]
    seen: set[str] = set()
    topics: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            topics.append(value)
    return topics[:8]
