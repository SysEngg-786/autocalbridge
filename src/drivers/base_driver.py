# File: src/drivers/base_driver.py
# Path: /autocalbridge/src/drivers/base_driver.py
# Purpose: Abstract base class for all vendor-specific instrument drivers.

from abc import ABC, abstractmethod


class BaseDriver(ABC):
    """Abstract base class for all instrument drivers."""

    @abstractmethod
    def configure(self, instrument, config):
        """Configure the instrument for measurement.

        Args:
            instrument: VISA instrument object
            config: Configuration dictionary
        """
        pass

    @abstractmethod
    def measure(self, instrument, target_value=None):
        """Take a measurement from the instrument.

        Args:
            instrument: VISA instrument object
            target_value: Optional target for error calculation

        Returns:
            float: Measured value
        """
        pass

    @abstractmethod
    def get_instruments(self):
        """Get list of supported instrument models.

        Returns:
            list: List of instrument model names
        """
        pass

    @abstractmethod
    def get_vendor_name(self):
        """Get the vendor name.

        Returns:
            str: Vendor name
        """
        pass

    def reset(self, instrument):
        """Reset the instrument to default state (optional override)."""
        try:
            instrument.write("*RST")
            instrument.write("*CLS")
            return True
        except Exception:
            return False

    def query_identity(self, instrument):
        """Query instrument identity (optional override)."""
        try:
            return instrument.query("*IDN?").strip()
        except Exception:
            return None