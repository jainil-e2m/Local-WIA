"""Structured JSON logging.

Always import as ``backend.logging.config``; run the app from the repo root
(``backend.app:app``) so this package never shadows the standard library.

Log records carry IDs, counts and error classes only. Never pass message
bodies, transcript text, email addresses or provider responses to a logger.
"""
import json
import logging as std_logging
import sys
from datetime import UTC, datetime

_RESERVED = set(vars(std_logging.LogRecord("", 0, "", 0, "", None, None)))


class JsonFormatter(std_logging.Formatter):
    def format(self, record: std_logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        payload.update({k: v for k, v in vars(record).items() if k not in _RESERVED})
        if record.exc_info:
            payload["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        return json.dumps(payload, default=str)


def configure(level: str = "INFO") -> None:
    handler = std_logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = std_logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    std_logging.getLogger("httpx").setLevel("WARNING")  # httpx logs full URLs incl. query strings


def get_logger(name: str) -> std_logging.Logger:
    return std_logging.getLogger(name)
