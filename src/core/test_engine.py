# File: src/core/test_engine.py
# Path: /autocalbridge/src/core/test_engine.py
# Purpose: Execute test sequences with two-ended support, synchronization, and
#          error handling.

import time
import logging
from datetime import datetime

from src.core.visa_manager import VisaManager
from src.core.endpoints.instrument_endpoint import InstrumentEndpointError
from src.core.endpoints.endpoint_factory import create_from_resource_string

logger = logging.getLogger(__name__)


class TestEngine:
    """Executes test sequences with two-ended (source + DUT) support.

    DESIGN NOTE:
    Source and DUT are treated as two independent instrument endpoints.

    Connection is performed through connect_source() and connect_dut(), which
    create endpoints from implicit resource strings. ACB does not branch on
    simulator vs physical instrument type.
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
        self.results = []
        self._sync_enabled = True
        self._sync_method = "opc"  # "opc", "wai", or "delay"
        self._settle_delay_ms = 100
        self._error_checking_enabled = True
        self._stop_on_error = True
        self._errors = []  # Track errors encountered

    # ========================================================================
    # Configuration
    # ========================================================================

    def set_sync_config(self, enabled=True, method="opc", delay_ms=100):
        """Configure synchronization settings.

        Args:
            enabled: Enable synchronization
            method: "opc" (*OPC?), "wai" (*WAI), or "delay" (fixed delay)
            delay_ms: Fallback delay in milliseconds (used with "delay" method)
        """
        self._sync_enabled = enabled
        self._sync_method = method
        self._settle_delay_ms = delay_ms
        logger.info(f"Sync config: enabled={enabled}, method={method}, delay={delay_ms}ms")

    def set_error_config(self, enabled=True, stop_on_error=True):
        """Configure error handling settings.

        Args:
            enabled: Enable error checking
            stop_on_error: Stop calibration on error
        """
        self._error_checking_enabled = enabled
        self._stop_on_error = stop_on_error
        logger.info(f"Error config: enabled={enabled}, stop_on_error={stop_on_error}")

    # ========================================================================
    # Connection Management
    # ========================================================================

    def connect_source(self, address, timeout=5000):
        """
        Connect to the source endpoint using an implicit resource string.

        Supported forms:
            sim://<profile_name>
            TCPIP0::192.168.1.50::inst0::INSTR
            USB0::0x0957::0x1507::MY12345678::INSTR
            GPIB0::1::INSTR
            ASRL1::INSTR

        Args:
            address: Implicit endpoint resource string.
            timeout: Timeout in milliseconds.

        Returns:
            bool: True if connected, False on failure.
        """
        try:
            endpoint = create_from_resource_string(address, self.visa_manager)
            endpoint.open(address, timeout)
        except InstrumentEndpointError as exc:
            logger.error(f"Failed to connect source at {address}: {exc}")
            return False
        except Exception as exc:
            logger.error(f"Unexpected source connection failure at {address}: {exc}")
            return False

        self.source = endpoint
        logger.info(f"Source connected at {address}")
        return True

    def connect_dut(self, address, timeout=5000):
        """
        Connect to the DUT endpoint using an implicit resource string.

        Supported forms are the same as connect_source().

        Args:
            address: Implicit endpoint resource string.
            timeout: Timeout in milliseconds.

        Returns:
            bool: True if connected, False on failure.
        """
        try:
            endpoint = create_from_resource_string(address, self.visa_manager)
            endpoint.open(address, timeout)
        except InstrumentEndpointError as exc:
            logger.error(f"Failed to connect DUT at {address}: {exc}")
            return False
        except Exception as exc:
            logger.error(f"Unexpected DUT connection failure at {address}: {exc}")
            return False

        self.dut = endpoint
        logger.info(f"DUT connected at {address}")
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
                logger.warning(f"Error closing source: {exc}")
        self.source = None
        logger.info("Source disconnected")

    def disconnect_dut(self):
        """Disconnect and release the DUT endpoint."""
        if self.dut:
            try:
                self.dut.close()
            except Exception as exc:
                logger.warning(f"Error closing DUT: {exc}")
        self.dut = None
        logger.info("DUT disconnected")

    def disconnect_all(self):
        """Disconnect all instrument endpoints."""
        self.disconnect_source()
        self.disconnect_dut()

    # ========================================================================
    # Identity and Status
    # ========================================================================

    def query_identity(self, instrument, name="Instrument"):
        """Query instrument identity.

        Args:
            instrument: An InstrumentEndpoint-compatible object.
            name: Human-readable instrument name.

        Returns:
            str or None: Identity response string, or None on failure.
        """
        if not instrument:
            logger.error(f"{name} not connected")
            return None
        try:
            idn = instrument.query("*IDN?").strip()
            logger.info(f"{name} identity: {idn}")
            return idn
        except Exception as exc:
            logger.error(f"{name} identity query failed: {exc}")
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
        """Wait for instrument to settle after a command.

        Uses the configured synchronization method:
        - "opc": Uses *OPC? to query operation complete
        - "wai": Uses *WAI to block until complete
        - "delay": Uses a fixed time delay

        Args:
            instrument: Source or DUT endpoint.
        """
        if not self._sync_enabled:
            logger.debug("Sync disabled — using fixed delay")
            time.sleep(self._settle_delay_ms / 1000.0)
            return

        try:
            if self._sync_method == "opc":
                result = instrument.query("*OPC?")
                logger.debug(f"*OPC? returned: {result.strip()}")
            elif self._sync_method == "wai":
                instrument.write("*WAI")
                time.sleep(0.01)
                logger.debug("*WAI executed")
            else:
                logger.debug(f"Using fallback delay: {self._settle_delay_ms}ms")
                time.sleep(self._settle_delay_ms / 1000.0)
        except Exception as exc:
            logger.warning(f"Sync failed: {exc}. Using fallback delay.")
            time.sleep(self._settle_delay_ms / 1000.0)

    # ========================================================================
    # Error Handling
    # ========================================================================

    def check_errors(self, instrument, name="Instrument"):
        """Check instrument error queue.

        Queries *ESR? and SYST:ERR? through the instrument endpoint.

        Returns:
            bool: True if no errors, False if errors detected.
        """
        if not self._error_checking_enabled:
            return True

        try:
            esr = instrument.query("*ESR?")
            esr_value = int(esr.strip())

            if esr_value != 0:
                error_response = instrument.query("SYST:ERR?")
                error_message = error_response.strip()
                self._errors.append({
                    "instrument": name,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "esr": esr_value,
                    "message": error_message
                })
                logger.error(f"{name} error: ESR={esr_value}, {error_message}")

                if self._stop_on_error:
                    logger.critical(f"Stopping due to error on {name}")
                    return False

            return esr_value == 0

        except Exception as exc:
            logger.warning(f"Error checking failed on {name}: {exc}")
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
            logger.error("Source not connected")
            return False
        try:
            self.source.write(f"SOUR:VOLT {value}")
            logger.debug(f"Source set to {value} V")
            return True
        except Exception as exc:
            logger.error(f"Source set failed: {exc}")
            return False

    def measure_dut(self):
        """Read a measurement from the DUT endpoint.

        Returns:
            float: Measured value, or None on failure.
        """
        if not self.dut:
            logger.error("DUT not connected")
            return None
        try:
            raw = self.dut.query("READ?")
            value = float(raw)
            logger.debug(f"DUT measured: {value:.4f} V")
            return value
        except Exception as exc:
            logger.error(f"DUT measurement failed: {exc}")
            return None

    # ========================================================================
    # Calibration Sequence
    # ========================================================================

    def run_calibration_sequence(self, test_points, tolerance, operator_name="Default"):
        """Run a calibration sequence with two-ended (source + DUT) control.

        Args:
            test_points: List of target values.
            tolerance: PASS/FAIL tolerance.
            operator_name: Operator identifier for logs.

        Returns:
            list: Test results.
        """
        if not self.source:
            logger.error("Source not connected")
            return []
        if not self.dut:
            logger.error("DUT not connected")
            return []

        self.results = []
        self._errors = []
        logger.info(f"Starting calibration sequence for {len(test_points)} points")
        logger.info(f"Tolerance: {tolerance} V")
        logger.info(f"Sync: enabled={self._sync_enabled}, method={self._sync_method}")
        logger.info(f"Error checking: enabled={self._error_checking_enabled}, stop_on_error={self._stop_on_error}")

        for target in test_points:
            logger.info(f"Testing {target:.3f} V...")

            # 1. Set source to target value
            if not self.set_source_value(target):
                logger.error(f"Failed to set source to {target:.3f} V")
                continue

            # 2. Wait for settlement
            self.wait_for_settle(self.source)

            # 3. Check source errors
            if not self.check_errors(self.source, "Source"):
                if self._stop_on_error:
                    break
                continue

            # 4. Read DUT
            measured = self.measure_dut()
            if measured is None:
                logger.error(f"Failed to read DUT at {target:.3f} V")
                continue

            # 5. Check DUT errors
            if not self.check_errors(self.dut, "DUT"):
                if self._stop_on_error:
                    break
                continue

            # 6. Compare and determine status
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
                logger.info(f"  Measured: {measured:.4f} V | Error: {error:.4f} V -> PASS")
            else:
                logger.warning(f"  Measured: {measured:.4f} V | Error: {error:.4f} V -> FAIL")

        total = len(self.results)
        passed = sum(1 for r in self.results if r["Status"] == "PASS")
        logger.info(f"Sequence complete: {passed}/{total} PASSED")
        if self._errors:
            logger.warning(f"Errors encountered: {len(self._errors)}")

        return self.results

    def get_results(self):
        """Get the test results."""
        return self.results

    def close(self):
        """Close all instrument endpoints."""
        self.disconnect_all()