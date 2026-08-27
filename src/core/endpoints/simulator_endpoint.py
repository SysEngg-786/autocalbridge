# File: src/core/endpoints/simulator_endpoint.py
# Path: /d/Projects/autocalbridge/src/core/endpoints/simulator_endpoint.py
# Purpose: InstrumentEndpoint adapter for AutoCalBridge simulator instruments.
#          Includes structured operational and audit logging with session
#          context automatically attached when active.

"""
Simulator endpoint adapter.

This adapter wraps MockInstrument or YAMLInstrument behind the standard
AutoCalBridge instrument endpoint contract.

ACB must not see simulator-specific methods such as:

- set_target()
- set_offset()
- set_noise()
- set_fail_rate()
- set_source_value()
- get_source_value()
- enable_error()
- force_error()
- clear_error()
- clear_history()

The only methods available through this adapter are those required by the
instrument abstraction boundary:

    open(resource_string, timeout_ms)
    write(command)
    query(command)
    close()

An optional CommandPolicy can be supplied by the endpoint factory. If present,
every write and query command must pass policy validation before it reaches
the simulator.

Every write and query is logged through the structured logging system.
Session context is attached automatically by the logging formatter when a
session context is active.
"""

from typing import Any, Optional

from .instrument_endpoint import InstrumentEndpoint, InstrumentEndpointError

# Imported from the security package so simulator commands can be validated
# at the endpoint boundary. The policy object is optional; when omitted, the
# endpoint behaves exactly as before.
from security.command_policy import CommandPolicy

# Structured loggers for audit and operational events.
from src.utils.structured_logger import get_operational_logger, get_audit_logger


