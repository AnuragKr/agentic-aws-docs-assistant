from unittest.mock import patch

from config.logging import log_memory, setup_logging
from config.settings import Settings


def test_setup_logging_without_cloudwatch():
    settings = Settings(
        LOG_LEVEL="INFO",
        CLOUDWATCH_LOGS_ENABLED=False,
    )
    setup_logging(settings)


def test_setup_logging_cloudwatch_requires_log_group():
    settings = Settings(
        LOG_LEVEL="INFO",
        CLOUDWATCH_LOGS_ENABLED=True,
        CLOUDWATCH_LOG_GROUP="",
    )
    try:
        setup_logging(settings)
        assert False, "expected ConfigurationError"
    except Exception as exc:
        assert "CLOUDWATCH_LOG_GROUP" in str(exc)


@patch("config.logging._memory_rss_mb", return_value=512.5)
def test_log_memory_includes_rss(_mock_rss):
    settings = Settings(LOG_LEVEL="INFO")
    setup_logging(settings)
    log_memory("test_memory_event", key="doc.pdf")
