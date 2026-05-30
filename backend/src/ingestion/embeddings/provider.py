from abc import ABC, abstractmethod
from threading import Lock


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        ...


class EmbeddingProviderSingleton:
    """Singleton: load embedding models once per process."""

    _lock = Lock()
    _instances: dict[str, EmbeddingProvider] = {}

    @classmethod
    def get(cls, name: str, factory) -> EmbeddingProvider:
        with cls._lock:
            if name not in cls._instances:
                cls._instances[name] = factory()
            return cls._instances[name]

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._instances.clear()
