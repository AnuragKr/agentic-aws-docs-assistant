from config.settings import Settings
from ingestion.embeddings.provider import EmbeddingProvider


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    def __init__(self, settings: Settings) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(settings.embedding_model_id)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()

    @property
    def dimension(self) -> int:
        return int(self._model.get_sentence_embedding_dimension())
