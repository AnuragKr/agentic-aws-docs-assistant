from abc import ABC, abstractmethod

from app.ingestion.domain.chunk import Chunk
from app.ingestion.domain.document import DocumentMetadata, PreprocessedDocument


class IChunker(ABC):
    @abstractmethod
    def chunk(
        self,
        document: PreprocessedDocument,
        metadata: DocumentMetadata,
    ) -> list[Chunk]:
        pass
