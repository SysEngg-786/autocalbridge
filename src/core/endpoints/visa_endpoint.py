# File: src/core/endpoints/visa_endpoint.py
# Path: /d/Projects/autocalbridge/src/core/endpoints/visa_endpoint.py
# Purpose: InstrumentEndpoint adapter for physical PyVISA instruments.

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

This adapter uses VisaManager as the low-level VISA connection provider.
"""

from typing import Optional

from .instrument_endpoint import InstrumentEndpoint, InstrumentEndpointError

# VisaManager is the existing low-level VISA connection provider inside ACB.
from src.core.visa_manager import VisaManager


class PyVisaEndpoint(InstrumentEndpoint):
    """
    Endpoint adapter for physical instruments reachable through PyVISA.

    This class wraps the raw PyVISA resource returned by VisaManager and
    translates PyVISA/socket failures into InstrumentEndpointError.
    """

    def __init__(self, visa_manager: Optional[VisaManager] = None) -> None:
        """
        Initialise the PyVISA endpoint.

        Args:
            visa_manager: Optional VisaManager instance. If not supplied, a new
                VisaManager is created internally. Supplying one from outside
                allows ACB to share a single VISA resource manager across
                multiple endpoints.
        """
        self._visa_manager = visa_manager if visa_manager is not None else VisaManager()
        self._resource = None
        self._tag = None
        self._resource_string: Optional[str] = None
        self._timeout_ms: int = 5000

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

        try:
            resource = self._visa_manager.open_instrument(
                resource_string,
                timeout=timeout_ms,
                tag=self._tag,
            )
        except Exception as exc:
            raise InstrumentEndpointError(
                f"Failed to open VISA resource: {resource_string!r}",
                endpoint_type="visa",
                resource_string=resource_string,
                cause=exc,
            ) from exc

        if resource is None:
            self._tag = None
            raise InstrumentEndpointError(
                f"VISA resource was not opened: {resource_string!r}",
                endpoint_type="visa",
                resource_string=resource_string,
            )

        self._resource = resource

    def write(self, command: str) -> None:
        """
        Send a setting or event command to the physical instrument.

        Args:
            command: One SCPI or vendor command string.

        Raises:
            InstrumentEndpointError: If the endpoint is not open, or the VISA
                write fails.
        """
        self._ensure_ready()

        try:
            self._resource.write(command)
        except Exception as exc:
            raise InstrumentEndpointError(
                f"VISA write failed for command: {command!r}",
                endpoint_type="visa",
                resource_string=self._resource_string,
                cause=exc,
            ) from exc

    def query(self, command: str) -> str:
        """
        Send a query to the physical instrument and return its response.

        Args:
            command: One query string, e.g. "*IDN?".

        Returns:
            str: Raw response string from the instrument. The caller may strip
                terminators or parse the value as required.

        Raises:
            InstrumentEndpointError: If the endpoint is not open, or the VISA
                query fails.
        """
        self._ensure_ready()

        try:
            response = self._resource.query(command)
        except Exception as exc:
            raise InstrumentEndpointError(
                f"VISA query failed for command: {command!r}",
                endpoint_type="visa",
                resource_string=self._resource_string,
                cause=exc,
            ) from exc

        if response is None:
            return ""
        return str(response)

    def close(self) -> None:
        """
        Close the physical VISA resource.

        close() is idempotent. The underlying VisaManager is asked to close the
        tagged resource. After close, the endpoint cannot be reused until open()
        is called again.
        """
        tag = self._tag
        self._tag = None
        self._resource = None

        if tag is None:
            return

        try:
            self._visa_manager.close_instrument(tag)
        except Exception as exc:
            # close() is intended to be safe and idempotent. The error is
            # wrapped for internal visibility, not re-raised, because callers
            # often call close() during cleanup.
            raise InstrumentEndpointError(
                "Failed to close VISA instrument.",
                endpoint_type="visa",
                resource_string=self._resource_string,
                cause=exc,
            ) from exc

    # ------------------------------------------------------------------
    # Internal helper
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