"""Structured JSON logging configuration shared across backend services and integrations."""

from __future__ import annotations

import logging
import sys

from pythonjsonlogger import jsonlogger

DEFAULT_SERVICE = "sre-agent"


class ServiceJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that ensures required observability fields are always present."""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault("timestamp", self.formatTime(record, self.datefmt))
        log_record.setdefault("level", record.levelname)
        log_record.setdefault("service", getattr(record, "service", DEFAULT_SERVICE))
        log_record.setdefault("node_name", getattr(record, "node_name", None))
        log_record.setdefault("incident_id", getattr(record, "incident_id", None))


def get_logger(name: str) -> logging.Logger:
    """Create or return a logger configured for structured JSON output."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    formatter = ServiceJsonFormatter("%(timestamp)s %(level)s %(name)s %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
