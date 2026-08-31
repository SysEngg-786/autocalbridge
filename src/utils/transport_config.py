# File: src/utils/transport_config.py
# Path: /d/Projects/autocalbridge/src/utils/transport_config.py
# Purpose: Load and normalize transport templates from config/transports/.
#          These templates provide low-level connection parameters for
#          physical instrument endpoints, selected by registry entries.

"""
Transport configuration loader.

Each transport type has one YAML template under config/transports/.

Example:
    config/transports/usbtmc.yaml
    config/transports/tcpip.yaml

A transport template may define:
    timeout_ms
    write_termination
    read_termination
    post_write_delay_ms

These values are applied by PyVisaEndpoint when opening a physical resource.
They are not SCPI commands and are never exposed to normal operators.
"""

import os
from dataclasses import dataclass
from typing import Optional

import yaml


# Default directory containing transport template files.
TRANSPORTS_DIR = "config/transports"


class TransportConfigError(Exception):
    """Raised when a transport template cannot be loaded or is invalid."""

    def __init__(self, message: str):
        super().__init__(message)


@dataclass(frozen=True)
class TransportConfig:
    """
    Normalized transport template values.

    Attributes:
        transport_name: Name of the transport, e.g. "usbtmc" or "tcpip".
        timeout_ms: Communication timeout in milliseconds.
        write_termination: Termination appended to write operations.
        read_termination: Termination used to detect end of read response.
        post_write_delay_ms: Delay after write before read, in milliseconds.
    """

    transport_name: str
    timeout_ms: int = 5000
    write_termination: str = "\n"
    read_termination: str = "\n"
    post_write_delay_ms: int = 0

    def to_dict(self):
        """Return a plain dictionary representation for logging/debugging."""
        return {
            "transport_name": self.transport_name,
            "timeout_ms": self.timeout_ms,
            "write_termination": self.write_termination,
            "read_termination": self.read_termination,
            "post_write_delay_ms": self.post_write_delay_ms,
        }


def load_transport_config(transport_name: str) -> TransportConfig:
    """
    Load and validate a transport template by name.

    Args:
        transport_name: Transport identifier, e.g. "usbtmc" or "tcpip".

    Returns:
        TransportConfig: Normalized transport settings.

    Raises:
        TransportConfigError: If template file is missing or invalid.
    """
    if not transport_name or not transport_name.strip():
        raise TransportConfigError("Transport name is empty.")

    # Prevent path traversal by using only basename.
    safe_name = os.path.basename(transport_name.strip())
    template_path = os.path.join(TRANSPORTS_DIR, f"{safe_name}.yaml")

    if not os.path.isfile(template_path):
        raise TransportConfigError(
            f"Transport template not found: {template_path}"
        )

    with open(template_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise TransportConfigError(
            f"Transport template must be a mapping: {template_path}"
        )

    required = "transport_name"
    if required not in data:
        raise TransportConfigError(
            f"Transport template missing required field '{required}'."
        )

    return TransportConfig(
        transport_name=str(data.get("transport_name", safe_name)),
        timeout_ms=int(data.get("timeout_ms", 5000)),
        write_termination=str(data.get("write_termination", "\n")),
        read_termination=str(data.get("read_termination", "\n")),
        post_write_delay_ms=int(data.get("post_write_delay_ms", 0)),
    )