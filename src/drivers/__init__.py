# File: src/drivers/__init__.py
# Path: /autocalbridge/src/drivers/__init__.py
# Purpose: Exports available instrument drivers.

from src.drivers.base_driver import BaseDriver
from src.drivers.keysight import KeysightDriver
from src.drivers.tektronix import TektronixDriver
from src.drivers.rohde_schwarz import RohdeSchwarzDriver
from src.drivers.keithley import KeithleyDriver

__all__ = [
    "BaseDriver",
    "KeysightDriver",
    "TektronixDriver",
    "RohdeSchwarzDriver",
    "KeithleyDriver",
]

# Driver registry for dynamic loading
DRIVER_REGISTRY = {
    "Keysight": KeysightDriver,
    "Tektronix": TektronixDriver,
    "Rohde & Schwarz": RohdeSchwarzDriver,
    "Keithley": KeithleyDriver,
}

def get_driver(vendor_name):
    """Get the driver class for a given vendor."""
    return DRIVER_REGISTRY.get(vendor_name)