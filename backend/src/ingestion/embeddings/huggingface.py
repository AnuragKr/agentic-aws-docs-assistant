from config.settings import Settings
from config.utils import with_retry
from ingestion.embeddings.provider import EmbeddingProvider


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    def __init__(self, settings: Settings) -> None:
        from sentence_transformers import SentenceTransformer

        self._batch_size = settings.embedding_batch_size
        self._model = SentenceTransformer(settings.embedding_model_id)

    @with_retry()
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            encoded = self._model.encode(batch, normalize_embeddings=True)
            vectors.extend(v.tolist() for v in encoded)
        return vectors

    @with_retry()
    def embed_query(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()

    @property
    def dimension(self) -> int:
        return int(self._model.get_sentence_embedding_dimension())
