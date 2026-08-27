# File: tests/test_utils/test_procedure_config.py
# Path: /d/Projects/autocalbridge/tests/test_utils/test_procedure_config.py
# Purpose: Unit tests for procedure configuration loader and validator.

import os
import tempfile
import unittest

import yaml

from src.core.procedure_config import load_procedure, ProcedureConfig
from src.core.procedure_validator import validate_procedure_data, ProcedureValidationError


class TestProcedureValidator(unittest.TestCase):
    """Validation rules for procedure configuration."""

    def _valid_data(self):
        return {
            "procedure_id": "proc-test-001",
            "label": "Test procedure",
            "source_command_template": "SOUR:VOLT {value}",
            "dut_query_command": "READ?",
            "points": [1.0, 2.5, 5.0],
            "tolerance": 0.005,
            "metadata": {"purpose": "test"},
        }

    def test_valid_procedure_passes(self):
        validate_procedure_data(self._valid_data())

    def test_missing_required_field_fails(self):
        data = self._valid_data()
        del data["dut_query_command"]
        with self.assertRaises(ProcedureValidationError):
            validate_procedure_data(data)

    def test_unknown_field_fails(self):
        data = self._valid_data()
        data["measure_command"] = "MEAS?"
        with self.assertRaises(ProcedureValidationError):
            validate_procedure_data(data)

    def test_points_must_be_nonempty_list(self):
        data = self._valid_data()
        data["points"] = []
        with self.assertRaises(ProcedureValidationError):
            validate_procedure_data(data)

    def test_points_must_be_numbers(self):
        data = self._valid_data()
        data["points"] = [1.0, "2.5"]
        with self.assertRaises(ProcedureValidationError):
            validate_procedure_data(data)

    def test_tolerance_must_be_positive_number(self):
        data = self._valid_data()
        data["tolerance"] = 0
        with self.assertRaises(ProcedureValidationError):
            validate_procedure_data(data)


class TestProcedureLoader(unittest.TestCase):
    """Procedure file loading behavior."""

    def _write_procedure_file(self, data):
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
            encoding="utf-8",
        )
        yaml.safe_dump(data, tmp)
        tmp.close()
        return tmp.name

    def test_load_procedure_returns_normalized_object(self):
        data = {
            "procedure_id": "proc-load-001",
            "source_command_template": "SOUR:VOLT {value}",
            "dut_query_command": "READ?",
            "points": [1.0, 2.5],
            "tolerance": 0.005,
        }
        path = self._write_procedure_file(data)
        try:
            procedure = load_procedure(path)
            self.assertIsInstance(procedure, ProcedureConfig)
            self.assertEqual(procedure.points, [1.0, 2.5])
            self.assertEqual(procedure.tolerance, 0.005)
        finally:
            os.unlink(path)

    def test_load_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_procedure("does-not-exist.yaml")


if __name__ == "__main__":
    unittest.main()