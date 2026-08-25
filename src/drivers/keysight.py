# File: src/drivers/keysight.py
# Path: /autocalbridge/src/drivers/keysight.py
# Purpose: Keysight-specific instrument driver.

import time
from src.drivers.base_driver import BaseDriver


class KeysightDriver(BaseDriver):
    """Keysight instrument driver."""

    SUPPORTED_INSTRUMENTS = ["34461A", "34970A", "N5171B", "N9020A"]

    def get_vendor_name(self):
        """Get the vendor name."""
        return "Keysight"

    def get_instruments(self):
        """Get list of supported instrument models."""
        return self.SUPPORTED_INSTRUMENTS

    def configure(self, instrument, config):
        """Configure the instrument for measurement."""
        try:
            instrument.write("*RST")
            time.sleep(0.2)
            instrument.write("*CLS")
            instrument.write("CONF:VOLT:DC")
            instrument.write("SENS:VOLT:DC:NPLC 1")
            return True
        except Exception as e:
            print(f"Keysight configuration failed: {e}")
            return False

    def measure(self, instrument, target_value=None):
        """Take a DC voltage measurement."""
        try:
            raw = instrument.query("READ?")
            value = float(raw)
            return value
        except Exception as e:
            print(f"Keysight measurement failed: {e}")
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

    def set_voltage_range(self, instrument, range_value):
        """Set the voltage range."""
        try:
            instrument.write(f"SENS:VOLT:RANG {range_value}")
            return True
        except Exception as e:
            print(f"Range set failed: {e}")
            return False

    def set_measurement_mode(self, instrument, mode="VOLT:DC"):
        """Set the measurement mode (VOLT:DC, VOLT:AC, CURR:DC, etc.)."""
        try:
            instrument.write(f"CONF:{mode}")
            return True
        except Exception as e:
            print(f"Mode set failed: {e}")
            return False