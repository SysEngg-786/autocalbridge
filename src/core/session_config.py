# File: src/core/session_config.py
# Path: /d/Projects/autocalbridge/src/core/session_config.py
# Purpose: Load and normalize AutoCalBridge session configuration files.
#          A session file defines who is operating, which registered
#          instruments are source and DUT, and run-specific metadata.

"""
Session configuration loader.

This module loads one session YAML file, validates it against the active
instrument registry, and returns a normalized SessionConfig object.

The session file is the single input artifact for one calibration run.
It does not contain instrument command behavior or endpoint logic.
"""

import os
from typing import Any, Dict, Optional

import yaml

from src.core.session_validator import validate_session_data, SessionValidationError
from src.utils.instrument_registry import load_registry, InstrumentRegistry

# Default directory containing session configuration files.
SESSIONS_DIR = "config/sessions"


class SessionConfig:
    """
    Normalized view of one calibration session.

    This object carries the original run configuration fields. It is
    immutable after creation to preserve the original input record.
    """

    def __init__(
        self,
        session_id: str,
        operator: str,
        source_id: str,
        dut_id: str,
        label: Optional[str] = None,
        supervisor: Optional[str] = None,
        procedure: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.session_id = session_id
        self.operator = operator
        self.source_id = source_id
        self.dut_id = dut_id
        self.label = label or ""
        self.supervisor = supervisor or ""
        self.procedure = procedure or ""
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dictionary representation for logging and reuse."""
        return {
            "session_id": self.session_id,
            "label": self.label,
            "operator": self.operator,
            "supervisor": self.supervisor,
            "source_id": self.source_id,
            "dut_id": self.dut_id,
            "procedure": self.procedure,
            "metadata": dict(self.metadata),
        }


def load_session(session_file: str, registry: Optional[InstrumentRegistry] = None) -> SessionConfig:
    """
    Load and validate a session configuration file.

    Args:
        session_file: Path to a session YAML file.
        registry: Optional InstrumentRegistry instance. If not supplied,
            the default registry is loaded from config/instruments_registry.yaml.

    Returns:
        SessionConfig: Normalized validated session object.

    Raises:
        FileNotFoundError: If the session file does not exist.
        SessionValidationError: If the session data is invalid.
    """
    if not os.path.isfile(session_file):
        raise FileNotFoundError(f"Session file not found: {session_file}")

    with open(session_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Load registry if not provided. This lets tests pass a controlled
    # registry while normal use loads the deployment registry.
    if registry is None:
        registry = load_registry()

    # Validate before normalization. If invalid, do not return a partial
    # session object.
    validate_session_data(data, registry)

    return SessionConfig(
        session_id=data.get("session_id", ""),
        operator=data.get("operator", ""),
        source_id=data.get("source_id", ""),
        dut_id=data.get("dut_id", ""),
        label=data.get("label"),
        supervisor=data.get("supervisor"),
        procedure=data.get("procedure"),
        metadata=data.get("metadata"),
    )