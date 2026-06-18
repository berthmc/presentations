"""Logging configuration."""

import sys

from loguru import logger

_LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | {level} | {extra[run_id]} | {extra[stage]} | "
    "rev={extra[revision]} | {name} | {message}"
)


def configure_logging(level: str = "INFO") -> None:
    """Configure loguru sinks for the application."""
    logger.remove()
    logger.configure(extra={"run_id": "-", "stage": "-", "revision": "-"})
    logger.add(sys.stderr, level=level, format=_LOG_FORMAT)
    log_dir = __import__("presentations.config.settings", fromlist=["get_settings"]).get_settings().data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(str(log_dir / "pptx.log"), rotation="10 MB", retention="7 days", level=level, format=_LOG_FORMAT)
