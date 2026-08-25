# File: src/core/endpoints/instrument_endpoint.py
# Path: /d/Projects/autocalbridge/src/core/endpoints/instrument_endpoint.py
# Purpose: Defines the neutral instrument endpoint contract and common error
#          type used by all AutoCalBridge instrument adapters.

"""
Instrument endpoint contract.

This module defines the only interface ACB is allowed to depend on when
controlling any instrument endpoint, whether that endpoint is:

- a simulator
- a physical VISA instrument
- a future VXI-11 transport-backed device
- any other transport adapter

The contract intentionally contains only the methods required by the
AutoCalBridge instrument abstraction boundary:

    open(resource_string, timeout_ms)
    write(command)
    query(command)
    close()

No raw PyVISA object, simulator-specific method, or transport-specific detail
may cross this boundary.
"""

from abc import ABC, abstractmethod
from typing import Optional


class InstrumentEndpointError(Exception):
    """
    Common error raised by every instrument endpoint adapter.

    Adapter-specific exceptions must be translated into this error type before
    they leave an endpoint. ACB should catch only InstrumentEndpointError.

    Attributes:
        message: Safe, human-readable description of the failure.
        endpoint_type: Optional adapter category, e.g. "simulator" or "visa".
        resource_string: Optional transport identifier. It may contain sensitive
            host information and must be redacted before client-facing display.
        cause: Optional original exception retained for internal debugging only.
            It must never be exposed to an instrument client.
    """

    def __init__(
        self,
        message: str,
        endpoint_type: Optional[str] = None,
        resource_string: Optional[str] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        self.message = message
        self.endpoint_type = endpoint_type
        self.resource_string = resource_string
        self.cause = cause

        # Exception.__init__ receives only the safe message. The original cause
        # is preserved separately on self.cause for internal logging.
        super().__init__(message)


class InstrumentEndpoint(ABC):
    """
    Abstract base class for all AutoCalBridge instrument endpoints.

    This is the only endpoint shape ACB may rely on. Concrete adapters must
    implement all four abstract methods and may not expose extra methods that
    ACB then depends on outside this contract.

    Context-manager usage is supported so callers can guarantee close() even if
    an operation raises:

        with endpoint as ep:
            ep.open(resource_string)
            ep.write(command)
            response = ep.query(query)
    """

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "InstrumentEndpoint":
        """
        Enter the runtime context.

        Returns:
            self: The endpoint instance is returned directly.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        Exit the runtime context and close the endpoint.

        Closing is attempted whether or not an exception occurred inside the
        context. The endpoint is responsible for safely handling close errors.

        Returns:
            False: Do not suppress exceptions raised inside the context.
        """
        self.close()
        return False

    # ------------------------------------------------------------------
    # Endpoint contract
    # ------------------------------------------------------------------

    @abstractmethod
    def open(self, resource_string: str, timeout_ms: int = 5000) -> None:
        """
        Open or initialise the endpoint.

        Args:
            resource_string: Transport or simulator resource identifier.
                For a VISA endpoint this is a VISA address string.
                For a simulator endpoint this may be a profile-based logical URI.
            timeout_ms: Operation timeout in milliseconds.

        Raises:
            InstrumentEndpointError: If the endpoint cannot be opened or the
                resource string is invalid.
        """
        raise NotImplementedError

    @abstractmethod
    def write(self, command: str) -> None:
        """
        Send a setting or event command to the endpoint.

        Args:
            command: One SCPI or vendor command string.

        Raises:
            InstrumentEndpointError: If the command is invalid, rejected by the
                security policy, or the transport fails.
        """
        raise NotImplementedError

    @abstractmethod
    def query(self, command: str) -> str:
        """
        Send a query command and return the endpoint response.

        Args:
            command: One query string, e.g. "*IDN?".

        Returns:
            str: Raw response string returned by the endpoint. The caller may
                strip terminators or parse the value as required.

        Raises:
            InstrumentEndpointError: If the query fails, the command is invalid,
                or the response cannot be returned safely.
        """
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """
        Release the endpoint and free any associated resources.

        This method must be idempotent. Calling close() more than once must not
        raise a new error.
        """
        raise NotImplementedError