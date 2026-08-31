# File: src/core/procedure_config.py
# Path: /d/Projects/autocalbridge/src/core/procedure_config.py
# Purpose: Load and normalize AutoCalBridge calibration procedure files.
#          A procedure defines the commands, points, and tolerance for one
#          calibration run, independent of the instruments themselves.
#          Supports absolute and relative tolerance types.

"""
Procedure configuration loader.

This module loads one procedure YAML file, validates its structure, and
returns a normalized ProcedureConfig object.

The procedure file is the single source of truth for what commands and
points are used during a calibration sequence. It must not contain
instrument identity, connection strings, or role assignment. Those belong
to the session and registry layers.
"""

import os
from typing import Any, Dict, List, Optional

import yaml

from src.core.procedure_validator import validate_procedure_data, ProcedureValidationError

# Default directory containing procedure configuration files.
PROCEDURES_DIR = "config/procedures"


class ProcedureConfig:
    """
    Normalized view of one calibration procedure.

    This object carries the command templates, points, tolerance, and
    tolerance type. It is immutable after creation to preserve the original
    procedure definition for traceability.
    """

    def __init__(
        self,
        procedure_id: str,
        source_command_template: str,
        dut_query_command: str,
        points: List[float],
        tolerance: float,
        tolerance_type: str = "absolute",
        label: Optional[str] = None,
        sync: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.procedure_id = procedure_id
        self.source_command_template = source_command_template
        self.dut_query_command = dut_query_command
        self.points = list(points)
        self.tolerance = float(tolerance)
        self.tolerance_type = tolerance_type.strip().lower()
        self.label = label or ""
        self.sync = sync or {}
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dictionary representation for logging and reuse."""
        return {
            "procedure_id": self.procedure_id,
            "label": self.label,
            "source_command_template": self.source_command_template,
            "dut_query_command": self.dut_query_command,
            "points": list(self.points),
            "tolerance": self.tolerance,
            "tolerance_type": self.tolerance_type,
            "sync": dict(self.sync),
            "metadata": dict(self.metadata),
        }


def load_procedure(procedure_file: str) -> ProcedureConfig:
    """
    Load and validate a procedure configuration file.

    Args:
        procedure_file: Path to a procedure YAML file.

    Returns:
        ProcedureConfig: Normalized validated procedure object.

    Raises:
        FileNotFoundError: If the procedure file does not exist.
        ProcedureValidationError: If the procedure data is invalid.
    """
    if not os.path.isfile(procedure_file):
        raise FileNotFoundError(f"Procedure file not found: {procedure_file}")

    with open(procedure_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Validate before normalization. If invalid, do not return a partial
    # procedure object.
    validate_procedure_data(data)

    tolerance_type = data.get("tolerance_type", "absolute")
    if not isinstance(tolerance_type, str):
        tolerance_type = "absolute"
    tolerance_type = tolerance_type.strip().lower()

    return ProcedureConfig(
        procedure_id=data.get("procedure_id", ""),
        source_command_template=data.get("source_command_template", ""),
        dut_query_command=data.get("dut_query_command", ""),
        points=data.get("points", []),
        tolerance=data.get("tolerance", 0.0),
        tolerance_type=tolerance_type,
        label=data.get("label"),
        sync=data.get("sync"),
        metadata=data.get("metadata"),
    )