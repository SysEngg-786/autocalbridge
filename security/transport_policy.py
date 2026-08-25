# File: security/transport_policy.py
# Path: /d/Projects/autocalbridge/security/transport_policy.py
# Purpose: External-data-driven transport bind policy for AutoCalBridge.

"""
Transport policy.

This module enforces transport/bind rules without hardcoding operational
values. Allowed hosts, denied hosts, default host, and port range limits are
supplied through configuration.

The policy follows the security spine rule:

- development/test services must not silently expose themselves beyond the
  configured host
- remote binding must be explicit through policy configuration
- fail closed when required policy data is missing

This module contains policy logic only. It must not contain operational IP
addresses, hostnames, or port numbers.
"""

from typing import Iterable, Optional, Tuple

from .validators import SecurityValidationError


class TransportPolicy:
    """
    Validates transport bind hosts and ports against external policy data.

    The policy does not assume any host or port value. It must be supplied with
    allowed/denied host data and port limits. If the required data is missing,
    validation fails closed.

    Host matching is exact after normalisation. No network resolution or
    wildcard handling is performed.
    """

    def __init__(
        self,
        allowed_bind_hosts: Optional[Iterable[str]] = None,
        denied_bind_hosts: Optional[Iterable[str]] = None,
        default_bind_host: Optional[str] = None,
        min_port: Optional[int] = None,
        max_port: Optional[int] = None,
    ) -> None:
        """
        Initialise transport policy from external data.

        Args:
            allowed_bind_hosts: Optional set/list of permitted bind hosts.
            denied_bind_hosts: Optional set/list of prohibited bind hosts.
            default_bind_host: Optional default host used when no host is given.
            min_port: Optional lowest permitted port number.
            max_port: Optional highest permitted port number.
        """
        self._allowed_bind_hosts = self._normalize_host_set(allowed_bind_hosts)
        self._denied_bind_hosts = self._normalize_host_set(denied_bind_hosts)
        self._default_bind_host = (
            self._normalize_host(default_bind_host)
            if default_bind_host is not None
            else None
        )
        self._min_port = min_port
        self._max_port = max_port

    # ------------------------------------------------------------------
    # Public validation API
    # ------------------------------------------------------------------

    def resolve_bind_host(self, host: Optional[str] = None) -> str:
        """
        Resolve and validate a bind host.

        If host is None or empty, the configured default host is used. If no
        default is configured, validation fails closed.

        Args:
            host: Candidate bind host string.

        Returns:
            str: Normalised bind host.

        Raises:
            SecurityValidationError: If the host is invalid or not allowed.
        """
        if host is None or not str(host).strip():
            if self._default_bind_host is None:
                raise SecurityValidationError(
                    "No bind host supplied and no default host configured"
                )
            host = self._default_bind_host

        return self.validate_host(host)

    def validate_host(self, host: str) -> str:
        """
        Validate a supplied bind host against the policy data.

        The host is accepted only if:

        - it is a non-empty printable string
        - it is inside the allowed set, when an allowed set is supplied
        - it is not inside the denied set, when a denied set is supplied

        If no allowed or denied set is configured, the policy fails closed.

        Args:
            host: Candidate bind host.

        Returns:
            str: Normalised bind host.

        Raises:
            SecurityValidationError: If the host is invalid or policy rejects it.
        """
        normalized = self._normalize_host(host)

        if not normalized:
            raise SecurityValidationError("Bind host is empty")

        if len(normalized) > 253:
            raise SecurityValidationError("Bind host exceeds maximum length")

        # Ensure no control characters or spaces are present.
        for char in normalized:
            if ord(char) < 0x20 or ord(char) > 0x7E:
                raise SecurityValidationError(
                    "Bind host contains non-printable characters"
                )

        # Fail closed if no policy sets were supplied.
        if not self._allowed_bind_hosts and not self._denied_bind_hosts:
            raise SecurityValidationError(
                "Transport policy has no allowed or denied host data"
            )

        if self._allowed_bind_hosts and normalized not in self._allowed_bind_hosts:
            raise SecurityValidationError(
                f"Bind host is not allowed: {normalized}"
            )

        if self._denied_bind_hosts and normalized in self._denied_bind_hosts:
            raise SecurityValidationError(
                f"Bind host is explicitly denied: {normalized}"
            )

        return normalized

    def validate_port(self, port: int) -> int:
        """
        Validate a transport port number against policy limits.

        Args:
            port: Candidate port number.

        Returns:
            int: Validated port number.

        Raises:
            SecurityValidationError: If the port is invalid or outside policy
                range.
        """
        if isinstance(port, bool):
            raise SecurityValidationError("Port must be an integer")

        try:
            value = int(port)
        except (TypeError, ValueError):
            raise SecurityValidationError("Port must be an integer")

        if self._min_port is None or self._max_port is None:
            raise SecurityValidationError(
                "Transport policy has no port range configured"
            )

        if value < int(self._min_port) or value > int(self._max_port):
            raise SecurityValidationError(
                f"Port is outside configured range: {value}"
            )

        return value

    def validate_bind_address(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ) -> Tuple[str, int]:
        """
        Validate a bind host and port together.

        Args:
            host: Optional bind host. If omitted, the configured default is used.
            port: Bind port.

        Returns:
            Tuple of (normalised_host, validated_port).

        Raises:
            SecurityValidationError: If either value is invalid.
        """
        resolved_host = self.resolve_bind_host(host)
        resolved_port = self.validate_port(port)
        return resolved_host, resolved_port

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_host(host: Optional[str]) -> Optional[str]:
        """
        Normalise one host string.

        Hostnames are case-insensitive, so the value is lowercased after
        stripping whitespace.

        Args:
            host: Host string, or None.

        Returns:
            str or None: Normalised host, or None when input is None.
        """
        if host is None:
            return None

        if not isinstance(host, str):
            return None

        return host.strip().lower()

    @classmethod
    def _normalize_host_set(
        cls,
        hosts: Optional[Iterable[str]],
    ) -> set:
        """
        Normalise a collection of host strings into a set.

        Args:
            hosts: Iterable of host strings, or None.

        Returns:
            set: Normalised host strings. Empty when input is None.
        """
        if hosts is None:
            return set()

        return {
            normalized
            for host in hosts
            if (normalized := cls._normalize_host(host)) is not None
        }