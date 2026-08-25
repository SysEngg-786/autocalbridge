# File: src/drivers/tektronix.py
# Path: /autocalbridge/src/drivers/tektronix.py
# Purpose: Tektronix-specific instrument driver.

import time
from src.drivers.base_driver import BaseDriver


class TektronixDriver(BaseDriver):
    """Tektronix instrument driver."""

    SUPPORTED_INSTRUMENTS = ["MSO2024", "TDS3012", "MSO5000", "TDS7000"]

    def get_vendor_name(self):
        """Get the vendor name."""
        return "Tektronix"

    def get_instruments(self):
        """Get list of supported instrument models."""
        return self.SUPPORTED_INSTRUMENTS

    def configure(self, instrument, config):
        """Configure the instrument for measurement."""
        try:
            instrument.write("*RST")
            time.sleep(0.2)
            instrument.write("*CLS")
            # Auto-set oscilloscope scales
            instrument.write("AUTOSET EXECUTE")
            # Set measurement type to frequency
            instrument.write("MEASU:IMM:TYPE FREQ")
            return True
        except Exception as e:
            print(f"Tektronix configuration failed: {e}")
            return False

    def measure(self, instrument, target_value=None):
        """Take a measurement."""
        try:
            # Get the current measurement value
            raw = instrument.query("MEASU:IMM:VAL?")
            value = float(raw)
            return value
        except Exception as e:
            print(f"Tektronix measurement failed: {e}")
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

    def set_measurement_type(self, instrument, measurement_type="FREQ"):
        """Set the measurement type (FREQ, VDC, VAC, etc.)."""
        try:
            instrument.write(f"MEASU:IMM:TYPE {measurement_type}")
            return True
        except Exception as e:
            print(f"Measurement type set failed: {e}")
            return False

    def select_channel(self, instrument, channel=1):
        """Select and enable a channel."""
        try:
            instrument.write(f"SEL:CH{channel} ON")
            return True
        except Exception as e:
            print(f"Channel selection failed: {e}")
            return False