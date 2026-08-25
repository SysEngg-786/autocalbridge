# File: src/models/test_result.py
# Path: /autocalbridge/src/models/test_result.py
# Purpose: Data model for test results.

from datetime import datetime


class TestResult:
    """Data model for a single test result."""

    def __init__(self, target_value, measured_value, tolerance, operator="Default", vendor="Unknown", instrument="Unknown"):
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.operator = operator
        self.vendor = vendor
        self.instrument = instrument
        self.target_value = target_value
        self.measured_value = measured_value
        self.tolerance = tolerance
        self.error = abs(measured_value - target_value)
        self.status = "PASS" if self.error <= tolerance else "FAIL"

    def to_dict(self):
        """Convert to dictionary for CSV export."""
        return {
            "Timestamp": self.timestamp,
            "Operator": self.operator,
            "Vendor": self.vendor,
            "Instrument": self.instrument,
            "Target_V": self.target_value,
            "Measured_V": self.measured_value,
            "Tolerance_V": self.tolerance,
            "Error_V": round(self.error, 4),
            "Status": self.status
        }

    def __repr__(self):
        return f"TestResult(target={self.target_value}V, measured={self.measured_value}V, status={self.status})"