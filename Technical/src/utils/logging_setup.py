"""Standardized logging configuration for Gerhard."""
import logging
import sys


def setup_logging(name: str = None, level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger with consistent formatting.

    Args:
        name: Logger name (defaults to calling module name)
        level: Logging level (default INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name or __name__)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)

    return logger
