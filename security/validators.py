# File: security/validators.py
# Path: /d/Projects/autocalbridge/security/validators.py
# Purpose: Input validation primitives for AutoCalBridge security spine.

"""
Security validators.

This module contains small, reusable validation functions used at instrument
endpoint and configuration boundaries.

Validators raise SecurityValidationError with a controlled message when input
is rejected. They must never leak internal paths, stack traces, or sensitive
values.

The module is intentionally independent of ACB, simulator, and endpoint
implementation details.
"""

from typing import Any, Optional


class SecurityValidationError(Exception):
    """
    Raised when a security validator rejects input.

    This is a controlled error type. Callers may catch it and translate it into
    their own boundary error type, such as InstrumentEndpointError.
    """

    pass


def validate_resource_string(resource_string: str) -> str:
    """
    Validate an instrument resource string.

    Resource strings may be:

    - simulator logical URI, e.g. sim://keysight_34461a
    - physical VISA resource string, e.g. TCPIP0::192.168.1.50::inst0::INSTR

    Validation does not interpret the VISA address; it only checks that the
    string is non-empty, printable, and within a safe length.

    Args:
        resource_string: Candidate resource string.

    Returns:
        str: Stripped resource string.

    Raises:
        SecurityValidationError: If the resource string is invalid.
    """
    if not isinstance(resource_string, str):
        raise SecurityValidationError("Resource string must be a string")

    stripped = resource_string.strip()

    if not stripped:
        raise SecurityValidationError("Resource string is empty")

    if len(stripped) > 2048:
        raise SecurityValidationError("Resource string exceeds maximum length")

    # Reject non-printable/control characters. Resource strings should contain
    # only printable ASCII or normal hostname/address characters.
    for char in stripped:
        if ord(char) < 0x20 or ord(char) > 0x7E:
            raise SecurityValidationError(
                "Resource string contains non-printable characters"
            )

    # Simulator scheme is the only implicit scheme handled by the factory.
    if stripped.startswith("sim://"):
        profile_name = stripped[len("sim://") :]

        if not profile_name:
            raise SecurityValidationError(
                "Simulator resource string is missing a profile name"
            )

        # Restrict profile names to a conservative safe set.
        for char in profile_name:
            if not (char.isalnum() or char in {"_", "-"}):
                raise SecurityValidationError(
                    "Simulator profile name contains invalid characters"
                )

    return stripped


def validate_timeout_ms(timeout_ms: Any) -> int:
    """
    Validate a timeout value in milliseconds.

    Args:
        timeout_ms: Timeout value supplied by configuration or caller.

    Returns:
        int: Validated timeout in milliseconds.

    Raises:
        SecurityValidationError: If the timeout is not a positive integer or is
            too large.
    """
    if isinstance(timeout_ms, bool):
        raise SecurityValidationError("Timeout must be a positive integer")

    try:
        value = int(timeout_ms)
    except (TypeError, ValueError):
        raise SecurityValidationError("Timeout must be a positive integer")

    if value <= 0:
        raise SecurityValidationError("Timeout must be a positive integer")

    # Instrument operations should not need excessive timeouts. This upper
    # bound prevents accidental hangs and is deliberately conservative.
    if value > 600000:
        raise SecurityValidationError("Timeout exceeds maximum allowed value")

    return value


def validate_numeric_range(
    value: Any,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> float:
    """
    Validate a numeric value and optional inclusive range.

    Args:
        value: Numeric value to validate.
        min_value: Optional minimum allowed value.
        max_value: Optional maximum allowed value.

    Returns:
        float: Validated numeric value.

    Raises:
        SecurityValidationError: If the value is not numeric or outside range.
    """
    if isinstance(value, bool):
        raise SecurityValidationError("Value must be numeric")

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        raise SecurityValidationError("Value must be numeric")

    if min_value is not None and numeric_value < float(min_value):
        raise SecurityValidationError(
            f"Value must be >= {min_value}"
        )

    if max_value is not None and numeric_value > float(max_value):
        raise SecurityValidationError(
            f"Value must be <= {max_value}"
        )

    return numeric_value