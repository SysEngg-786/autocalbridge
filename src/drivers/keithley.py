# File: src/drivers/keithley.py
# Path: /autocalbridge/src/drivers/keithley.py
# Purpose: Keithley-specific instrument driver.

import time
from src.drivers.base_driver import BaseDriver


class KeithleyDriver(BaseDriver):
    """Keithley instrument driver."""

    SUPPORTED_INSTRUMENTS = ["2450", "2400", "2600B", "4200A"]

    def get_vendor_name(self):
        """Get the vendor name."""
        return "Keithley"

    def get_instruments(self):
        """Get list of supported instrument models."""
        return self.SUPPORTED_INSTRUMENTS

    def configure(self, instrument, config):
        """Configure the instrument for measurement."""
        try:
            instrument.write("*RST")
            time.sleep(0.2)
            instrument.write("*CLS")
            # Configure for DC voltage measurement
            instrument.write("SENS:FUNC 'VOLT:DC'")
            instrument.write("SENS:VOLT:RANG 10")
            return True
        except Exception as e:
            print(f"Keithley configuration failed: {e}")
            return False

    def measure(self, instrument, target_value=None):
        """Take a DC voltage measurement."""
        try:
            raw = instrument.query("READ?")
            value = float(raw)
            return value
        except Exception as e:
            print(f"Keithley measurement failed: {e}")
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

    def set_measurement_function(self, instrument, function="VOLT:DC"):
        """Set the measurement function (VOLT:DC, VOLT:AC, CURR:DC, etc.)."""
        try:
            instrument.write(f"SENS:FUNC '{function}'")
            return True
        except Exception as e:
            print(f"Function set failed: {e}")
            return False

    def set_voltage_range(self, instrument, range_value):
        """Set the voltage range."""
        try:
            instrument.write(f"SENS:VOLT:RANG {range_value}")
            return True
        except Exception as e:
            print(f"Range set failed: {e}")
            return False

    def set_current_range(self, instrument, range_value):
        """Set the current range."""
        try:
            instrument.write(f"SENS:CURR:RANG {range_value}")
            return True
        except Exception as e:
            print(f"Range set failed: {e}")
            return False