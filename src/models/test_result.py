# File: src/models/test_result.py
# Path: /d/Projects/autocalbridge/src/models/test_result.py
# Purpose: Canonical data model for a single calibration test result.
#          Used by TestEngine, session runner, and report generator so
#          results have one stable traceable schema across the system.

"""
Canonical test result model.

This model is the single result representation for AutoCalBridge.
It contains all traceability fields required for calibration records:

- session_id
- operator
- supervisor
- procedure_id
- source_id
- dut_id
- target
- measured
- error
- tolerance
- status
- timestamp
- metadata

No connection strings, endpoint internals, or transport details are stored.
Instrument IDs are registry identifiers only, not VISA resource strings.
"""

from datetime import datetime
from typing import Any, Dict, Optional


class TestResult:
    """
    Immutable calibration test result.

    All fields are plain safe types: str, float, int, dict, list, None.
    The object is frozen after creation to preserve the original record.
    """

    def __init__(
        self,
        target_value: float,
        measured_value: float,
        tolerance: float,
        operator: str = "Default",
        session_id: str = "",
        supervisor: Optional[str] = None,
        procedure_id: str = "",
        source_id: str = "",
        dut_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> None:
        """
        Initialise a canonical test result.

        Args:
            target_value: Expected or stimulus value.
            measured_value: Actual measured value.
            tolerance: PASS/FAIL tolerance.
            operator: Operator identifier.
            session_id: Session identifier from session config.
            supervisor: Optional supervisor identifier.
            procedure_id: Procedure identifier.
            source_id: Registry ID of source instrument.
            dut_id: Registry ID of DUT instrument.
            metadata: Optional free-form metadata mapping.
            timestamp: Optional explicit timestamp. If not supplied,
                current UTC time in "%Y-%m-%d %H:%M:%S" format is used.
        """
        self.target_value = float(target_value)
        self.measured_value = float(measured_value)
        self.tolerance = float(tolerance)
        self.operator = operator
        self.session_id = session_id
        self.supervisor = supervisor or ""
        self.procedure_id = procedure_id
        self.source_id = source_id
        self.dut_id = dut_id
        self.metadata = metadata or {}

        # Calculate error and status deterministically.
        self.error = abs(self.measured_value - self.target_value)
        self.status = "PASS" if self.error <= self.tolerance else "FAIL"

        if timestamp is None:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        """
        Return a stable dictionary representation for CSV and logging.

        Returns:
            dict: Canonical result fields with consistent keys.
        """
        return {
            "Timestamp": self.timestamp,
            "SessionID": self.session_id,
            "Operator": self.operator,
            "Supervisor": self.supervisor,
            "Procedure": self.procedure_id,
            "SourceID": self.source_id,
            "DUTID": self.dut_id,
            "Target": self.target_value,
            "Measured": self.measured_value,
            "Error": round(self.error, 4),
            "Tolerance": self.tolerance,
            "Status": self.status,
            "Metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return (
            f"TestResult(session={self.session_id or '-'}, "
            f"procedure={self.procedure_id or '-'}, "
            f"target={self.target_value}, measured={self.measured_value}, "
            f"status={self.status})"
        )