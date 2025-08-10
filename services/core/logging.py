"""
Logging configuration for services
"""

import logging
import sys
from typing import Optional


def configure_logging(
    level: str = "INFO", format_type: str = "json", service_name: Optional[str] = None
) -> None:
    """
    Configure logging for services

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        format_type: Format type ("json" or "text")
        service_name: Service name to include in logs
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Clear any existing handlers
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)

    if format_type == "json":
        # Structured JSON logging for production
        import datetime
        import json

        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                    "level": record.levelname,
                    "message": record.getMessage(),
                    "logger": record.name,
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }

                if service_name:
                    log_entry["service"] = service_name

                # Add exception info if present
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)

                # Add extra fields
                if hasattr(record, "extra_fields"):
                    log_entry.update(record.extra_fields)

                return json.dumps(log_entry)

        formatter = JsonFormatter()
    else:
        # Human-readable text logging for development
        format_string = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        if service_name:
            format_string = f"%(asctime)s [%(levelname)s] {service_name}.%(name)s: %(message)s"

        formatter = logging.Formatter(format_string)

    handler.setFormatter(formatter)
    handler.setLevel(log_level)

    # Configure root logger
    root.setLevel(log_level)
    root.addHandler(handler)

    # Set specific loggers to appropriate levels
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("dropbox").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)


def get_logger(name: str, extra_fields: Optional[dict] = None) -> logging.Logger:
    """
    Get a logger with optional extra fields for structured logging

    Args:
        name: Logger name
        extra_fields: Extra fields to include in all log messages

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)

    if extra_fields:
        # Create adapter to add extra fields
        class ExtraFieldsAdapter(logging.LoggerAdapter):
            def process(self, msg, kwargs):
                # Add extra fields to the record
                if "extra" not in kwargs:
                    kwargs["extra"] = {}
                kwargs["extra"]["extra_fields"] = self.extra
                return msg, kwargs

        return ExtraFieldsAdapter(logger, extra_fields)

    return logger
