from abc import ABC, abstractmethod


class IEmbeddingProvider(ABC):
    @property
    @abstractmethod
    def model_id(self) -> str:
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        pass
