# File: security/logger.py
# Path: /d/Projects/autocalbridge/security/logger.py
# Purpose: Security audit logging wrapper for AutoCalBridge.
#          Uses the structured security logger and session context.

"""
Security audit logger.

This module provides a small, reusable audit logger for security-relevant
events at the instrument endpoint and transport boundaries.

Design rules:

- This module contains logging logic only.
- Redaction fields are supplied externally through configuration.
- No sensitive operational values are hardcoded here.
- Internal stack traces may be logged to file, but they must never be sent
  to an instrument client.
- The actual log destination and format are controlled by
  src.utils.structured_logger.

Use in endpoints and security modules as:

    audit = SecurityAuditLogger(redact_fields={"resource_string"})
    audit.command_rejected("READ?")
"""

from src.utils.structured_logger import get_security_logger


class SecurityAuditLogger:
    """
    Wrapper around the structured security logger.

    The wrapper standardises security event formatting and applies externally
    supplied redaction fields. All events are written as JSON Lines to the
    security log directory.
    """

    def __init__(self, logger_name="acb.security", redact_fields=None):
        """
        Initialise the security audit logger.

        Args:
            logger_name: Kept for backward compatibility. The structured
                security logger is always used regardless of this value.
            redact_fields: Optional iterable of field names whose values must
                be redacted in log output.
        """
        # The structured security logger is the single destination.
        self._logger = get_security_logger()
        self._redact_fields = set(redact_fields or set())

    # ------------------------------------------------------------------
    # Generic event logging
    # ------------------------------------------------------------------

    def log_security_event(self, event_type, message="", **fields):
        """
        Log one security event.

        The event type and supplied fields are rendered in JSON Lines.
        Any field whose name is present in redact_fields is rendered as
        `***` instead of its actual value.

        Args:
            event_type: Short event name, e.g. "command_rejected".
            message: Human-readable event message.
            **fields: Additional key/value context.
        """
        safe_fields = {}
        for key, value in fields.items():
            if key in self._redact_fields:
                safe_fields[key] = "***"
            else:
                safe_fields[key] = value

        # Extra is used so JsonLineFormatter picks up the structured fields.
        extra = {"event_type": event_type}
        extra.update(safe_fields)

        self._logger.warning(message, extra=extra)

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------

    def command_rejected(self, command, reason, **fields):
        """
        Log a rejected instrument command.

        Args:
            command: The rejected command.
            reason: Controlled rejection reason.
            **fields: Additional context fields.
        """
        self.log_security_event(
            "command_rejected",
            message=reason,
            command=command,
            **fields,
        )

    def validation_rejected(self, subject, reason, **fields):
        """
        Log a generic input validation rejection.

        Args:
            subject: The input value or input category that was rejected.
            reason: Controlled rejection reason.
            **fields: Additional context fields.
        """
        self.log_security_event(
            "validation_rejected",
            message=reason,
            subject=subject,
            **fields,
        )

    def transport_rejected(self, bind_host, bind_port, reason, **fields):
        """
        Log a rejected transport bind attempt.

        Args:
            bind_host: Candidate bind host.
            bind_port: Candidate bind port.
            reason: Controlled rejection reason.
            **fields: Additional context fields.
        """
        self.log_security_event(
            "transport_rejected",
            message=reason,
            bind_host=bind_host,
            bind_port=bind_port,
            **fields,
        )