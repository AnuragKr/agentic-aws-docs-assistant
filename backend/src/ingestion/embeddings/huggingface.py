from threading import Lock

from config.logging import ConfigurationError
from config.settings import Settings
from config.utils import with_retry
from domain.models import ChunkRecord, DocumentMetadata
from ingestion.embeddings.provider import EmbeddingProvider
from ingestion.enrichers.chunks import build_embedding_text


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    def __init__(self, settings: Settings) -> None:
        from sentence_transformers import SentenceTransformer

        self._batch_size = settings.embedding_batch_size
        self._dimension = settings.embedding_dimension
        self._encode_lock = Lock()
        self._model = SentenceTransformer(settings.embedding_model_id)

        model_dim = int(
            getattr(self._model, "get_embedding_dimension", self._model.get_sentence_embedding_dimension)()
        )
        if model_dim != self._dimension:
            raise ConfigurationError(
                f"Model {settings.embedding_model_id!r} outputs {model_dim} dims; "
                f"expected EMBEDDING_DIMENSION={self._dimension}"
            )

    @with_retry()
    def embed_documents(
        self,
        chunks: list[ChunkRecord],
        metadata: DocumentMetadata,
    ) -> list[list[float]]:
        if not chunks:
            return []

        texts = [build_embedding_text(chunk, metadata) for chunk in chunks]
        vectors: list[list[float]] = []
        with self._encode_lock:
            for start in range(0, len(texts), self._batch_size):
                batch = texts[start : start + self._batch_size]
                encoded = self._model.encode(batch, normalize_embeddings=True)
                vectors.extend(v.tolist() for v in encoded)
        return vectors

    @with_retry()
    def embed_query(self, text: str) -> list[float]:
        with self._encode_lock:
            return self._model.encode(text, normalize_embeddings=True).tolist()

    @property
    def dimension(self) -> int:
        return self._dimension
