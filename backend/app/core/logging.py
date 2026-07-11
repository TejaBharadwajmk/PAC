"""
PAC Backend — Logging Configuration

Structured console logging with timestamps, level names, and module info.
Log level is driven by DEBUG setting in config.
"""

import logging
import sys

from app.config import settings


def setup_logging() -> None:
    """
    Configure root logger with formatted output.
    Called once at application startup in main.py.
    """
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    fmt = (
        "%(asctime)s | %(levelname)-8s | %(name)-35s | %(message)s"
    )
    date_fmt = "%Y-%m-%d %H:%M:%S"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=date_fmt))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress noisy library loggers
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("passlib").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging initialised | level={logging.getLevelName(log_level)} "
        f"| env={settings.ENVIRONMENT}"
    )
