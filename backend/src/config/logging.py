import json
import logging
import os
import socket
import sys
from datetime import datetime, timezone

import structlog

from config.settings import Settings


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


def _resolve_log_level(level: str) -> int:
    return getattr(logging, level.upper(), logging.INFO)


def _memory_rss_mb() -> float | None:
    """Resident set size in MB (Linux /proc; None elsewhere)."""
    try:
        with open("/proc/self/status", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return round(int(line.split()[1]) / 1024, 1)
    except OSError:
        return None
    return None


def log_memory(event: str, logger=None, **fields) -> None:
    """Log process RSS — useful for spotting OOM pressure in CloudWatch."""
    rss = _memory_rss_mb()
    if rss is not None:
        fields["memory_rss_mb"] = rss
    (logger or get_logger("memory")).info(event, **fields)


def _cloudwatch_stream_name(settings: Settings) -> str:
    if settings.cloudwatch_log_stream:
        return settings.cloudwatch_log_stream
    host = socket.gethostname().split(".")[0]
    return f"{host}-{os.getpid()}"


def _attach_cloudwatch_handler(settings: Settings, log_level: int) -> None:
    import watchtower

    handler = watchtower.CloudWatchLogHandler(
        log_group=settings.cloudwatch_log_group,
        stream_name=_cloudwatch_stream_name(settings),
        use_queues=True,
        send_interval=5,
        max_batch_size=10,
        create_log_group=False,
    )
    handler.setLevel(log_level)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(handler)


def setup_logging(settings: Settings | None = None, *, level: str | None = None) -> None:
    log_level_name = level or (settings.log_level if settings else "INFO")
    log_level = _resolve_log_level(log_level_name)

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        stream=sys.stdout,
        force=True,
    )

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    if settings and settings.cloudwatch_logs_enabled:
        if not settings.cloudwatch_log_group:
            raise ConfigurationError(
                "CLOUDWATCH_LOG_GROUP is required when CLOUDWATCH_LOGS_ENABLED=true"
            )
        _attach_cloudwatch_handler(settings, log_level)
        get_logger(__name__).info(
            "cloudwatch_logging_enabled",
            log_group=settings.cloudwatch_log_group,
            stream=_cloudwatch_stream_name(settings),
        )


def get_logger(name: str):
    return structlog.get_logger(name)
