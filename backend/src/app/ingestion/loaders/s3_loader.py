from collections.abc import Iterator

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.observability.logging import get_logger
from app.ingestion.ports.loader import IDocumentLoader
from app.ingestion.domain.document import RawDocument
from app.infrastructure.aws.s3_repository import S3Repository

logger = get_logger(__name__)


class S3DocumentLoader(IDocumentLoader):
    def __init__(self, settings: Settings, repository: S3Repository | None = None) -> None:
        self._settings = settings
        self._repository = repository or S3Repository(settings)

    def iter_documents(
        self,
        prefix: str | None = None,
        max_documents: int | None = None,
    ) -> Iterator[RawDocument]:
        if not self._settings.s3_bucket:
            raise ConfigurationError(
                "S3_BUCKET is not configured. Set it in backend/.env when your bucket is ready."
            )

        effective_prefix = prefix if prefix is not None else self._settings.s3_prefix
        count = 0

        for key in self._repository.list_keys(effective_prefix):
            if max_documents is not None and count >= max_documents:
                break
            ext = "." + key.rsplit(".", 1)[-1].lower()
            try:
                content = self._repository.get_object_text(key)
            except Exception as exc:
                logger.warning("s3_document_load_failed", key=key, error=str(exc))
                continue
            count += 1
            logger.info("s3_document_loaded", key=key)
            yield RawDocument(key=key, content=content, extension=ext)
