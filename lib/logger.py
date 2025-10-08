"""Shared logging configuration for the service."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging once at module import
_logging_configured = False


class FlushingFileHandler(logging.FileHandler):
    """FileHandler that flushes after every emit."""

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


def _configure_logging() -> None:
    """Configure root logger once."""
    global _logging_configured
    if _logging_configured:
        return

    handlers: list[logging.Handler] = []

    # Always add StreamHandler for console output
    handlers.append(logging.StreamHandler())

    # Only add FileHandler if DEV_MODE=1
    if os.getenv("DEV_MODE") == "1":
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "console.txt"
        file_handler = FlushingFileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        handlers.append(file_handler)

    # Get log level from environment, default to INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, log_level, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True,
    )

    _logging_configured = True


def setup_logger(name: str) -> logging.Logger:
    """
    Setup logger with console output and optional file logging in dev mode.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    _configure_logging()
    return logging.getLogger(name)
