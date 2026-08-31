# File: src/models/test_result.py
# Path: /d/Projects/autocalbridge/src/models/test_result.py
# Purpose: Canonical data model for a single calibration test result.
#          Used by TestEngine, session runner, and report generator so
#          results have one stable traceable schema across the system.
#          Supports absolute and relative tolerance types.

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
- error_percent
- tolerance
- tolerance_type
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
        tolerance_type: str = "absolute",
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> None:
        """
        Initialise a canonical test result.

        Args:
            target_value: Expected or stimulus value.
            measured_value: Actual measured value.
            tolerance: PASS/FAIL tolerance.
                - Absolute: value in measurement units, e.g. 500 Hz.
                - Relative: percentage, e.g. 2 means 2%.
            operator: Operator identifier.
            session_id: Session identifier from session config.
            supervisor: Optional supervisor identifier.
            procedure_id: Procedure identifier.
            source_id: Registry ID of source instrument.
            dut_id: Registry ID of DUT instrument.
            tolerance_type: "absolute" or "relative".
            metadata: Optional free-form metadata mapping.
            timestamp: Optional explicit timestamp. If not supplied,
                current UTC time in "%Y-%m-%d %H:%M:%S" format is used.
        """
        self.target_value = float(target_value)
        self.measured_value = float(measured_value)
        self.tolerance = float(tolerance)
        self.tolerance_type = tolerance_type.strip().lower()
        self.operator = operator
        self.session_id = session_id
        self.supervisor = supervisor or ""
        self.procedure_id = procedure_id
        self.source_id = source_id
        self.dut_id = dut_id
        self.metadata = metadata or {}

        # Calculate error and status deterministically.
        self.error = abs(self.measured_value - self.target_value)

        # Percentage error. Guard against division by zero for zero target.
        if abs(self.target_value) > 1e-12:
            self.error_percent = (self.error / abs(self.target_value)) * 100.0
        else:
            self.error_percent = 0.0

        # Determine PASS/FAIL based on tolerance type.
        if self.tolerance_type == "relative":
            allowed_error = (self.tolerance / 100.0) * abs(self.target_value)
        else:
            allowed_error = self.tolerance

        self.status = "PASS" if self.error <= allowed_error else "FAIL"

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
            "ErrorPercent": round(self.error_percent, 4),
            "Tolerance": self.tolerance,
            "ToleranceType": self.tolerance_type,
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