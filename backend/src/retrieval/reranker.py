from threading import Lock

from config.logging import get_logger
from config.settings import Settings
from domain.models import RetrievedChunk

logger = get_logger(__name__)


class CrossEncoderReranker:
    """Rerank vector-search candidates with a cross-encoder model."""

    def __init__(self, settings: Settings) -> None:
        from sentence_transformers import CrossEncoder

        self._model_id = settings.reranker_model_id
        logger.info("reranker_loading", model=self._model_id)
        self._model = CrossEncoder(self._model_id)
        logger.info("reranker_ready", model=self._model_id)

    def rerank(
        self,
        query: str,
        candidates: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        if not candidates:
            return []

        pairs = [(query, chunk.content) for chunk in candidates]
        scores = self._model.predict(pairs)

        ranked = sorted(
            zip(candidates, scores, strict=True),
            key=lambda item: float(item[1]),
            reverse=True,
        )
        results: list[RetrievedChunk] = []
        for chunk, score in ranked:
            results.append(chunk.model_copy(update={"score": float(score)}))
        return results


class RerankerSingleton:
    """Singleton: load cross-encoder once per process."""

    _lock = Lock()
    _instances: dict[str, CrossEncoderReranker] = {}

    @classmethod
    def get(cls, settings: Settings) -> CrossEncoderReranker | None:
        if not settings.reranker_enabled:
            return None
        key = settings.reranker_model_id
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = CrossEncoderReranker(settings)
            return cls._instances[key]

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._instances.clear()


def get_reranker(settings: Settings) -> CrossEncoderReranker | None:
    return RerankerSingleton.get(settings)
