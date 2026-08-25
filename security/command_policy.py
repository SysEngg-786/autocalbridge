# File: security/command_policy.py
# Path: /d/Projects/autocalbridge/security/command_policy.py
# Purpose: Allowlist-based SCPI command policy for AutoCalBridge endpoints.

"""
Command policy for instrument endpoints.

This module provides a small, reusable command policy that validates SCPI
commands before they are sent to a simulator or physical instrument.

Policy approach:
- allowlist-based
- commands are normalised before comparison
- query commands are matched exactly
- write commands may be matched by an allowed root or root plus space
- malformed or overly long commands are rejected
- rejected commands return a controlled message, never a raw exception

The allowed command sets are supplied by the caller, usually from a device
profile or a dedicated policy data source. This module contains policy logic
only, not command data.
"""

from typing import Optional, Tuple


class CommandPolicy:
    """
    Allowlist-based SCPI command validator.

    The allowed command sets are passed in at construction time. This keeps the
    policy reusable across many instrument types and profiles.

    Query commands are compared exactly after normalisation.

    Write commands may appear with parameters, for example:

        SOUR:VOLT 5.0

    For that reason, write matching supports two forms:

        1. Exact root command, e.g. SOUR:VOLT
        2. Root command followed by a space and parameters, e.g. SOUR:VOLT 5.0

    A write root of SOUR:VOLT will not match SOUR:VOLTAGE.
    """

    # Maximum acceptable normalised command length.
    # This is deliberately small for instrument control commands.
    MAX_COMMAND_LENGTH = 1024

    def __init__(
        self,
        allowed_queries: Optional[set] = None,
        allowed_writes: Optional[set] = None,
    ) -> None:
        """
        Initialise the command policy.

        Args:
            allowed_queries: Set of allowed exact query commands,
                e.g. {"*IDN?", "READ?"}.
            allowed_writes: Set of allowed write roots,
                e.g. {"*RST", "SOUR:VOLT", "*CLS"}.
        """
        self._allowed_queries = {
            self.normalize(command) for command in (allowed_queries or set())
        }
        self._allowed_writes = {
            self.normalize(command) for command in (allowed_writes or set())
        }

    @staticmethod
    def normalize(command: str) -> str:
        """
        Normalise one incoming SCPI command.

        Normalisation removes surrounding whitespace, strips non-printable
        control characters, and converts the command to uppercase.

        Args:
            command: Raw command string received from a VISA client.

        Returns:
            str: Normalised command string. May be empty if the command was
                empty or contained only control characters.
        """
        if not isinstance(command, str):
            return ""

        # Keep only printable ASCII characters. This blocks control characters
        # that may be used for command injection or malformed messages.
        cleaned = "".join(
            char for char in command
            if 0x20 <= ord(char) <= 0x7E
        )

        return cleaned.strip().upper()

    def validate(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        Validate one command against the configured allowlists.

        Args:
            command: Raw command string.

        Returns:
            Tuple of (is_valid, error_message).
            If is_valid is True, error_message is None.
            If is_valid is False, error_message contains a controlled reason.
        """
        normalized = self.normalize(command)

        if not normalized:
            return False, "Empty or malformed command"

        if len(normalized) > self.MAX_COMMAND_LENGTH:
            return False, "Command exceeds maximum length"

        # Query commands end with "?" and must be present in the query allowlist.
        if normalized.endswith("?"):
            if normalized not in self._allowed_queries:
                return False, f"Query not allowed: {normalized}"
            return True, None

        # Non-query commands use the parameterised write matching rules.
        if not self._is_allowed_write(normalized):
            return False, f"Command not allowed: {normalized}"

        return True, None

    def _is_allowed_write(self, normalized: str) -> bool:
        """
        Check whether a normalised write command matches an allowed write root.

        Matching rules:
            1. Exact match against the allowed root.
            2. Root followed by one space and optional parameters.

        Args:
            normalized: Normalised command string.

        Returns:
            bool: True if the write command is allowed.
        """
        if normalized in self._allowed_writes:
            return True

        # Root plus space prevents prefix collisions such as SOUR:VOLTAGE
        # when the allowed root is SOUR:VOLT.
        for allowed_root in self._allowed_writes:
            if normalized.startswith(allowed_root + " "):
                return True

        return False