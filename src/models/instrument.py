# File: src/models/instrument.py
# Path: /autocalbridge/src/models/instrument.py
# Purpose: Data model for instrument information.

class Instrument:
    """Data model for an instrument."""

    def __init__(self, vendor, model, visa_address=None, connection_mode="network"):
        self.vendor = vendor
        self.model = model
        self.visa_address = visa_address
        self.connection_mode = connection_mode  # "local" or "network"
        self.is_connected = False
        self.identity = None

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "vendor": self.vendor,
            "model": self.model,
            "visa_address": self.visa_address,
            "connection_mode": self.connection_mode,
            "is_connected": self.is_connected,
            "identity": self.identity
        }

    def __repr__(self):
        return f"Instrument(vendor={self.vendor}, model={self.model}, address={self.visa_address})"