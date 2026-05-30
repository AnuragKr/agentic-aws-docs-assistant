from abc import ABC, abstractmethod

from app.ingestion.domain.chunk import Chunk


class IVectorIndexer(ABC):
    @abstractmethod
    def ensure_index(self, dimension: int) -> None:
        pass

    @abstractmethod
    def bulk_upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
        pass
