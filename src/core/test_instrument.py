# File: src/core/test_instrument.py
# Path: /autocalbridge/src/core/test_instrument.py
# Purpose: Mock instrument simulator for testing without hardware.
# Supports both source and DUT emulation with error simulation.

import random
from datetime import datetime


class MockInstrument:
    """Simulates an instrument for testing and development."""

    # ========================================================================
    # Design Mode Flags
    # ========================================================================

    MODE_SOURCE = "source"
    MODE_DUT = "dut"

    # ========================================================================
    # Initialization
    # ========================================================================

    def __init__(self, vendor="Keysight", model="34461A", serial="MOCK12345", mode="dut"):
        """Initialize the mock instrument.

        Args:
            vendor: Vendor name (Keysight, Tektronix, etc.)
            model: Instrument model
            serial: Serial number
            mode: "source" or "dut" — determines behavior
        """
        self.vendor = vendor
        self.model = model
        self.serial = serial
        self.version = "A.02.10"
        self.idn = f"{vendor} TECHNOLOGIES,{model},{serial},{self.version}"
        self.mode = mode

        # Command tracking
        self.command_history = []

        # Source-specific attributes
        self._source_value = 0.0
        self._source_range = 10.0

        # DUT-specific attributes
        self._dut_value = 1.0  # Default target
        self._offset = 0.0
        self._noise = 0.001
        self._fail_rate = 0.0

        # Error simulation
        self._simulate_error = False
        self._error_message = ""
        self._error_code = 0
        self._force_error = False

        # State
        self._configured = False

    # ========================================================================
    # Identity
    # ========================================================================

    def query_identity(self):
        """Return the instrument identity."""
        return self.idn

    # ========================================================================
    # Core VISA Interface
    # ========================================================================

    def query(self, command):
        """Simulate query command."""
        self.command_history.append(command)
        cmd = command.strip().upper()

        if cmd == "*IDN?":
            return self.idn

        # Error simulation for *ESR? and SYST:ERR?
        if cmd == "*ESR?":
            if self._simulate_error or self._force_error:
                return str(self._error_code)
            return "0"

        if cmd == "SYST:ERR?":
            if self._simulate_error or self._force_error:
                error_msg = self._error_message if self._error_message else "Simulated error"
                return f'{self._error_code},"{error_msg}"'
            return '0,"No error"'

        # Source mode commands
        if self.mode == self.MODE_SOURCE:
            return self._handle_source_command(cmd, command)

        # DUT mode commands
        if self.mode == self.MODE_DUT:
            return self._handle_dut_command(cmd, command)

        return ""

    def write(self, command):
        """Simulate write command."""
        self.command_history.append(command)
        cmd = command.strip().upper()

        # Source mode commands
        if self.mode == self.MODE_SOURCE:
            self._handle_source_write(cmd, command)
            return ""

        # DUT mode commands
        if self.mode == self.MODE_DUT:
            self._handle_dut_write(cmd, command)
            return ""

        return ""

    def close(self):
        """Simulate closing the connection."""
        pass

    # ========================================================================
    # Source-Specific Handlers
    # ========================================================================

    def _handle_source_command(self, cmd, full_cmd):
        """Handle query commands in source mode."""
        if cmd.startswith("SOUR:VOLT?"):
            return f"{self._source_value:.6f}"
        if cmd.startswith("SOUR:RANG?"):
            return f"{self._source_range:.6f}"
        if cmd == "*OPC?":
            return "1"
        return ""

    def _handle_source_write(self, cmd, full_cmd):
        """Handle write commands in source mode."""
        if cmd.startswith("SOUR:VOLT"):
            try:
                parts = full_cmd.split()
                if len(parts) >= 2:
                    self._source_value = float(parts[1])
            except ValueError:
                pass
        if cmd.startswith("SOUR:RANG"):
            try:
                parts = full_cmd.split()
                if len(parts) >= 2:
                    self._source_range = float(parts[1])
            except ValueError:
                pass
        if cmd.startswith("*RST"):
            self._source_value = 0.0
            self._source_range = 10.0
            self._configured = False
            self._simulate_error = False
            self._force_error = False
        if cmd == "*CLS":
            self._simulate_error = False
            self._force_error = False
            self._error_message = ""

    # ========================================================================
    # DUT-Specific Handlers
    # ========================================================================

    def _handle_dut_command(self, cmd, full_cmd):
        """Handle query commands in DUT mode."""
        if cmd == "READ?":
            return self._generate_measurement()
        if cmd.startswith("CONF") or cmd.startswith("SENS"):
            return ""
        if cmd == "*OPC?":
            return "1"
        return ""

    def _handle_dut_write(self, cmd, full_cmd):
        """Handle write commands in DUT mode."""
        if cmd.startswith("CONF") or cmd.startswith("SENS"):
            self._configured = True
        if cmd.startswith("*RST"):
            self._configured = False
            self._offset = 0.0
            self._simulate_error = False
            self._force_error = False
        if cmd == "*CLS":
            self._simulate_error = False
            self._force_error = False
            self._error_message = ""

    # ========================================================================
    # Measurement Generation
    # ========================================================================

    def _generate_measurement(self):
        """Generate a simulated measurement value."""
        if self._simulate_error or self._force_error:
            return "READ FAILED"

        # Generate value around target
        target = self._dut_value + self._offset
        value = target + random.gauss(0, self._noise)

        # Occasionally simulate failure
        if random.random() < self._fail_rate:
            return "READ FAILED"

        return f"{value:.6f}"

    # ========================================================================
    # Configuration Methods
    # ========================================================================

    def set_mode(self, mode):
        """Set the instrument mode: 'source' or 'dut'."""
        if mode in [self.MODE_SOURCE, self.MODE_DUT]:
            self.mode = mode

    def set_target(self, target):
        """Set the target value for DUT measurements."""
        self._dut_value = target

    def set_offset(self, offset):
        """Set offset to simulate systematic error."""
        self._offset = offset

    def set_noise(self, noise):
        """Set noise level."""
        self._noise = noise

    def set_fail_rate(self, rate):
        """Set failure rate (0.0 to 1.0)."""
        self._fail_rate = max(0.0, min(1.0, rate))

    def set_source_value(self, value):
        """Set the source output value."""
        self._source_value = value

    def get_source_value(self):
        """Get the current source output value."""
        return self._source_value

    # ========================================================================
    # Error Simulation
    # ========================================================================

    def enable_error(self, code=1, message="Simulated error"):
        """Enable error simulation for the next query."""
        self._simulate_error = True
        self._error_code = code
        self._error_message = message

    def force_error(self, code=1, message="Forced error"):
        """Force a persistent error condition."""
        self._force_error = True
        self._error_code = code
        self._error_message = message

    def disable_error(self):
        """Disable error simulation."""
        self._simulate_error = False
        self._force_error = False
        self._error_message = ""

    def clear_error(self):
        """Clear error state."""
        self.disable_error()
        self._error_code = 0

    def get_command_history(self):
        """Get the command history."""
        return self.command_history

    def clear_history(self):
        """Clear command history."""
        self.command_history = []


class MockSource(MockInstrument):
    """Convenience class for source emulation."""

    def __init__(self, vendor="Keysight", model="34461A", serial="MOCK12345"):
        super().__init__(vendor, model, serial, mode="source")


class MockDUT(MockInstrument):
    """Convenience class for DUT emulation."""

    def __init__(self, vendor="Keysight", model="34461A", serial="MOCK12345"):
        super().__init__(vendor, model, serial, mode="dut")
        self._dut_value = 1.0  # Default target