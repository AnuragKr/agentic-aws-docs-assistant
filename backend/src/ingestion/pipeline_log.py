import time
from contextlib import contextmanager
from typing import Any, Iterator

from config.logging import get_logger

logger = get_logger(__name__)


@contextmanager
def log_stage(stage: str, *, document_key: str, **context: Any) -> Iterator[None]:
    started = time.perf_counter()
    logger.info("pipeline_stage_start", stage=stage, document_key=document_key, **context)
    try:
        yield
    except Exception as exc:
        logger.error(
            "pipeline_stage_failed",
            stage=stage,
            document_key=document_key,
            error=str(exc),
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            **context,
        )
        raise
    else:
        logger.info(
            "pipeline_stage_complete",
            stage=stage,
            document_key=document_key,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            **context,
        )


def log_gap(stage: str, *, document_key: str, reason: str, **context: Any) -> None:
    logger.warning(
        "pipeline_gap",
        stage=stage,
        document_key=document_key,
        reason=reason,
        **context,
    )
