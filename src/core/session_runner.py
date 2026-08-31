# File: src/core/session_runner.py
# Path: /d/Projects/autocalbridge/src/core/session_runner.py
# Purpose: Thin session runner that executes a calibration run from a session
#          file, resolving instruments from the registry and procedure from
#          the session's procedure reference.
#          Supplies command policies, safety limits, and transport configs to
#          the TestEngine so physical endpoints receive the same protection
#          and connection behavior as required.
#          Activates a SessionContext so all structured logs during the run
#          automatically carry session traceability fields.

"""
Session runner.

This module bridges session configuration, procedure configuration, and the
existing TestEngine.

It does not replace TestEngine yet. It:

1. Loads a session configuration file.
2. Resolves source and DUT IDs to registry entries.
3. Resolves the procedure ID to a procedure file.
4. Builds command policies from instrument profiles.
5. Merges profile and registry safety limits for the source.
6. Loads transport configs for physical entries.
7. Creates a SessionContext from the session config and activates it around
   the actual run, so endpoint and engine logs include session fields.
8. Creates a TestEngine.
9. Connects source and DUT using resolved connection strings, policies, and
   transport configs.
10. Sets source safety limits on the TestEngine.
11. Runs the procedure with session traceability fields.
12. Closes all endpoints.
13. Returns results and errors for reporting.

The long-term target is to make TestEngine a thin procedure runner. That
refactor belongs to later phases. This module currently owns the security
and safety preparation that will eventually move to a dedicated endpoint
security context.
"""

import os
from typing import List, Tuple, Any, Dict

import yaml

from src.core.session_config import load_session, SessionConfig
from src.core.session_resolver import resolve_session
from src.core.procedure_config import load_procedure, ProcedureConfig
from src.core.test_engine import TestEngine
from security.policy_loader import build_policy_from_source
from src.core.session_context import SessionContext, session_context
from src.utils.transport_config import load_transport_config, TransportConfigError

# Default directory containing procedure configuration files.
PROCEDURES_DIR = "config/procedures"

# Default directory containing instrument capability profiles.
INSTRUMENTS_DIR = "config/instruments"


class SessionRunnerError(Exception):
    """Raised when a session runner step fails before or during execution."""

    def __init__(self, message: str):
        super().__init__(message)


def _resolve_procedure_file(procedure_id: str) -> str:
    """
    Resolve a procedure ID to its file path.

    Args:
        procedure_id: Procedure identifier, e.g. "keysight_source_to_34461a".

    Returns:
        str: Path to procedure YAML file.

    Raises:
        SessionRunnerError: If procedure_id is empty.
    """
    if not procedure_id or not procedure_id.strip():
        raise SessionRunnerError("Session procedure reference is empty.")

    return os.path.join(PROCEDURES_DIR, f"{procedure_id}.yaml")


def _build_policy_for_entry(entry):
    """
    Build a CommandPolicy from an instrument registry entry's profile.

    Args:
        entry: InstrumentRegistryEntry instance.

    Returns:
        CommandPolicy or None if profile cannot be loaded.
    """
    profile_path = os.path.join(INSTRUMENTS_DIR, entry.profile)

    if not os.path.isfile(profile_path):
        return None

    return build_policy_from_source(profile_path)


def _load_transport_for_entry(entry):
    """
    Load a TransportConfig for a physical registry entry.

    Args:
        entry: InstrumentRegistryEntry instance.

    Returns:
        TransportConfig or None if entry has no transport or is virtual.
    """
    transport_name = getattr(entry, "transport", None)
    if not transport_name:
        return None

    try:
        return load_transport_config(transport_name)
    except TransportConfigError as exc:
        raise SessionRunnerError(
            f"Failed to load transport config '{transport_name}': {exc}"
        ) from exc


def _load_profile_safety_limits(entry) -> Dict[str, Dict[str, float]]:
    """
    Read safety_limits from an instrument capability profile.

    Args:
        entry: InstrumentRegistryEntry instance.

    Returns:
        dict: Command root -> {"min": float, "max": float}.
    """
    profile_path = os.path.join(INSTRUMENTS_DIR, entry.profile)

    if not os.path.isfile(profile_path):
        return {}

    with open(profile_path, "r", encoding="utf-8") as f:
        profile_data = yaml.safe_load(f) or {}

    limits = profile_data.get("safety_limits", {})
    if not isinstance(limits, dict):
        return {}
    return limits