class SimulatorEndpoint(InstrumentEndpoint):
    """
    Endpoint adapter that wraps a simulator instrument instance.

    The simulator instance must behave like MockInstrument or YAMLInstrument:

        sim.query(command) -> str
        sim.write(command)  -> None or empty response
        sim.close()         -> no-op or resource cleanup

    The adapter translates simulator failures into InstrumentEndpointError so
    ACB only has one error type to handle.
    """

    def __init__(
        self,
        simulator: Any = None,
        command_policy: Optional[CommandPolicy] = None,
    ) -> None:
        """
        Initialise the simulator endpoint.

        Args:
            simulator: A MockInstrument or YAMLInstrument instance. The
                simulator may be supplied at construction time.
            command_policy: Optional CommandPolicy instance. If supplied, all
                write and query commands are validated before being delegated
                to the simulator.
        """
        self._simulator: Optional[Any] = simulator
        self._command_policy: Optional[CommandPolicy] = command_policy
        self._resource_string: Optional[str] = None
        self._timeout_ms: int = 5000

        self._operational_logger = get_operational_logger()
        self._audit_logger = get_audit_logger()

    # ------------------------------------------------------------------
    # Endpoint contract
    # ------------------------------------------------------------------

    def open(self, resource_string: str, timeout_ms: int = 5000) -> None:
        """
        Initialise the simulator endpoint with a logical resource string.

        The resource string is not used to open a network connection. It is
        retained as an identifier only, so ACB can log and track endpoints
        consistently with physical endpoints.

        Args:
            resource_string: Logical simulator identifier, e.g.
                "sim://keysight_34461a" or "sim://dut".
            timeout_ms: Not used for simulator endpoints. Retained for
                interface compatibility with PyVisaEndpoint.

        Raises:
            InstrumentEndpointError: If no simulator instance has been supplied.
        """
        if self._simulator is None:
            raise InstrumentEndpointError(
                "SimulatorEndpoint cannot open because no simulator instance "
                "was supplied.",
                endpoint_type="simulator",
                resource_string=resource_string,
            )

        self._resource_string = resource_string
        self._timeout_ms = timeout_ms

        self._operational_logger.info(
            "Simulator endpoint opened",
            extra={
                "event_type": "simulator_open_success",
                "resource_string": resource_string,
            },
        )

    def write(self, command: str) -> None:
        """
        Send a setting or event command to the simulator.

        If a CommandPolicy is present, the command is validated first. Invalid
        commands are rejected with a controlled InstrumentEndpointError.

        Args:
            command: One SCPI or vendor command string.

        Raises:
            InstrumentEndpointError: If the simulator has not been opened, the
                command is rejected by the policy, or the simulator write fails.
        """
        self._ensure_ready()
        self._validate_command(command)

        self._audit_logger.info(
            "Simulator write",
            extra={
                "event_type": "command_write",
                "command": command,
                "resource_string": self._resource_string,
            },
        )

        try:
            self._simulator.write(command)
        except Exception as exc:
            self._audit_logger.error(
                "Simulator write failed",
                extra={
                    "event_type": "command_write_failed",
                    "command": command,
                    "resource_string": self._resource_string,
                    "error": str(exc),
                },
            )
            raise InstrumentEndpointError(
                f"Simulator write failed for command: {command!r}",
                endpoint_type="simulator",
                resource_string=self._resource_string,
                cause=exc,
            ) from exc

    def query(self, command: str) -> str:
        """
        Send a query to the simulator and return its response.

        If a CommandPolicy is present, the command is validated first. Invalid
        queries are rejected with a controlled InstrumentEndpointError.

        Args:
            command: One query string, e.g. "*IDN?".

        Returns:
            str: Raw response from the simulator.

        Raises:
            InstrumentEndpointError: If the simulator has not been opened, the
                command is rejected by the policy, or the simulator query fails.
        """
        self._ensure_ready()
        self._validate_command(command)

        self._audit_logger.info(
            "Simulator query",
            extra={
                "event_type": "command_query",
                "command": command,
                "resource_string": self._resource_string,
            },
        )

        try:
            response = self._simulator.query(command)
        except Exception as exc:
            self._audit_logger.error(
                "Simulator query failed",
                extra={
                    "event_type": "command_query_failed",
                    "command": command,
                    "resource_string": self._resource_string,
                    "error": str(exc),
                },
            )
            raise InstrumentEndpointError(
                f"Simulator query failed for command: {command!r}",
                endpoint_type="simulator",
                resource_string=self._resource_string,
                cause=exc,
            ) from exc

        # A simulator query should return a string. If it does not, preserve the
        # boundary by converting to a string rather than leaking the type.
        if response is None:
            response_text = ""
        else:
            response_text = str(response)

        self._audit_logger.info(
            "Simulator query response",
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
        Close the simulator endpoint.

        close() is idempotent. It calls simulator.close() if the simulator has
        a close() method, then clears the internal reference so later use fails
        at _ensure_ready() rather than operating on a released object.
        """
        simulator = self._simulator
        self._simulator = None

        if simulator is None:
            return

        self._operational_logger.info(
            "Closing simulator endpoint",
            extra={
                "event_type": "simulator_close",
                "resource_string": self._resource_string,
            },
        )

        close_method = getattr(simulator, "close", None)
        if close_method is None:
            return

        try:
            close_method()
        except Exception as exc:
            # close() is intentionally idempotent and must not raise. The
            # original error is converted to InstrumentEndpointError only for
            # internal logging if needed; it is not re-raised here.
            self._operational_logger.error(
                "Simulator close failed",
                extra={
                    "event_type": "simulator_close_failed",
                    "resource_string": self._resource_string,
                    "error": str(exc),
                },
            )
            raise InstrumentEndpointError(
                "Simulator close failed.",
                endpoint_type="simulator",
                resource_string=self._resource_string,
                cause=exc,
            ) from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_ready(self) -> None:
        """
        Ensure the endpoint has an open simulator before delegating a command.

        Raises:
            InstrumentEndpointError: If open() has not been called or close()
                has already released the simulator.
        """
        if self._simulator is None:
            raise InstrumentEndpointError(
                "Simulator endpoint is not open.",
                endpoint_type="simulator",
                resource_string=self._resource_string,
            )

    def _validate_command(self, command: str) -> None:
        """
        Validate a command against the optional CommandPolicy.

        If no policy is present, validation is a no-op and behavior matches the
        earlier version of SimulatorEndpoint.

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
                endpoint_type="simulator",
                resource_string=self._resource_string,
            )