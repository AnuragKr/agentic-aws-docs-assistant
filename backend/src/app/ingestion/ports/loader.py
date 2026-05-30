from abc import ABC, abstractmethod
from collections.abc import Iterator

from app.ingestion.domain.document import RawDocument


class IDocumentLoader(ABC):
    @abstractmethod
    def iter_documents(
        self,
        prefix: str | None = None,
        max_documents: int | None = None,
    ) -> Iterator[RawDocument]:
        pass
