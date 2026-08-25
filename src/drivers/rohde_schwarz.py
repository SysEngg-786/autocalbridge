# File: src/drivers/rohde_schwarz.py
# Path: /autocalbridge/src/drivers/rohde_schwarz.py
# Purpose: Rohde & Schwarz-specific instrument driver.

import time
from src.drivers.base_driver import BaseDriver


class RohdeSchwarzDriver(BaseDriver):
    """Rohde & Schwarz instrument driver."""

    SUPPORTED_INSTRUMENTS = ["SMB100A", "FSV3000", "SMW200A", "FSW"]

    def get_vendor_name(self):
        """Get the vendor name."""
        return "Rohde & Schwarz"

    def get_instruments(self):
        """Get list of supported instrument models."""
        return self.SUPPORTED_INSTRUMENTS

    def configure(self, instrument, config):
        """Configure the instrument for measurement."""
        try:
            instrument.write("*RST")
            time.sleep(0.2)
            instrument.write("*CLS")
            # Disable continuous sweep mode for single measurements
            instrument.write("INIT:CONT OFF")
            # Set default center frequency
            instrument.write("FREQ:CENT 2.4GHz")
            return True
        except Exception as e:
            print(f"Rohde & Schwarz configuration failed: {e}")
            return False

    def measure(self, instrument, target_value=None):
        """Take a measurement."""
        try:
            # Trigger a single sweep and get trace data
            instrument.write("INIT:IMM")
            time.sleep(0.1)
            raw = instrument.query("TRAC:DATA? TRACE1")
            # Parse the first data point (simplified)
            values = raw.strip().split(',')
            if values:
                value = float(values[0])
                return value
            return None
        except Exception as e:
            print(f"Rohde & Schwarz measurement failed: {e}")
            return None

    def query_identity(self, instrument):
        """Query instrument identity."""
        try:
            return instrument.query("*IDN?").strip()
        except Exception as e:
            print(f"Identity query failed: {e}")
            return None

    def reset(self, instrument):
        """Reset the instrument."""
        try:
            instrument.write("*RST")
            time.sleep(0.2)
            instrument.write("*CLS")
            return True
        except Exception as e:
            print(f"Reset failed: {e}")
            return False

    def set_center_frequency(self, instrument, frequency):
        """Set the center frequency."""
        try:
            instrument.write(f"FREQ:CENT {frequency}")
            return True
        except Exception as e:
            print(f"Center frequency set failed: {e}")
            return False

    def set_span(self, instrument, span):
        """Set the frequency span."""
        try:
            instrument.write(f"FREQ:SPAN {span}")
            return True
        except Exception as e:
            print(f"Span set failed: {e}")
            return False