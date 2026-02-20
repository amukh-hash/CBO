from __future__ import annotations

import logging
import re
from typing import Any


class SafePHIFormatter(logging.Formatter):
    _patterns = [
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        re.compile(r"\b\d{10}\b"),
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
        re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"),
        re.compile(r"\b(John\s+Doe|Jane\s+Doe|Alice\s+Patient)\b", re.I),
    ]

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if record.exc_info:
            exc_type = record.exc_info[0].__name__ if record.exc_info[0] else "Exception"
            message = f"{message} [exception={exc_type}]"
            record.exc_info = None
            record.exc_text = None
        for pattern in self._patterns:
            message = pattern.sub("[REDACTED]", message)
        record.msg = message
        record.args = ()
        return super().format(record)


class PHIRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for pattern in SafePHIFormatter._patterns:
            msg = pattern.sub("[REDACTED]", msg)
        record.msg = msg
        record.args = ()
        # Keep tracebacks out of default logs; diagnostics can be collected separately.
        if record.exc_info:
            record.exc_info = None
            record.exc_text = None
        return True


def get_logger(name: str = "cb_organizer") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.addFilter(PHIRedactionFilter())
    formatter = SafePHIFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def safe_log(logger: logging.Logger, level: int, message: str, **_: Any) -> None:
    logger.log(level, message)
