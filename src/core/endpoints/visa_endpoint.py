# File: src/core/endpoints/visa_endpoint.py
# Path: /d/Projects/autocalbridge/src/core/endpoints/visa_endpoint.py
# Purpose: InstrumentEndpoint adapter for physical PyVISA instruments.
#          Includes structured operational and audit logging with session
#          context automatically attached when active.
#          Optional CommandPolicy enforcement is supported so physical and
#          simulator endpoints share one security seam.

"""
PyVISA endpoint adapter.

This adapter wraps a raw PyVISA resource object behind the standard
AutoCalBridge instrument endpoint contract.

The raw PyVISA resource must never cross the instrument abstraction boundary.
ACB code may depend only on the methods defined by InstrumentEndpoint:

    open(resource_string, timeout_ms)
    write(command)
    query(command)
    close()

Every open, write, query, and close action is logged through the structured
logging system. Session context is attached automatically by the logging
formatter when a session context is active.

Query responses are cleaned of trailing carriage return and line feed
characters so audit logs and returned values are consistent and human-safe.

An optional CommandPolicy may be supplied at construction time. If present,
write and query commands are validated before they reach the VISA resource.
This gives physical endpoints the same command allowlist protection as
simulator endpoints.
"""

from typing import Optional

from .instrument_endpoint import InstrumentEndpoint, InstrumentEndpointError

# VisaManager is the existing low-level VISA connection provider inside ACB.
from src.core.visa_manager import VisaManager

# Structured loggers. Audit captures command/response traces for calibration
# traceability. Operational captures lifecycle events for debugging.
from src.utils.structured_logger import get_operational_logger, get_audit_logger

# CommandPolicy gives physical endpoints the same validation seam as
# simulator endpoints. The policy is optional so existing direct callers
# without policy data remain compatible.
from security.command_policy import CommandPolicy


