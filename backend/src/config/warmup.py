from config.logging import get_logger, setup_logging
from config.settings import get_settings
from ingestion.embeddings.factory import get_embedding_provider
from retrieval.reranker import get_reranker

logger = get_logger(__name__)


def warmup_models() -> None:
    """Preload ML models at startup so first /search is not blocked for minutes."""
    settings = get_settings()
    if not settings.warmup_models_on_startup:
        logger.info("warmup_skipped")
        return

    logger.info("warmup_start", reranker_enabled=settings.reranker_enabled)
    started = __import__("time").perf_counter()

    get_embedding_provider(settings)
    logger.info("warmup_embedding_ready")

    if settings.reranker_enabled:
        logger.info(
            "warmup_reranker_start",
            model=settings.reranker_model_id,
            note="First run downloads ~1.1GB from HuggingFace — can take several minutes",
        )
        get_reranker(settings)
        logger.info("warmup_reranker_ready")

    logger.info(
        "warmup_complete",
        duration_ms=round((__import__("time").perf_counter() - started) * 1000, 2),
    )
