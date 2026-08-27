# File: tests/test_utils/test_instrument_registry.py
# Path: /d/Projects/autocalbridge/tests/test_utils/test_instrument_registry.py
# Purpose: Unit tests for the instrument registry loader and validator.

import os
import tempfile
import unittest

import yaml

from src.utils.instrument_registry import load_registry
from src.utils.registry_validator import validate_registry, RegistryValidationError


class TestRegistryValidator(unittest.TestCase):
    """Validation rules for the instrument registry."""

    def _base_data(self):
        """Return a minimal valid registry dictionary."""
        return {
            "instruments": [
                {
                    "id": "dev1",
                    "profile": "rs_rtc1002.yaml",
                    "kind": "virtual",
                    "display_name": "Dev One",
                    "connection": "sim://rs_rtc1002",
                    "role": "any",
                    "safety_limits": {},
                    "metadata": {},
                }
            ]
        }

    def test_valid_data_passes(self):
        """A correctly formed entry should validate without error."""
        data = self._base_data()
        # Use the real project profile directory so the profile check passes.
        validate_registry(data, profile_dir="config/instruments")

    def test_duplicate_id_fails(self):
        """Duplicate IDs must be rejected."""
        data = self._base_data()
        second = dict(data["instruments"][0])
        second["id"] = "dev1"
        data["instruments"].append(second)

        with self.assertRaises(RegistryValidationError) as ctx:
            validate_registry(data, profile_dir="config/instruments")
        self.assertIn("duplicate id", str(ctx.exception))

    def test_missing_profile_fails(self):
        """A profile that does not exist must be rejected."""
        data = self._base_data()
        data["instruments"][0]["profile"] = "does_not_exist.yaml"

        with self.assertRaises(RegistryValidationError):
            validate_registry(data, profile_dir="config/instruments")

    def test_invalid_kind_fails(self):
        """Only physical and virtual kinds are allowed."""
        data = self._base_data()
        data["instruments"][0]["kind"] = "cloud"

        with self.assertRaises(RegistryValidationError):
            validate_registry(data, profile_dir="config/instruments")

    def test_physical_with_sim_scheme_fails(self):
        """A physical instrument must not use sim:// connection."""
        data = self._base_data()
        data["instruments"][0]["kind"] = "physical"
        data["instruments"][0]["connection"] = "sim://rs_rtc1002"

        with self.assertRaises(RegistryValidationError):
            validate_registry(data, profile_dir="config/instruments")

    def test_unknown_field_fails(self):
        """Unknown fields must be rejected to catch typos."""
        data = self._base_data()
        data["instruments"][0]["connetion"] = "sim://rs_rtc1002"  # misspelled

        with self.assertRaises(RegistryValidationError):
            validate_registry(data, profile_dir="config/instruments")


class TestRegistryLoader(unittest.TestCase):
    """Loader behavior using a temporary registry file."""

    def _write_registry(self, data):
        """Write test data to a temporary YAML file and return the path."""
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
            encoding="utf-8",
        )
        yaml.safe_dump(data, tmp)
        tmp.close()
        return tmp.name

    def test_load_registry_returns_ids(self):
        """The loader should return normalized entries with stable IDs."""
        data = {
            "instruments": [
                {
                    "id": "dev1",
                    "profile": "rs_rtc1002.yaml",
                    "kind": "virtual",
                    "display_name": "Dev One",
                    "connection": "sim://rs_rtc1002",
                    "role": "any",
                    "safety_limits": {},
                    "metadata": {},
                }
            ]
        }
        registry_file = self._write_registry(data)
        try:
            registry = load_registry(registry_file=registry_file)
            self.assertEqual(registry.ids(), ["dev1"])
            entry = registry.get("dev1")
            self.assertEqual(entry.kind, "virtual")
            self.assertEqual(entry.connection, "sim://rs_rtc1002")
        finally:
            os.unlink(registry_file)

    def test_missing_file_raises(self):
        """A missing registry file must raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            load_registry(registry_file="does_not_exist.yaml")


if __name__ == "__main__":
    unittest.main()