class PyVisaEndpoint(InstrumentEndpoint):
    """
    Endpoint adapter for physical instruments reachable through PyVISA.

    This class wraps the raw PyVISA resource returned by VisaManager and
    translates PyVISA/socket failures into InstrumentEndpointError.
    """

    def __init__(
        self,
        visa_manager: Optional[VisaManager] = None,
        command_policy: Optional[CommandPolicy] = None,
    ) -> None:
        """
        Initialise the PyVISA endpoint.

        Args:
            visa_manager: Optional VisaManager instance. If not supplied, a new
                VisaManager is created internally. Supplying one from outside
                allows ACB to share a single VISA resource manager across
                multiple endpoints.
            command_policy: Optional CommandPolicy instance. If supplied, all
                write and query commands are validated before being sent to
                the physical instrument.
        """
        self._visa_manager = visa_manager if visa_manager is not None else VisaManager()
        self._resource = None
        self._tag = None
        self._resource_string: Optional[str] = None
        self._timeout_ms: int = 5000
        self._command_policy: Optional[CommandPolicy] = command_policy

        self._operational_logger = get_operational_logger()
        self._audit_logger = get_audit_logger()

    # ------------------------------------------------------------------
    # Endpoint contract
    # ------------------------------------------------------------------

    def open(self, resource_string: str, timeout_ms: int = 5000) -> None:
        """
        Open a physical VISA instrument resource.

        Args:
            resource_string: VISA resource string, e.g.
                "TCPIP0::192.168.1.50::inst0::INSTR".
            timeout_ms: Communication timeout in milliseconds.

        Raises:
            InstrumentEndpointError: If the resource string is empty, or the
                VISA open fails.
        """
        if not resource_string:
            raise InstrumentEndpointError(
                "VISA resource string is empty.",
                endpoint_type="visa",
                resource_string=resource_string,
            )

        self._resource_string = resource_string
        self._timeout_ms = timeout_ms

        # Use a unique tag for this endpoint so a shared VisaManager can track
        # multiple endpoint sessions without tag collisions.
        self._tag = f"visa:{id(self)}"

        self._operational_logger.info(
            "Opening VISA endpoint",
            extra={
                "event_type": "visa_open",
                "resource_string": resource_string,
            },
        )

        try:
            resource = self._visa_manager.open_instrument(
                resource_string,
                timeout=timeout_ms,
                tag=self._tag,
            )
        except Exception as exc:
            self._operational_logger.error(
                "VISA open failed",
                extra={
                    "event_type": "visa_open_failed",
                    "resource_string": resource_string,
                    "error": str(exc),
                },
            )
            raise InstrumentEndpointError(
                f"Failed to open VISA resource: {resource_string!r}",
                endpoint_type="visa",
                resource_string=resource_string,
                cause=exc,
            ) from exc

        if resource is None:
            self._tag = None
            self._operational_logger.error(
                "VISA open returned no resource",
                extra={
                    "event_type": "visa_open_failed",
                    "resource_string": resource_string,
                    "error": "resource is None",
                },
            )
            raise InstrumentEndpointError(
                f"VISA resource was not opened: {resource_string!r}",
                endpoint_type="visa",
                resource_string=resource_string,
            )

        self._resource = resource
        self._operational_logger.info(
            "VISA endpoint opened",
            extra={
                "event_type": "visa_open_success",
                "resource_string": resource_string,
            },
        )

    def write(self, command: str) -> None:
        """
        Send a setting or event command to the physical instrument.

        If a CommandPolicy is present, the command is validated first. Invalid
        commands are rejected with a controlled InstrumentEndpointError.

        Args:
            command: One SCPI or vendor command string.

        Raises:
            InstrumentEndpointError: If the endpoint is not open, command is
                rejected by policy, or the VISA write fails.
        """
        self._ensure_ready()
        self._validate_command(command)

        # Audit log every write command. This is the calibration traceability
        # record and must not be omitted.
        self._audit_logger.info(
            "VISA write",
            extra={
                "event_type": "command_write",
                "command": command,
                "resource_string": self._resource_string,
            },
        )

        try:
            self._resource.write(command)
        except Exception as exc:
            self._audit_logger.error(
                "VISA write failed",
                extra={
                    "event_type": "command_write_failed",
                    "command": command,
                    "resource_string": self._resource_string,
                    "error": str(exc),
                },
            )
            raise InstrumentEndpointError(
                f"VISA write failed for command: {command!r}",
                endpoint_type="visa",
                resource_string=self._resource_string,
                cause=exc,
            ) from exc

    def query(self, command: str) -> str:
        """
        Send a query to the physical instrument and return its response.

        If a CommandPolicy is present, the command is validated first. Invalid
        queries are rejected with a controlled InstrumentEndpointError.

        Args:
            command: One query string, e.g. "*IDN?".

        Returns:
            str: Response string from the instrument with trailing line
                terminators removed.

        Raises:
            InstrumentEndpointError: If the endpoint is not open, command is
                rejected by policy, or the VISA query fails.
        """
        self._ensure_ready()
        self._validate_command(command)

        self._audit_logger.info(
            "VISA query",
            extra={
                "event_type": "command_query",
                "command": command,
                "resource_string": self._resource_string,
            },
        )

        try:
            response = self._resource.query(command)
        except Exception as exc:
            self._audit_logger.error(
                "VISA query failed",
                extra={
                    "event_type": "command_query_failed",
                    "command": command,
                    "resource_string": self._resource_string,
                    "error": str(exc),
                },
            )
            raise InstrumentEndpointError(
                f"VISA query failed for command: {command!r}",
                endpoint_type="visa",
                resource_string=self._resource_string,
                cause=exc,
            ) from exc

        if response is None:
            response_text = ""
        else:
            # Strip only trailing carriage return and line feed characters.
            # This keeps audit logs and returned values clean without
            # removing meaningful leading/trailing spaces.
            response_text = str(response).rstrip("\r\n")

        self._audit_logger.info(
            "VISA query response",
            extra={
                "event_type": "command_response",
                "command": command,
                "response": response_text,
                "resource_string": self._resource_string,
            },
        )

        return response_text

    def close(self) -> None:
        """
        Close the physical VISA resource.

        close() is idempotent. The underlying VisaManager is asked to close the
        tagged resource. After close, the endpoint cannot be reused until open()
        is called again.
        """
        tag = self._tag
        resource_string = self._resource_string

        if tag is None:
            return

        self._tag = None
        self._resource = None

        self._operational_logger.info(
            "Closing VISA endpoint",
            extra={
                "event_type": "visa_close",
                "resource_string": resource_string,
            },
        )

        try:
            self._visa_manager.close_instrument(tag)
        except Exception as exc:
            # close() is intended to be safe and idempotent. The error is
            # wrapped for internal visibility, not re-raised, because callers
            # often call close() during cleanup.
            self._operational_logger.error(
                "VISA close failed",
                extra={
                    "event_type": "visa_close_failed",
                    "resource_string": resource_string,
                    "error": str(exc),
                },
            )
            raise InstrumentEndpointError(
                "Failed to close VISA instrument.",
                endpoint_type="visa",
                resource_string=resource_string,
                cause=exc,
            ) from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_ready(self) -> None:
        """
        Ensure the VISA resource has been opened.

        Raises:
            InstrumentEndpointError: If open() has not been called or close()
                has already released the resource.
        """
        if self._resource is None:
            raise InstrumentEndpointError(
                "VISA endpoint is not open.",
                endpoint_type="visa",
                resource_string=self._resource_string,
            )

    def _validate_command(self, command: str) -> None:
        """
        Validate a command against the optional CommandPolicy.

        If no policy is present, validation is a no-op and behavior matches
        the earlier version of PyVisaEndpoint.

        Args:
            command: Raw command string.

        Raises:
            InstrumentEndpointError: If the policy rejects the command.
        """
        if self._command_policy is None:
            return

        is_valid, error_message = self._command_policy.validate(command)

        if not is_valid:
            raise InstrumentEndpointError(
                f"Command rejected by policy: {error_message}",
                endpoint_type="visa",
                resource_string=self._resource_string,
            )