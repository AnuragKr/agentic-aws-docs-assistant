import re
from collections import Counter
from datetime import datetime, timezone

from app.core.config import Settings
from app.ingestion.domain.chunk import Chunk
from app.ingestion.domain.document import DocumentMetadata

STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with", "is", "are",
    "this", "that", "by", "as", "at", "from", "be", "can", "you", "your", "it", "will",
}


class MetadataExtractor:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def document_metadata(self, key: str) -> DocumentMetadata:
        parts = [p for p in key.split("/") if p]
        name = parts[-1] if parts else key
        service = self._infer_service(parts)
        doc_type = self._infer_document_type(parts)
        topics = [p.replace("-", " ").title() for p in parts[:-1]][:5]
        source_url = f"{self._settings.docs_base_url.rstrip('/')}/{key}"

        return DocumentMetadata(
            document_name=name,
            source_url=source_url,
            service=service,
            document_type=doc_type,
            topics=topics,
        )

    def enrich_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        now = datetime.now(timezone.utc)
        for chunk in chunks:
            chunk.ingestion_timestamp = now
            chunk.keywords = self._keywords(chunk.content)
            if not chunk.topics and chunk.section_hierarchy:
                chunk.topics = chunk.section_hierarchy[:3]
        return chunks

    @staticmethod
    def _infer_service(parts: list[str]) -> str | None:
        if not parts:
            return None
        candidate = parts[0].replace("-", " ")
        if candidate.lower() in {"docs", "documentation", "latest"}:
            return parts[1].replace("-", " ").title() if len(parts) > 1 else None
        return candidate.title()

    @staticmethod
    def _infer_document_type(parts: list[str]) -> str | None:
        joined = "/".join(parts).lower()
        for label in ("best-practices", "api-reference", "guide", "developer-guide"):
            if label in joined:
                return label
        return None

    @staticmethod
    def _keywords(text: str, limit: int = 8) -> list[str]:
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
        filtered = [w for w in words if w not in STOPWORDS]
        counts = Counter(filtered)
        return [w for w, _ in counts.most_common(limit)]
