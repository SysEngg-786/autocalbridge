# File: src/core/test_engine.py
# Path: /d/Projects/autocalbridge/src/core/test_engine.py
# Purpose: Execute test sequences with two-ended support, synchronization, and
#          error handling. Uses structured operational, audit, and security
#          loggers so calibration execution is traceable with session context.
#          Procedure-based execution returns canonical TestResult objects.

import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from src.core.visa_manager import VisaManager
from src.core.endpoints.instrument_endpoint import InstrumentEndpointError
from src.core.endpoints.endpoint_factory import create_from_resource_string
from src.core.procedure_config import ProcedureConfig
from src.models.test_result import TestResult
from security.command_policy import CommandPolicy

# Structured loggers.
from src.utils.structured_logger import (
    get_operational_logger,
    get_audit_logger,
    get_security_logger,
)


class TestEngine:
    """Executes test sequences with two-ended (source + DUT) support.

    DESIGN NOTE:
    Source and DUT are treated as two independent instrument endpoints.

    Connection is performed through connect_source() and connect_dut(), which
    create endpoints from implicit resource strings and optional command
    policies. ACB does not branch on simulator vs physical instrument type.

    Calibration execution events are written to structured audit logs.
    Errors and lifecycle events go to operational logs. Safety violations
    go to the security log.

    Procedure-based execution returns TestResult objects for canonical
    traceability and report generation.
    """

    def __init__(self, visa_manager=None):
        """Initialize the test engine.

        Args:
            visa_manager: Optional VisaManager instance used for physical VISA
                endpoints. Simulator endpoints do not use it.
        """
        self.visa_manager = visa_manager if visa_manager else VisaManager()
        self.source = None  # Reference standard endpoint
        self.dut = None     # Unit under test endpoint
        self.results: List[TestResult] = []
        self._sync_enabled = True
        self._sync_method = "opc"  # "opc", "wai", or "delay"
        self._settle_delay_ms = 100
        self._error_checking_enabled = True
        self._stop_on_error = True
        self._errors = []  # Track errors encountered
        self._source_safety_limits = {}  # command root -> {"min":..., "max":...}

        self._operational_logger = get_operational_logger()
        self._audit_logger = get_audit_logger()
        self._security_logger = get_security_logger()

    # ========================================================================
    # Configuration
    # ========================================================================

    def set_sync_config(self, enabled=True, method="opc", delay_ms=100):
        """Configure synchronization settings."""
        self._sync_enabled = enabled
        self._sync_method = method
        self._settle_delay_ms = delay_ms
        self._operational_logger.info(
            "Sync config updated",
            extra={
                "event_type": "sync_config",
                "enabled": enabled,
                "method": method,
                "delay_ms": delay_ms,
            },
        )

    def set_error_config(self, enabled=True, stop_on_error=True):
        """Configure error handling settings."""
        self._error_checking_enabled = enabled
        self._stop_on_error = stop_on_error
        self._operational_logger.info(
            "Error config updated",
            extra={
                "event_type": "error_config",
                "enabled": enabled,
                "stop_on_error": stop_on_error,
            },
        )

    def set_source_safety_limits(self, limits: Dict[str, Dict[str, float]]):
        """Set safety limits for the source instrument.

        Args:
            limits: Mapping of command root to {"min": float, "max": float}.
                Example:
                    {
                        "SOUR:VOLT": {"min": -10.0, "max": 10.0},
                        "SOUR:CURR": {"min": 0.0, "max": 1.0}
                    }
        """
        self._source_safety_limits = limits or {}
        self._operational_logger.info(
            "Source safety limits set",
            extra={
                "event_type": "safety_limits_set",
                "limits": self._source_safety_limits,
            },
        )

    # ========================================================================
    # Connection Management
    # ========================================================================

    def connect_source(self, address, timeout=5000, command_policy=None):
        """
        Connect to the source endpoint using an implicit resource string.

        Args:
            address: Implicit endpoint resource string.
            timeout: Timeout in milliseconds.
            command_policy: Optional CommandPolicy for physical endpoints.

        Returns:
            bool: True if connected, False on failure.
        """
        try:
            endpoint = create_from_resource_string(
                address,
                self.visa_manager,
                command_policy=command_policy,
            )
            endpoint.open(address, timeout)
        except InstrumentEndpointError as exc:
            self._operational_logger.error(
                "Source connection failed",
                extra={
                    "event_type": "source_connect_failed",
                    "address": address,
                    "error": str(exc),
                },
            )
            return False
        except Exception as exc:
            self._operational_logger.error(
                "Unexpected source connection failure",
                extra={
                    "event_type": "source_connect_failed",
                    "address": address,
                    "error": str(exc),
                },
            )
            return False

        self.source = endpoint
        self._operational_logger.info(
            "Source connected",
            extra={
                "event_type": "source_connected",
                "address": address,
            },
        )
        return True

    def connect_dut(self, address, timeout=5000, command_policy=None):
        """
        Connect to the DUT endpoint using an implicit resource string.

        Args:
            address: Implicit endpoint resource string.
            timeout: Timeout in milliseconds.
            command_policy: Optional CommandPolicy for physical endpoints.

        Returns:
            bool: True if connected, False on failure.
        """
        try:
            endpoint = create_from_resource_string(
                address,
                self.visa_manager,
                command_policy=command_policy,
            )
            endpoint.open(address, timeout)
        except InstrumentEndpointError as exc:
            self._operational_logger.error(
                "DUT connection failed",
                extra={
                    "event_type": "dut_connect_failed",
                    "address": address,
                    "error": str(exc),
                },
            )
            return False
        except Exception as exc:
            self._operational_logger.error(
                "Unexpected DUT connection failure",
                extra={
                    "event_type": "dut_connect_failed",
                    "address": address,
                    "error": str(exc),
                },
            )
            return False

        self.dut = endpoint
        self._operational_logger.info(
            "DUT connected",
            extra={
                "event_type": "dut_connected",
                "address": address,
            },
        )
        return True

    # ========================================================================
    # Disconnect
    # ========================================================================

    def disconnect_source(self):
        """Disconnect and release the source endpoint."""
        if self.source:
            try:
                self.source.close()
            except Exception as exc:
                self._operational_logger.warning(
                    "Error closing source",
                    extra={"event_type": "source_close_failed", "error": str(exc)},
                )
        self.source = None
        self._operational_logger.info(
            "Source disconnected",
            extra={"event_type": "source_disconnected"},
        )

    def disconnect_dut(self):
        """Disconnect and release the DUT endpoint."""
        if self.dut:
            try:
                self.dut.close()
            except Exception as exc:
                self._operational_logger.warning(
                    "Error closing DUT",
                    extra={"event_type": "dut_close_failed", "error": str(exc)},
                )
        self.dut = None
        self._operational_logger.info(
            "DUT disconnected",
            extra={"event_type": "dut_disconnected"},
        )

    def disconnect_all(self):
        """Disconnect all instrument endpoints."""
        self.disconnect_source()
        self.disconnect_dut()

    # ========================================================================
    # Identity and Status
    # ========================================================================

    def query_identity(self, instrument, name="Instrument"):
        """Query instrument identity."""
        if not instrument:
            self._operational_logger.error(
                f"{name} not connected",
                extra={"event_type": "identity_failed", "instrument_name": name},
            )
            return None
        try:
            idn = instrument.query("*IDN?").strip()
            self._operational_logger.info(
                f"{name} identity queried",
                extra={
                    "event_type": "identity_queried",
                    "instrument_name": name,
                    "identity": idn,
                },
            )
            return idn
        except Exception as exc:
            self._operational_logger.error(
                f"{name} identity query failed",
                extra={
                    "event_type": "identity_failed",
                    "instrument_name": name,
                    "error": str(exc),
                },
            )
            return None

    def query_source_identity(self):
        """Query the source endpoint identity."""
        return self.query_identity(self.source, "Source")

    def query_dut_identity(self):
        """Query the DUT endpoint identity."""
        return self.query_identity(self.dut, "DUT")

    # ========================================================================
    # Synchronization
    # ========================================================================

    def wait_for_settle(self, instrument):
        """Wait for instrument to settle after a command."""
        if not self._sync_enabled:
            self._operational_logger.debug(
                "Sync disabled - using fixed delay",
                extra={"event_type": "sync_fallback"},
            )
            time.sleep(self._settle_delay_ms / 1000.0)
            return

        try:
            if self._sync_method == "opc":
                result = instrument.query("*OPC?")
                self._operational_logger.debug(
                    f"*OPC? returned: {result.strip()}",
                    extra={"event_type": "sync_opc"},
                )
            elif self._sync_method == "wai":
                instrument.write("*WAI")
                time.sleep(0.01)
                self._operational_logger.debug(
                    "*WAI executed",
                    extra={"event_type": "sync_wai"},
                )
            else:
                self._operational_logger.debug(
                    f"Using fallback delay: {self._settle_delay_ms}ms",
                    extra={"event_type": "sync_fallback"},
                )
                time.sleep(self._settle_delay_ms / 1000.0)
        except Exception as exc:
            self._operational_logger.warning(
                f"Sync failed: {exc}. Using fallback delay.",
                extra={"event_type": "sync_failed", "error": str(exc)},
            )
            time.sleep(self._settle_delay_ms / 1000.0)

    # ========================================================================
    # Error Handling
    # ========================================================================

    def check_errors(self, instrument, name="Instrument"):
        """Check instrument error queue.

        Queries SYST:ERR? as the authoritative error indicator.
        ESR is queried for diagnostic context but does not trigger
        a failure on its own, because power-on or event bits may be set
        without an actual command error.

        Returns:
            bool: True if no errors, False if errors detected.
        """
        if not self._error_checking_enabled:
            return True

        try:
            error_response = instrument.query("SYST:ERR?")
            error_message = error_response.strip()

            if error_message.startswith("0,"):
                return True

            esr = instrument.query("*ESR?")
            esr_value = int(esr.strip())

            self._errors.append({
                "instrument": name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "esr": esr_value,
                "message": error_message
            })

            self._operational_logger.error(
                f"{name} error detected",
                extra={
                    "event_type": "instrument_error",
                    "instrument_name": name,
                    "esr": esr_value,
                    "error_message": error_message,
                },
            )

            if self._stop_on_error:
                self._operational_logger.critical(
                    f"Stopping due to error on {name}",
                    extra={"event_type": "stop_on_error", "instrument_name": name},
                )
                return False

            return False

        except Exception as exc:
            self._operational_logger.warning(
                f"Error checking failed on {name}: {exc}",
                extra={
                    "event_type": "error_check_failed",
                    "instrument_name": name,
                    "error": str(exc),
                },
            )
            return True

    def get_errors(self):
        """Get the list of errors encountered."""
        return self._errors

    def clear_errors(self):
        """Clear the error list."""
        self._errors = []

    # ========================================================================
    # Core Operations
    # ========================================================================

    def set_source_value(self, value):
        """Set the source to a specific value.

        Args:
            value: Target value (voltage, current, etc.)

        Returns:
            bool: True if successful.
        """
        if not self.source:
            self._operational_logger.error(
                "Source not connected",
                extra={"event_type": "source_not_connected"},
            )
            return False
        try:
            command = f"SOUR:VOLT {value}"
            self.source.write(command)
            self._operational_logger.debug(
                f"Source set to {value} V",
                extra={"event_type": "source_set", "command": command, "value": value},
            )
            return True
        except Exception as exc:
            self._operational_logger.error(
                f"Source set failed: {exc}",
                extra={"event_type": "source_set_failed", "error": str(exc)},
            )
            return False

    def measure_dut(self):
        """Read a measurement from the DUT endpoint.

        Returns:
            float: Measured value, or None on failure.
        """
        if not self.dut:
            self._operational_logger.error(
                "DUT not connected",
                extra={"event_type": "dut_not_connected"},
            )
            return None
        try:
            raw = self.dut.query("READ?")
            value = float(raw)
            self._operational_logger.debug(
                f"DUT measured: {value:.4f} V",
                extra={"event_type": "dut_measured", "value": value},
            )
            return value
        except Exception as exc:
            self._operational_logger.error(
                f"DUT measurement failed: {exc}",
                extra={"event_type": "dut_measure_failed", "error": str(exc)},
            )
            return None

    # ========================================================================
    # Legacy Calibration Sequence
    # ========================================================================

    def run_calibration_sequence(self, test_points, tolerance, operator_name="Default"):
        """Run a legacy hardcoded calibration sequence.

        This method remains for backward compatibility during Phase 3
        transition. New execution should use run_procedure().
        """
        if not self.source:
            self._operational_logger.error(
                "Source not connected",
                extra={"event_type": "source_not_connected"},
            )
            return []
        if not self.dut:
            self._operational_logger.error(
                "DUT not connected",
                extra={"event_type": "dut_not_connected"},
            )
            return []

        self.results = []
        self._errors = []
        self._operational_logger.info(
            f"Starting legacy calibration sequence for {len(test_points)} points",
            extra={
                "event_type": "calibration_start",
                "operator": operator_name,
                "tolerance": tolerance,
                "point_count": len(test_points),
            },
        )

        for target in test_points:
            self._operational_logger.info(
                f"Testing {target} V...",
                extra={"event_type": "point_start", "target": target},
            )

            if not self.set_source_value(target):
                continue

            self.wait_for_settle(self.source)

            if not self.check_errors(self.source, "Source"):
                if self._stop_on_error:
                    break
                continue

            measured = self.measure_dut()
            if measured is None:
                continue

            if not self.check_errors(self.dut, "DUT"):
                if self._stop_on_error:
                    break
                continue

            error = abs(measured - target)
            status = "PASS" if error <= tolerance else "FAIL"

            result = {
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Operator": operator_name,
                "Target_V": target,
                "Measured_V": measured,
                "Error_V": round(error, 4),
                "Status": status
            }
            self.results.append(result)

            if status == "PASS":
                self._operational_logger.info(
                    f"Measured: {measured} | Error: {error} -> PASS",
                    extra={"event_type": "point_passed", "target": target},
                )
            else:
                self._operational_logger.warning(
                    f"Measured: {measured} | Error: {error} -> FAIL",
                    extra={"event_type": "point_failed", "target": target},
                )

        total = len(self.results)
        passed = sum(1 for r in self.results if r["Status"] == "PASS")
        self._operational_logger.info(
            f"Legacy sequence complete: {passed}/{total} PASSED",
            extra={"event_type": "calibration_complete", "passed": passed, "total": total},
        )
        if self._errors:
            self._operational_logger.warning(
                f"Errors encountered: {len(self._errors)}",
                extra={"event_type": "calibration_errors", "error_count": len(self._errors)},
            )

        return self.results

    # ========================================================================
    # Procedure-Based Calibration Sequence
    # ========================================================================

    def run_procedure(
        self,
        procedure: ProcedureConfig,
        operator_name="Default",
        session_id="",
        supervisor="",
        source_id="",
        dut_id="",
    ):
        """Run a procedure-defined calibration sequence.

        This method uses the procedure's source command template and DUT
        query command instead of hardcoded SOUR:VOLT and READ?.

        Safety limits are enforced before source commands are sent.

        Results are returned as canonical TestResult objects.

        Args:
            procedure: ProcedureConfig object.
            operator_name: Operator identifier for logs and results.
            session_id: Session identifier for traceability.
            supervisor: Supervisor identifier for traceability.
            source_id: Registry ID of source instrument.
            dut_id: Registry ID of DUT instrument.

        Returns:
            list[TestResult]: Canonical result objects.
        """
        if not self.source:
            self._operational_logger.error(
                "Source not connected",
                extra={"event_type": "source_not_connected"},
            )
            return []
        if not self.dut:
            self._operational_logger.error(
                "DUT not connected",
                extra={"event_type": "dut_not_connected"},
            )
            return []

        self.results = []
        self._errors = []

        self._audit_logger.info(
            "Procedure started",
            extra={
                "event_type": "procedure_start",
                "procedure_id": procedure.procedure_id,
                "operator": operator_name,
                "point_count": len(procedure.points),
                "tolerance": procedure.tolerance,
                "source_command_template": procedure.source_command_template,
                "dut_query_command": procedure.dut_query_command,
            },
        )

        for target in procedure.points:
            self._audit_logger.info(
                "Point started",
                extra={
                    "event_type": "point_start",
                    "procedure_id": procedure.procedure_id,
                    "target": target,
                },
            )

            source_command = procedure.source_command_template.format(value=target)

            if not self._check_source_safety(source_command, target):
                self._security_logger.error(
                    "Safety limit violation",
                    extra={
                        "event_type": "safety_limit_violation",
                        "procedure_id": procedure.procedure_id,
                        "command": source_command,
                        "target": target,
                    },
                )
                self._errors.append({
                    "instrument": "Source",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "esr": 0,
                    "message": f"Safety limit violated for {source_command}"
                })
                if self._stop_on_error:
                    break
                continue

            try:
                self.source.write(source_command)
                self._audit_logger.info(
                    "Source command sent",
                    extra={
                        "event_type": "source_command_sent",
                        "procedure_id": procedure.procedure_id,
                        "command": source_command,
                    },
                )
            except Exception as exc:
                self._operational_logger.error(
                    f"Source command failed: {exc}",
                    extra={
                        "event_type": "source_command_failed",
                        "procedure_id": procedure.procedure_id,
                        "command": source_command,
                        "error": str(exc),
                    },
                )
                continue

            self.wait_for_settle(self.source)

            if not self.check_errors(self.source, "Source"):
                if self._stop_on_error:
                    break
                continue

            measured = self.measure_with_command(procedure.dut_query_command)
            if measured is None:
                continue

            if not self.check_errors(self.dut, "DUT"):
                if self._stop_on_error:
                    break
                continue

            error = abs(measured - target)
            status = "PASS" if error <= procedure.tolerance else "FAIL"

            result = TestResult(
                target_value=target,
                measured_value=measured,
                tolerance=procedure.tolerance,
                operator=operator_name,
                session_id=session_id,
                supervisor=supervisor,
                procedure_id=procedure.procedure_id,
                source_id=source_id,
                dut_id=dut_id,
                metadata={
                    "source_command": source_command,
                    "dut_query_command": procedure.dut_query_command,
                },
            )
            self.results.append(result)

            self._audit_logger.info(
                "Point result",
                extra={
                    "event_type": "point_result",
                    "procedure_id": procedure.procedure_id,
                    "target": target,
                    "measured": measured,
                    "error": round(error, 4),
                    "status": status,
                },
            )

        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASS")

        self._audit_logger.info(
            "Procedure completed",
            extra={
                "event_type": "procedure_complete",
                "procedure_id": procedure.procedure_id,
                "passed": passed,
                "total": total,
                "error_count": len(self._errors),
            },
        )

        if self._errors:
            self._operational_logger.warning(
                f"Errors encountered during procedure: {len(self._errors)}",
                extra={
                    "event_type": "procedure_errors",
                    "procedure_id": procedure.procedure_id,
                    "error_count": len(self._errors),
                },
            )

        return self.results

    def measure_with_command(self, query_command):
        """Read a measurement from the DUT using a procedure-supplied query."""
        if not self.dut:
            self._operational_logger.error(
                "DUT not connected",
                extra={"event_type": "dut_not_connected"},
            )
            return None
        try:
            raw = self.dut.query(query_command)
            value = float(raw)
            self._operational_logger.debug(
                f"DUT measured: {value}",
                extra={"event_type": "dut_measured", "value": value, "command": query_command},
            )
            return value
        except Exception as exc:
            self._operational_logger.error(
                f"DUT measurement failed for {query_command}: {exc}",
                extra={
                    "event_type": "dut_measure_failed",
                    "command": query_command,
                    "error": str(exc),
                },
            )
            return None

    # ========================================================================
    # Safety Limit Helpers
    # ========================================================================

    def _extract_command_root(self, source_command_template: str) -> str:
        """Extract the SCPI command root from a template.

        Example:
            "SOUR:VOLT {value}" -> "SOUR:VOLT"
            "FREQ {value} MHz"  -> "FREQ"
        """
        root = source_command_template.strip().split("{")[0].strip()
        return root.upper()

    def _check_source_safety(self, source_command: str, value: float) -> bool:
        """Check the source command value against configured safety limits.

        Args:
            source_command: Full formatted source command string.
            value: Numeric value being set.

        Returns:
            bool: True if allowed, False if out of limits.
        """
        if not self._source_safety_limits:
            return True

        root = source_command.strip().split(" ")[0].upper()

        limits = self._source_safety_limits.get(root)
        if limits is None:
            return True

        min_val = limits.get("min")
        max_val = limits.get("max")

        if min_val is not None and value < min_val:
            self._security_logger.warning(
                f"Safety: {root} value {value} below min {min_val}",
                extra={
                    "event_type": "safety_below_min",
                    "command_root": root,
                    "value": value,
                    "min": min_val,
                },
            )
            return False
        if max_val is not None and value > max_val:
            self._security_logger.warning(
                f"Safety: {root} value {value} above max {max_val}",
                extra={
                    "event_type": "safety_above_max",
                    "command_root": root,
                    "value": value,
                    "max": max_val,
                },
            )
            return False

        return True

    def get_results(self):
        """Get the test results."""
        return self.results

    def close(self):
        """Close all instrument endpoints."""
        self.disconnect_all()