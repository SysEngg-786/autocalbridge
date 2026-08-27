# File: tests/test_utils/test_session_config.py
# Path: /d/Projects/autocalbridge/tests/test_utils/test_session_config.py
# Purpose: Unit tests for session configuration loader, validator, and resolver.

import os
import tempfile
import unittest

import yaml

from src.core.session_config import load_session, SessionConfig
from src.core.session_validator import validate_session_data, SessionValidationError
from src.core.session_resolver import resolve_session, SessionResolutionError
from src.utils.instrument_registry import load_registry


class TestSessionValidator(unittest.TestCase):
    """Validation rules for session configuration."""

    def _valid_data(self):
        return {
            "session_id": "session-test-001",
            "label": "Test session",
            "operator": "Operator A",
            "supervisor": "Supervisor B",
            "source_id": "rtc1002-sim",
            "dut_id": "rtc1002-sim-dut",
            "procedure": "",
            "metadata": {"site": "Local Dev"},
        }

    def setUp(self):
        # Use the real project registry because it contains the test IDs.
        self.registry = load_registry()

    def test_valid_session_passes(self):
        validate_session_data(self._valid_data(), self.registry)

    def test_missing_required_field_fails(self):
        data = self._valid_data()
        del data["operator"]
        with self.assertRaises(SessionValidationError):
            validate_session_data(data, self.registry)

    def test_unknown_field_fails(self):
        data = self._valid_data()
        data["operator_name"] = "typo"
        with self.assertRaises(SessionValidationError):
            validate_session_data(data, self.registry)

    def test_unregistered_source_fails(self):
        data = self._valid_data()
        data["source_id"] = "does-not-exist"
        with self.assertRaises(SessionValidationError):
            validate_session_data(data, self.registry)

    def test_same_source_and_dut_fails(self):
        data = self._valid_data()
        data["dut_id"] = data["source_id"]
        with self.assertRaises(SessionValidationError):
            validate_session_data(data, self.registry)

    def test_metadata_must_be_mapping(self):
        data = self._valid_data()
        data["metadata"] = "not-a-map"
        with self.assertRaises(SessionValidationError):
            validate_session_data(data, self.registry)


class TestSessionLoader(unittest.TestCase):
    """Session file loading behavior."""

    def _write_session_file(self, data):
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
            encoding="utf-8",
        )
        yaml.safe_dump(data, tmp)
        tmp.close()
        return tmp.name

    def test_load_session_returns_normalized_object(self):
        data = {
            "session_id": "session-load-001",
            "operator": "Operator A",
            "source_id": "rtc1002-sim",
            "dut_id": "rtc1002-sim-dut",
        }
        path = self._write_session_file(data)
        try:
            session = load_session(path)
            self.assertIsInstance(session, SessionConfig)
            self.assertEqual(session.source_id, "rtc1002-sim")
            self.assertEqual(session.dut_id, "rtc1002-sim-dut")
        finally:
            os.unlink(path)

    def test_load_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_session("does-not-exist.yaml")


class TestSessionResolver(unittest.TestCase):
    """Session resolution against the instrument registry."""

    def setUp(self):
        self.registry = load_registry()

    def _make_session(self, source_id="rtc1002-sim", dut_id="rtc1002-sim-dut"):
        return SessionConfig(
            session_id="session-resolve-001",
            operator="Operator A",
            source_id=source_id,
            dut_id=dut_id,
        )

    def test_resolve_session_returns_entries(self):
        session = self._make_session()
        resolved = resolve_session(session, self.registry)
        self.assertEqual(resolved.source_entry.id, "rtc1002-sim")
        self.assertEqual(resolved.dut_entry.id, "rtc1002-sim-dut")

    def test_resolve_session_connection_strings(self):
        session = self._make_session()
        resolved = resolve_session(session, self.registry)
        self.assertEqual(resolved.source_entry.connection, "sim://rs_rtc1002")
        self.assertEqual(resolved.dut_entry.connection, "sim://rs_rtc1002")

    def test_resolve_missing_source_raises(self):
        session = self._make_session(source_id="missing-source")
        with self.assertRaises(SessionResolutionError):
            resolve_session(session, self.registry)

    def test_resolve_missing_dut_raises(self):
        session = self._make_session(dut_id="missing-dut")
        with self.assertRaises(SessionResolutionError):
            resolve_session(session, self.registry)


if __name__ == "__main__":
    unittest.main()