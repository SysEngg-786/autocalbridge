# File: src/utils/config_loader.py
# Path: /autocalbridge/src/utils/config_loader.py
# Purpose: Load configuration from config.json with fallback defaults.

import os
import json

DEFAULT_CONFIG = {
    "visa_address": "TCPIP0::localhost::hislip0::INSTR",
    "vendor": "Keysight",
    "instrument_model": "34461A",
    "calibration_points_volts": [1.000, 5.000],
    "pass_tolerance_volts": 0.005,
    "operator_name": "Default_Operator",
    "report_directory": "Reports",
    "logging_level": "INFO",
    "connection_mode": "local"
}

CONFIG_FILE = "config.json"


def load_config():
    """Load configuration from config.json with fallback defaults."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                user_config = json.load(f)
            merged_config = DEFAULT_CONFIG.copy()
            merged_config.update(user_config)
            return merged_config
        except (json.JSONDecodeError, IOError) as e:
            print(f"Config error: {e}. Using defaults.")
            return DEFAULT_CONFIG.copy()
    else:
        print(f"config.json not found. Using defaults.")
        return DEFAULT_CONFIG.copy()


def save_config(config):
    """Save configuration to config.json."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except IOError as e:
        print(f"Failed to save config: {e}")
        return False