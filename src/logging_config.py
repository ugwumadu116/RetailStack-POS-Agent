# Logging configuration - RotatingFileHandler, structured format, error alerting

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Callable

# Default log directory (project root / logs)
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "retailstack_pos.log"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 5

# Optional: call this when an ERROR is logged (e.g. send to monitoring)
_error_alert_callback: Optional[Callable[[str, str], None]] = None


def set_error_alert_callback(callback: Callable[[str, str], None]):
    """Set a callback(message, level) for error alerting."""
    global _error_alert_callback
    _error_alert_callback = callback


class ErrorAlertHandler(logging.Handler):
    """Handler that invokes the alert callback on ERROR and CRITICAL."""

    def emit(self, record: logging.LogRecord):
        if record.levelno >= logging.ERROR and _error_alert_callback:
            try:
                msg = self.format(record)
                _error_alert_callback(msg, record.levelname)
            except Exception:
                self.handleError(record)


def setup_logging(
    log_path: Optional[Path] = None,
    max_bytes: int = LOG_MAX_BYTES,
    backup_count: int = LOG_BACKUP_COUNT,
    console: bool = True,
    level: int = logging.INFO,
) -> None:
    """
    Configure structured logging with file rotation and optional console.
    """
    log_path = log_path or LOG_FILE
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers when called multiple times
    for h in list(root.handlers):
        root.removeHandler(h)

    # Rotating file
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Console
    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    # Error alerting
    alert_handler = ErrorAlertHandler()
    alert_handler.setLevel(logging.ERROR)
    alert_handler.setFormatter(formatter)
    root.addHandler(alert_handler)
