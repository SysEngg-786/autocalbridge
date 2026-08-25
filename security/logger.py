# File: security/logger.py
# Path: /d/Projects/autocalbridge/security/logger.py
# Purpose: Security audit logging helper for AutoCalBridge.

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

Use in endpoints and security modules as:

    audit = SecurityAuditLogger(redact_fields={"resource_string"})
    audit.command_rejected("READ?")
"""

import logging


class SecurityAuditLogger:
    """
    Wrapper around Python logging for security audit events.

    The wrapper standardises security event formatting and applies externally
    supplied redaction fields.
    """

    def __init__(self, logger_name="acb.security", redact_fields=None):
        """
        Initialise the security audit logger.

        Args:
            logger_name: Python logger name.
            redact_fields: Optional iterable of field names whose values must
                be redacted in log output.
        """
        self._logger = logging.getLogger(logger_name)
        self._redact_fields = set(redact_fields or set())

    # ------------------------------------------------------------------
    # Generic event logging
    # ------------------------------------------------------------------

    def log_security_event(self, event_type, message="", **fields):
        """
        Log one security event.

        The event type and supplied fields are rendered in a stable format.
        Any field whose name is present in redact_fields is rendered as
        `***` instead of its actual value.

        Args:
            event_type: Short event name, e.g. "command_rejected".
            message: Human-readable event message.
            **fields: Additional key/value context.
        """
        rendered_fields = []

        for key, value in fields.items():
            if key in self._redact_fields:
                rendered_fields.append(f"{key}=***")
            else:
                rendered_fields.append(f"{key}={value}")

        prefix = f"security_event={event_type} message={message}"
        if rendered_fields:
            prefix = prefix + " " + " ".join(rendered_fields)

        self._logger.warning(prefix)

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