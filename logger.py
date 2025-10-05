"""Shared logging configuration for the service."""

import logging
import os
from pathlib import Path


def setup_logger(name: str) -> logging.Logger:
    """
    Setup logger with console output and optional file logging in dev mode.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    handlers = []

    # Always add StreamHandler for console output
    handlers.append(logging.StreamHandler())

    # Only add FileHandler if DEV_MODE=1
    if os.getenv("DEV_MODE") == "1":
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "console.txt"
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True,
    )

    return logging.getLogger(name)
