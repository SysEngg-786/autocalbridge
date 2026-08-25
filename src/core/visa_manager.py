# File: src/core/visa_manager.py
# Path: /autocalbridge/src/core/visa_manager.py
# Purpose: Manages VISA connections to instruments with multi-session support.

import pyvisa
import pyvisa.errors


class VisaManager:
    """Manages VISA resources and instrument connections.

    DESIGN NOTE: Supports multiple simultaneous VISA sessions
    for two-ended (source + DUT) calibration.
    """

    def __init__(self):
        """Initialize the VISA resource manager."""
        self.rm = None
        self._resources = []  # Track open resources for cleanup
        self.instruments = {}  # Store instrument references by address

    def connect(self):
        """Initialize the VISA resource manager."""
        try:
            self.rm = pyvisa.ResourceManager()
            return self.rm
        except pyvisa.errors.VisaError as e:
            print(f"Failed to initialize VISA: {e}")
            return None

    def list_resources(self):
        """List all available VISA resources."""
        if not self.rm:
            self.connect()
        try:
            resources = self.rm.list_resources()
            return resources
        except pyvisa.errors.VisaError as e:
            print(f"Failed to list resources: {e}")
            return []

    def open_instrument(self, address, timeout=5000, tag=None):
        """Open a connection to an instrument.

        Args:
            address: VISA address string
            timeout: Timeout in milliseconds (default: 5000)
            tag: Optional identifier for this instrument (source/dut)

        Returns:
            instrument object or None on failure
        """
        if not self.rm:
            self.connect()
        try:
            instrument = self.rm.open_resource(address)
            instrument.timeout = timeout
            self._resources.append(instrument)

            # Store by tag if provided, otherwise by address
            key = tag if tag else address
            self.instruments[key] = instrument

            return instrument
        except pyvisa.errors.VisaError as e:
            print(f"Failed to open instrument at {address}: {e}")
            return None

    def get_instrument(self, tag):
        """Get an instrument by its tag."""
        return self.instruments.get(tag)

    def close_instrument(self, tag):
        """Close a specific instrument by tag."""
        if tag in self.instruments:
            try:
                self.instruments[tag].close()
                del self.instruments[tag]
                return True
            except Exception as e:
                print(f"Error closing instrument {tag}: {e}")
                return False
        return False

    def close(self):
        """Close all instrument connections and the resource manager."""
        # Close all instruments
        for instrument in self._resources:
            try:
                instrument.close()
            except:
                pass
        self._resources.clear()
        self.instruments.clear()

        # Close resource manager
        if self.rm:
            try:
                self.rm.close()
            except:
                pass
            self.rm = None

    def close_all(self):
        """Alias for close() for backward compatibility."""
        self.close()