from app.core.config import Settings
from app.ingestion.ports.embeddings import IEmbeddingProvider


class EmbeddingService:
    def __init__(self, provider: IEmbeddingProvider, settings: Settings) -> None:
        self._provider = provider
        self._settings = settings

    @property
    def dimension(self) -> int:
        return self._provider.dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        batch_size = self._settings.embedding_batch_size
        results: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            results.extend(self._provider.embed_documents(batch))
        return results
