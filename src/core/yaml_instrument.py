# File: src/core/yaml_instrument.py
# Path: /autocalbridge/src/core/yaml_instrument.py
# Purpose: YAML-based instrument emulator.

import os
import random
import yaml
from src.core.test_instrument import MockInstrument
from src.core.simulation_context import SimulationContext


class YAMLInstrument(MockInstrument):
    """Instrument emulator that loads behavior from YAML files."""

    def __init__(self, yaml_path=None, config_dict=None, simulation_context=None):
        """Initialize from YAML file or dictionary.

        Args:
            yaml_path: Path to a YAML instrument profile.
            config_dict: Optional dictionary-based profile.
            simulation_context: Optional shared SimulationContext.
                This belongs to the simulator layer. ACB never sees it.
        """
        self._responses = {}
        self._write_commands = []
        self._response_dynamic = []

        # Simulator-layer hidden link between source and DUT.
        self._simulation_context = (
            simulation_context if simulation_context is not None else None
        )

        if yaml_path:
            self._load_from_yaml(yaml_path)
        elif config_dict:
            self._load_from_dict(config_dict)
        else:
            raise ValueError("Either yaml_path or config_dict must be provided")

        # Initialize parent with values from config
        vendor = self._config.get('vendor', 'Unknown')
        model = self._config.get('model', 'Unknown')
        serial = self._config.get('serial', 'MOCK12345')
        mode = self._config.get('mode', 'dut')

        super().__init__(vendor, model, serial, mode)

        # Apply YAML-specific settings
        self._dut_value = self._config.get('default_target', 1.0)
        self._noise = self._config.get('noise', 0.001)
        self._offset = self._config.get('offset', 0.0)
        self._fail_rate = self._config.get('fail_rate', 0.0)

        # Source-specific
        if mode == 'source':
            self._source_range = self._config.get('source_range', 10.0)

        # Override idn if provided
        if 'idn' in self._config:
            self.idn = self._config['idn']

    def _load_from_yaml(self, yaml_path):
        """Load configuration from YAML file."""
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")

        with open(yaml_path, 'r') as f:
            self._config = yaml.safe_load(f)

        self._parse_config()

    def _load_from_dict(self, config_dict):
        """Load configuration from dictionary."""
        self._config = config_dict
        self._parse_config()

    def _parse_config(self):
        """Parse the configuration into internal structures."""
        self._responses = self._config.get('responses', {})
        self._write_commands = self._config.get('write_commands', [])

        # Identify dynamic responses (where value is None)
        self._response_dynamic = [cmd for cmd, val in self._responses.items() if val is None]

    def _handle_source_command(self, cmd, full_cmd):
        """Handle query commands in source mode with YAML support."""
        # Check for dynamic responses first
        if cmd in self._response_dynamic:
            return self._generate_measurement()

        # Check YAML-defined responses
        if cmd in self._responses:
            return self._responses[cmd]

        # Handle source-specific dynamic responses
        if cmd.startswith("SOUR:VOLT?"):
            return f"{self._source_value:.6f}"
        if cmd.startswith("SOUR:RANG?"):
            return f"{self._source_range:.6f}"

        return ""

    def _handle_source_write(self, cmd, full_cmd):
        """Handle write commands in source mode with YAML support."""
        # Check if this is a defined write command
        for write_cmd in self._write_commands:
            if full_cmd.startswith(write_cmd):
                # Parse value if applicable
                if "SOUR:VOLT" in cmd:
                    try:
                        parts = full_cmd.split()
                        if len(parts) >= 2:
                            self._source_value = float(parts[1])
                    except ValueError:
                        pass
                if "SOUR:RANG" in cmd:
                    try:
                        parts = full_cmd.split()
                        if len(parts) >= 2:
                            self._source_range = float(parts[1])
                    except ValueError:
                        pass
                break

        # Handle standard commands
        super()._handle_source_write(cmd, full_cmd)

        # After the value is settled, publish the latest source voltage into
        # the shared simulation context so a DUT simulator can read it later.
        if self._simulation_context is not None and "SOUR:VOLT" in cmd:
            self._simulation_context.set_value("voltage", self._source_value)

    def _handle_dut_command(self, cmd, full_cmd):
        """Handle query commands in DUT mode with YAML support."""
        # Check for dynamic responses first
        if cmd in self._response_dynamic:
            return self._generate_measurement()

        # Check YAML-defined responses
        if cmd in self._responses:
            return self._responses[cmd]

        return super()._handle_dut_command(cmd, full_cmd)

    def _handle_dut_write(self, cmd, full_cmd):
        """Handle write commands in DUT mode with YAML support."""
        # Check if this is a defined write command
        for write_cmd in self._write_commands:
            if full_cmd.startswith(write_cmd):
                break

        super()._handle_dut_write(cmd, full_cmd)

    def _generate_measurement(self):
        """Generate a simulated measurement value."""
        if self._simulate_error or self._force_error:
            return "READ FAILED"

        # If a shared simulation context is present, use the simulated source
        # voltage as the measurement target. Otherwise fall back to the DUT's
        # own configured default target.
        if self._simulation_context is not None:
            target = self._simulation_context.get_value(
                "voltage",
                self._dut_value,
            )
        else:
            target = self._dut_value

        target = target + self._offset
        value = target + random.gauss(0, self._noise)

        if random.random() < self._fail_rate:
            return "READ FAILED"

        return f"{value:.6f}"


def load_instrument(yaml_path, simulation_context=None):
    """Load an instrument from a YAML file.

    Args:
        yaml_path: Path to the YAML instrument profile.
        simulation_context: Optional shared SimulationContext for source-DUT
            simulator coupling.
    """
    return YAMLInstrument(
        yaml_path=yaml_path,
        simulation_context=simulation_context,
    )