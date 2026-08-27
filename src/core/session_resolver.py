# File: src/core/session_resolver.py
# Path: /d/Projects/autocalbridge/src/core/session_resolver.py
# Purpose: Resolve a normalized session configuration to registry entries.
#          Keeps session loading separate from instrument lookup.

"""
Session resolver.

This module takes a SessionConfig and resolves its source_id and dut_id
to InstrumentRegistryEntry objects from the active instrument registry.

The result is a ResolvedSession containing source_entry and dut_entry.
Later phases can pass this resolved session to the procedure runner or
TestEngine so endpoints can be opened without repeating lookup logic.
"""

from dataclasses import dataclass
from typing import Optional

from src.core.session_config import SessionConfig
from src.utils.instrument_registry import load_registry, InstrumentRegistry, InstrumentRegistryEntry


class SessionResolutionError(Exception):
    """Raised when a session references an instrument that cannot be resolved."""

    def __init__(self, message):
        super().__init__(message)


@dataclass(frozen=True)
class ResolvedSession:
    """
    Result of resolving a session against the instrument registry.

    Attributes:
        config: Original normalized session configuration.
        source_entry: Registry entry for the source instrument.
        dut_entry: Registry entry for the DUT instrument.
    """

    config: SessionConfig
    source_entry: InstrumentRegistryEntry
    dut_entry: InstrumentRegistryEntry


def resolve_session(
    session_config: SessionConfig,
    registry: Optional[InstrumentRegistry] = None,
) -> ResolvedSession:
    """
    Resolve a session's source and DUT IDs to registry entries.

    Args:
        session_config: Normalized SessionConfig object.
        registry: Optional InstrumentRegistry instance. If not supplied,
            the default deployment registry is loaded.

    Returns:
        ResolvedSession: Session with resolved source and DUT entries.

    Raises:
        SessionResolutionError: If either instrument ID cannot be resolved.
    """
    if registry is None:
        registry = load_registry()

    source_entry = registry.get(session_config.source_id)
    if source_entry is None:
        raise SessionResolutionError(
            f"source_id '{session_config.source_id}' not found in instrument registry."
        )

    dut_entry = registry.get(session_config.dut_id)
    if dut_entry is None:
        raise SessionResolutionError(
            f"dut_id '{session_config.dut_id}' not found in instrument registry."
        )

    return ResolvedSession(
        config=session_config,
        source_entry=source_entry,
        dut_entry=dut_entry,
    )