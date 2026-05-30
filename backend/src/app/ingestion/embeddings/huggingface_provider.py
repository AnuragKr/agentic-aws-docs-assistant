import threading

from app.ingestion.ports.embeddings import IEmbeddingProvider


class HuggingFaceEmbeddingProvider(IEmbeddingProvider):
    _models: dict[str, object] = {}
    _lock = threading.Lock()

    def __init__(self, model_id: str) -> None:
        self._model_id = model_id
        self._dimension: int | None = None

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            self._dimension = self._get_model().get_sentence_embedding_dimension()
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._get_model().encode(texts, convert_to_numpy=True)
        return [v.tolist() for v in vectors]

    def _get_model(self):
        with self._lock:
            if self._model_id not in self._models:
                from sentence_transformers import SentenceTransformer

                self._models[self._model_id] = SentenceTransformer(self._model_id)
            return self._models[self._model_id]
