import json
import logging
from datetime import datetime, timezone

import structlog


class NotFoundError(Exception):
    pass


class ConfigurationError(Exception):
    pass


class UnsupportedFormatError(Exception):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_json(payload: object) -> str:
    if hasattr(payload, "model_dump"):
        return json.dumps(payload.model_dump(mode="json"), default=str)
    return json.dumps(payload, default=str)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
    )


def get_logger(name: str):
    return structlog.get_logger(name)
