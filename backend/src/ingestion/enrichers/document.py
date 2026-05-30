from config.logging import get_logger
from domain.models import DocumentMetadata, PreprocessedDocument

logger = get_logger(__name__)


class DocumentEnricher:
    """Generate a concise document summary before chunking."""

    def summarize(self, document: PreprocessedDocument, metadata: DocumentMetadata) -> str:
        lead = document.text.strip().replace("\n", " ")[:400]
        section_titles = [s.title for s in document.sections[:5]]
        parts = [p for p in [metadata.service, metadata.title] if p]
        prefix = " — ".join(parts)

        if section_titles:
            summary = f"{prefix}: covers {', '.join(section_titles)}. {lead}"[:500]
        else:
            summary = f"{prefix}: {lead}"[:500] if prefix else lead[:500]

        logger.info("document_summary_generated", document_id=metadata.document_id)
        return summary.strip()
