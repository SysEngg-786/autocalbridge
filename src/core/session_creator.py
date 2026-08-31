# File: src/core/session_creator.py
# Path: /d/Projects/autocalbridge/src/core/session_creator.py
# Purpose: Create session configuration files automatically from operator
#          selections. This is the product-facing replacement for manual
#          YAML session file creation. Uses registry and procedure IDs as
#          inputs and writes one run-configuration file per session.

"""
Session creator.

This module creates a session YAML file from validated operator inputs.

Inputs:
- operator
- supervisor (optional)
- source_id
- dut_id
- procedure
- label (optional)
- metadata (optional)

Outputs:
- A unique session_id
- A file at config/sessions/<session_id>.yaml

The session file is the single input artifact for one calibration run.
It does not contain SCPI commands, connection strings, or profile internals.
"""

import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import yaml

from src.utils.instrument_registry import load_registry

# Directories used for session and procedure files.
SESSIONS_DIR = "config/sessions"
PROCEDURES_DIR = "config/procedures"


class SessionCreationError(Exception):
    """Raised when session creation inputs are invalid."""

    def __init__(self, message: str):
        super().__init__(message)


def _validate_inputs(
    operator: str,
    source_id: str,
    dut_id: str,
    procedure: str,
    metadata: Optional[Dict[str, Any]],
    supervisor: Optional[str],
    label: Optional[str],
) -> None:
    """
    Validate session creation inputs.

    Raises:
        SessionCreationError: If any required input is missing or invalid.
    """
    # Required string fields must be non-empty.
    required = {
        "operator": operator,
        "source_id": source_id,
        "dut_id": dut_id,
        "procedure": procedure,
    }
    for field, value in required.items():
        if not isinstance(value, str) or not value.strip():
            raise SessionCreationError(
                f"Missing or empty required field '{field}'."
            )

    # Source and DUT must be different.
    if source_id.strip() == dut_id.strip():
        raise SessionCreationError("source_id and dut_id must be different.")

    # Optional string fields must be strings if present.
    for field, value in {
        "supervisor": supervisor,
        "label": label,
    }.items():
        if value is not None and not isinstance(value, str):
            raise SessionCreationError(f"Field '{field}' must be a string.")

    # metadata must be a mapping if present.
    if metadata is not None and not isinstance(metadata, dict):
        raise SessionCreationError("Field 'metadata' must be a mapping.")


def _validate_references(
    source_id: str,
    dut_id: str,
    procedure: str,
) -> None:
    """
    Validate that instrument and procedure references exist.

    Raises:
        SessionCreationError: If any reference is missing.
    """
    # Instrument registry must contain both IDs.
    try:
        registry = load_registry()
    except Exception as exc:
        raise SessionCreationError(f"Failed to load instrument registry: {exc}") from exc

    if registry.get(source_id.strip()) is None:
        raise SessionCreationError(
            f"source_id '{source_id}' is not a registered instrument."
        )

    if registry.get(dut_id.strip()) is None:
        raise SessionCreationError(
            f"dut_id '{dut_id}' is not a registered instrument."
        )

    # Procedure file must exist.
    procedure_file = os.path.join(PROCEDURES_DIR, f"{procedure.strip()}.yaml")
    if not os.path.isfile(procedure_file):
        raise SessionCreationError(
            f"procedure '{procedure}' not found under '{PROCEDURES_DIR}'."
        )


def _generate_session_id() -> str:
    """
    Generate a unique session ID.

    Format:
        ACB-YYYYMMDD-HHMMSS-<short unique suffix>

    The suffix comes from a UUID4 and prevents collisions if two sessions
    are created within the same second.
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    short = uuid.uuid4().hex[:4]
    return f"ACB-{timestamp}-{short}"


def create_session(
    operator: str,
    source_id: str,
    dut_id: str,
    procedure: str,
    supervisor: Optional[str] = None,
    label: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> str:
    """
    Create a session configuration file.

    Args:
        operator: Operator name for this run.
        source_id: Registry ID of the source instrument.
        dut_id: Registry ID of the DUT instrument.
        procedure: Procedure ID without .yaml extension.
        supervisor: Optional supervisor name.
        label: Optional human-readable label for the session.
        metadata: Optional mapping of site/purpose/work-order data.
        session_id: Optional explicit session ID. If not supplied, a unique
            session ID is generated automatically.

    Returns:
        str: Full path to the created session file.

    Raises:
        SessionCreationError: If validation fails or file cannot be written.
    """
    # Validate raw inputs.
    _validate_inputs(
        operator=operator,
        source_id=source_id,
        dut_id=dut_id,
        procedure=procedure,
        supervisor=supervisor,
        label=label,
        metadata=metadata,
    )

    # Validate registry and procedure references.
    _validate_references(
        source_id=source_id,
        dut_id=dut_id,
        procedure=procedure,
    )

    # Generate session ID if not provided.
    final_session_id = session_id.strip() if session_id else _generate_session_id()
    if not final_session_id:
        raise SessionCreationError("Session ID cannot be empty.")

    # Build session document in a stable field order.
    session_doc = {
        "session_id": final_session_id,
        "operator": operator.strip(),
        "source_id": source_id.strip(),
        "dut_id": dut_id.strip(),
        "procedure": procedure.strip(),
    }

    if label and label.strip():
        session_doc["label"] = label.strip()
    if supervisor and supervisor.strip():
        session_doc["supervisor"] = supervisor.strip()
    if metadata:
        session_doc["metadata"] = dict(metadata)

    # Ensure the sessions directory exists.
    os.makedirs(SESSIONS_DIR, exist_ok=True)

    session_file = os.path.join(SESSIONS_DIR, f"{final_session_id}.yaml")

    # Write the session file.
    try:
        with open(session_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(session_doc, f, sort_keys=False, default_flow_style=False)
    except OSError as exc:
        raise SessionCreationError(
            f"Failed to write session file '{session_file}': {exc}"
        ) from exc

    return session_file