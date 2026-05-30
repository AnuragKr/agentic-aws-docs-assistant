from config.logging import get_logger
from domain.models import ChunkRecord, DocumentMetadata
from ingestion.enrichers.metadata import MetadataExtractor

logger = get_logger(__name__)


class ChunkEnricher:
    """Add chunk_summary, keywords, and topics for Agentic RAG."""

    def enrich(self, chunks: list[ChunkRecord], metadata: DocumentMetadata) -> list[ChunkRecord]:
        total = len(chunks)
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i
            chunk.total_chunks = total
            chunk.document_id = metadata.document_id
            chunk.title = metadata.title
            chunk.service = metadata.service
            chunk.service_category = metadata.service_category
            chunk.source_url = metadata.source_url
            if not chunk.keywords:
                chunk.keywords = MetadataExtractor.keywords(chunk.content)
            if not chunk.topics:
                chunk.topics = [
                    t
                    for t in [
                        metadata.service,
                        metadata.service_category,
                        chunk.section,
                        chunk.subsection,
                    ]
                    if t
                ][:5]
            if not chunk.chunk_summary:
                chunk.chunk_summary = self._summary(chunk)

        logger.info("chunks_enriched", count=len(chunks))
        return chunks

    @staticmethod
    def _summary(chunk: ChunkRecord) -> str:
        parts = [p for p in [chunk.section, chunk.subsection] if p]
        prefix = " > ".join(parts)
        lead = chunk.content.strip().replace("\n", " ")[:160]
        return f"{prefix}: {lead}"[:200] if prefix else lead[:200]
