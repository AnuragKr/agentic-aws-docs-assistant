import re
from collections import Counter

from config.settings import Settings
from config.logging import get_logger
from config.utils import document_id_from_key
from domain.models import DocumentMetadata, PreprocessedDocument

logger = get_logger(__name__)

STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with", "is", "are",
    "this", "that", "by", "as", "at", "from", "be", "can", "you", "your", "it", "will",
}

SERVICE_CATEGORIES = {
    "lambda": "Compute",
    "ec2": "Compute",
    "ecs": "Compute",
    "eks": "Compute",
    "s3": "Storage",
    "ebs": "Storage",
    "iam": "Security",
    "kms": "Security",
    "vpc": "Networking",
    "cloudfront": "Networking",
    "rds": "Database",
    "dynamodb": "Database",
    "cloudwatch": "Monitoring",
}


class MetadataExtractor:
    def __init__(self, settings: Settings) -> None:
        self._docs_base = settings.docs_base_url.rstrip("/")

    def extract(self, document: PreprocessedDocument) -> DocumentMetadata:
        parts = [p for p in document.key.split("/") if p]
        title = self._title(document, parts)
        service, category = self._service_and_category(parts)

        metadata = DocumentMetadata(
            document_id=document_id_from_key(document.key),
            title=title,
            service=service,
            service_category=category,
            source_url=f"{self._docs_base}/{document.key}",
            document_type=self._document_type(parts),
            source_key=document.key,
            last_modified=document.last_modified,
            etag=document.etag,
            sections=document.sections,
        )
        logger.info("metadata_extracted", document_id=metadata.document_id, service=service)
        return metadata

    @staticmethod
    def _title(document: PreprocessedDocument, parts: list[str]) -> str:
        if document.sections:
            return document.sections[0].title
        name = parts[-1] if parts else document.key
        return re.sub(r"\.[^.]+$", "", name).replace("-", " ").replace("_", " ").title()

    @staticmethod
    def _service_and_category(parts: list[str]) -> tuple[str | None, str | None]:
        if not parts:
            return None, None
        service_key = parts[0].lower()
        service = parts[0].replace("-", " ").title()
        category = SERVICE_CATEGORIES.get(service_key)
        if service.lower() in {"docs", "documentation", "latest"} and len(parts) > 1:
            service_key = parts[1].lower()
            service = parts[1].replace("-", " ").title()
            category = SERVICE_CATEGORIES.get(service_key)
        return service, category

    @staticmethod
    def _document_type(parts: list[str]) -> str | None:
        joined = "/".join(parts).lower()
        for label in ("best-practices", "api-reference", "guide", "developer-guide"):
            if label in joined:
                return label
        return None

    @staticmethod
    def keywords(text: str, limit: int = 8) -> list[str]:
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
        filtered = [w for w in words if w not in STOPWORDS]
        return [w for w, _ in Counter(filtered).most_common(limit)]
