# File: src/utils/structured_logger.py
# Path: /d/Projects/autocalbridge/src/utils/structured_logger.py
# Purpose: Structured logging setup for AutoCalBridge.
#          Creates separate operational, audit, and security logs.
#          Audit and security logs use JSON Lines for machine-readability.
#          Operational logs use plain key=value text for human use.
#          Session context is automatically included when active.

"""
Structured logging.

This module implements the logging architecture decision documented at:

    docs/dev/ACB_logging_session_architecture_decision.md

Log destinations:

    logs/operational/  -> human-readable operational events
    logs/audit/        -> JSON Lines traceability events
    logs/security/     -> JSON Lines security-relevant events

Session context is read lazily inside formatter methods to avoid circular
imports during package initialization. No caller needs to pass session
fields manually.

All fields supplied through the `extra` argument to a logger call are
included in the output. Internal logging-record attributes are excluded
so the output contains only meaningful event data.
"""

import json
import logging
import os
from datetime import datetime

# Log directories.
OPERATIONAL_LOG_DIR = "logs/operational"
AUDIT_LOG_DIR = "logs/audit"
SECURITY_LOG_DIR = "logs/security"

# Logger names.
OPERATIONAL_LOGGER_NAME = "acb.operational"
AUDIT_LOGGER_NAME = "acb.audit"
SECURITY_LOGGER_NAME = "acb.security"

# Standard logging.LogRecord fields that must not be copied into event payload.
_INTERNAL_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


def _extra_fields(record):
    """
    Return a dictionary of all non-internal fields supplied via `extra`.

    Args:
        record: logging.LogRecord instance.

    Returns:
        dict: Event-specific fields, excluding standard LogRecord internals.
    """
    result = {}
    for key, value in record.__dict__.items():
        if key not in _INTERNAL_RECORD_FIELDS:
            result[key] = value
    return result


class JsonLineFormatter(logging.Formatter):
    """
    JSON Lines formatter for machine-readable logs.

    Each log record becomes one JSON object on one line. Session context
    and all extra fields are merged automatically.
    """

    def format(self, record):
        # Lazy import avoids circular dependency at module import time.
        from src.core.session_context import get_session_context

        log_entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        session_ctx = get_session_context()
        if session_ctx is not None:
            log_entry.update(session_ctx.to_dict())

        log_entry.update(_extra_fields(record))

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class OperationalFormatter(logging.Formatter):
    """
    Plain text key=value formatter for operational logs.

    The format remains human-readable while including session context and
    all extra fields supplied by the caller.
    """

    def format(self, record):
        from src.core.session_context import get_session_context

        parts = [
            f"{datetime.utcfromtimestamp(record.created).isoformat()}Z",
            f"[{record.levelname}]",
            f"logger={record.name}",
        ]

        session_ctx = get_session_context()
        if session_ctx is not None:
            parts.append(f"session_id={session_ctx.session_id}")
            parts.append(f"operator={session_ctx.operator}")
            if session_ctx.supervisor:
                parts.append(f"supervisor={session_ctx.supervisor}")

        parts.append(record.getMessage())

        for key, value in _extra_fields(record).items():
            parts.append(f"{key}={value}")

        if record.exc_info and record.exc_info[0] is not None:
            parts.append(self.formatException(record.exc_info))

        return " ".join(parts)


def _make_file_handler(log_dir, formatter):
    """
    Create a file handler inside a given log directory.

    The file name includes a timestamp to avoid overwriting previous runs.
    """
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"autocalbridge_{timestamp}.log")

    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(formatter)
    return handler


def setup_logging():
    """
    Configure the three AutoCalBridge loggers.

    This function is idempotent for the loggers it configures. It does not
    call logging.basicConfig, so other application loggers are not affected.
    """
    operational = logging.getLogger(OPERATIONAL_LOGGER_NAME)
    operational.setLevel(logging.INFO)
    operational.handlers.clear()
    operational.addHandler(
        _make_file_handler(OPERATIONAL_LOG_DIR, OperationalFormatter())
    )

    audit = logging.getLogger(AUDIT_LOGGER_NAME)
    audit.setLevel(logging.INFO)
    audit.handlers.clear()
    audit.addHandler(
        _make_file_handler(AUDIT_LOG_DIR, JsonLineFormatter())
    )

    security = logging.getLogger(SECURITY_LOGGER_NAME)
    security.setLevel(logging.INFO)
    security.handlers.clear()
    security.addHandler(
        _make_file_handler(SECURITY_LOG_DIR, JsonLineFormatter())
    )


def get_operational_logger():
    """Return the operational logger."""
    return logging.getLogger(OPERATIONAL_LOGGER_NAME)


def get_audit_logger():
    """Return the audit logger."""
    return logging.getLogger(AUDIT_LOGGER_NAME)


def get_security_logger():
    """Return the security logger."""
    return logging.getLogger(SECURITY_LOGGER_NAME)