"""Central logging configuration for the app."""

import logging
import sys

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class FlushingStreamHandler(logging.StreamHandler):
    """StreamHandler that flushes after each emit so logs show under uvicorn."""

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


def setup_logging(level: str = "INFO") -> None:
    """Configure root and app loggers to output to console."""
    level_value = getattr(logging, level.upper(), logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # stderr so logs show immediately (stdout often buffered under uvicorn)
    handler = FlushingStreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level_value)
    if not root.handlers:
        root.addHandler(handler)

    # App logger inherits from root (no extra handler = no duplicate lines)
    logging.getLogger("app").setLevel(level_value)

    # Reduce noise from third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str = "app") -> logging.Logger:
    """Return a logger for the given name (default: app)."""
    return logging.getLogger(name)
