"""Logging configuration."""

import sys

from loguru import logger


def configure_logging(level: str = "INFO") -> None:
    """Configure loguru sinks for the application."""
    logger.remove()
    logger.add(sys.stderr, level=level, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}")
    log_dir = __import__("presentations.config.settings", fromlist=["get_settings"]).get_settings().data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(str(log_dir / "pptx.log"), rotation="10 MB", retention="7 days", level=level)
