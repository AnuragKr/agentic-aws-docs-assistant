import hashlib
import unicodedata
from functools import wraps
from typing import Callable, TypeVar

from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import Settings, get_settings

T = TypeVar("T")


def with_retry(settings: Settings | None = None) -> Callable:
    cfg = settings or get_settings()

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @retry(
            stop=stop_after_attempt(cfg.retry_max_attempts),
            wait=wait_exponential(
                multiplier=1,
                min=cfg.retry_min_wait,
                max=cfg.retry_max_wait,
            ),
            reraise=True,
        )
        @wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def document_id_from_key(source_key: str) -> str:
    return hashlib.sha256(source_key.encode()).hexdigest()[:16]


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)