def _merge_safety_limits(
    profile_limits: Dict[str, Dict[str, float]],
    registry_limits: Dict[str, Dict[str, float]],
) -> Dict[str, Dict[str, float]]:
    """
    Merge profile and registry safety limits.

    Profile limits are the default envelope. Registry limits may narrow that
    envelope, not widen it.

    If a command root exists only in registry, it is accepted as-is because
    there is no profile default to conflict with.

    Args:
        profile_limits: Type-level safety limits.
        registry_limits: Deployment-specific safety limits.

    Returns:
        dict: Merged command root -> {"min": float, "max": float}.

    Raises:
        SessionRunnerError: If registry limits attempt to widen profile limits.
    """
    merged = dict(profile_limits)

    for root, reg_limits in registry_limits.items():
        if not isinstance(reg_limits, dict):
            raise SessionRunnerError(
                f"Invalid registry safety limit for command root '{root}'."
            )

        if root not in merged:
            merged[root] = dict(reg_limits)
            continue

        prof = merged[root]

        prof_min = prof.get("min")
        prof_max = prof.get("max")
        reg_min = reg_limits.get("min")
        reg_max = reg_limits.get("max")

        if prof_min is not None and reg_min is not None and reg_min < prof_min:
            raise SessionRunnerError(
                f"Registry safety limit for {root} min={reg_min} is wider than "
                f"profile min={prof_min}."
            )
        if prof_max is not None and reg_max is not None and reg_max > prof_max:
            raise SessionRunnerError(
                f"Registry safety limit for {root} max={reg_max} is wider than "
                f"profile max={prof_max}."
            )

        merged[root] = {
            "min": reg_min if reg_min is not None else prof_min,
            "max": reg_max if reg_max is not None else prof_max,
        }

    return merged


def run_session(session_file: str):
    """
    Run a calibration session from a session file.

    The session file must contain:
    - operator
    - source_id
    - dut_id
    - procedure (procedure ID without .yaml)

    Command policies, safety limits, and transport configs are loaded and
    supplied to the TestEngine. SessionContext is activated for the duration
    of the run so logs carry traceability fields.

    Args:
        session_file: Path to a valid session YAML file.

    Returns:
        Tuple of (results, errors).
    """
    try:
        session_config: SessionConfig = load_session(session_file)
    except Exception as exc:
        raise SessionRunnerError(f"Failed to load session file: {exc}") from exc

    try:
        resolved = resolve_session(session_config)
    except Exception as exc:
        raise SessionRunnerError(f"Failed to resolve session instruments: {exc}") from exc

    try:
        procedure_file = _resolve_procedure_file(session_config.procedure)
        procedure: ProcedureConfig = load_procedure(procedure_file)
    except Exception as exc:
        raise SessionRunnerError(f"Failed to load procedure: {exc}") from exc

    source_policy = _build_policy_for_entry(resolved.source_entry)
    dut_policy = _build_policy_for_entry(resolved.dut_entry)

    source_profile_limits = _load_profile_safety_limits(resolved.source_entry)
    source_registry_limits = resolved.source_entry.safety_limits or {}
    source_safety_limits = _merge_safety_limits(
        source_profile_limits,
        source_registry_limits,
    )

    source_transport = _load_transport_for_entry(resolved.source_entry)
    dut_transport = _load_transport_for_entry(resolved.dut_entry)

    session_ctx = SessionContext(
        session_id=session_config.session_id,
        operator=session_config.operator,
        supervisor=session_config.supervisor,
        instrument_roles={
            "source": resolved.source_entry.id,
            "dut": resolved.dut_entry.id,
        },
    )

    engine = TestEngine()
    engine.set_source_safety_limits(source_safety_limits)

    try:
        with session_context(session_ctx):
            source_connected = engine.connect_source(
                resolved.source_entry.connection,
                command_policy=source_policy,
                transport_config=source_transport,
            )
            if not source_connected:
                raise SessionRunnerError(
                    f"Failed to connect source instrument: {resolved.source_entry.id}"
                )

            dut_connected = engine.connect_dut(
                resolved.dut_entry.connection,
                command_policy=dut_policy,
                transport_config=dut_transport,
            )
            if not dut_connected:
                raise SessionRunnerError(
                    f"Failed to connect DUT instrument: {resolved.dut_entry.id}"
                )

            results = engine.run_procedure(
                procedure=procedure,
                operator_name=session_config.operator,
                session_id=session_config.session_id,
                supervisor=session_config.supervisor,
                source_id=resolved.source_entry.id,
                dut_id=resolved.dut_entry.id,
            )

            errors = engine.get_errors()
            return results, errors

    except Exception as exc:
        raise SessionRunnerError(f"Session run failed: {exc}") from exc

    finally:
        engine.close()