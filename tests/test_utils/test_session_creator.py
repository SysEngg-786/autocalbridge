# File: tests/test_utils/test_session_creator.py
# Path: /d/Projects/autocalbridge/tests/test_utils/test_session_creator.py
# Purpose: Unit tests for the session_creator module.
#          Verifies automatic session file creation and validation.

import os
import tempfile
import unittest

import src.core.session_creator as session_creator
from src.core.session_config import load_session


class TestSessionCreator(unittest.TestCase):
    """Session creation behavior."""

    def setUp(self):
        # Redirect sessions directory to a temporary location for isolation.
        self.original_sessions_dir = session_creator.SESSIONS_DIR
        self.temp_dir = tempfile.TemporaryDirectory()
        session_creator.SESSIONS_DIR = self.temp_dir.name

    def tearDown(self):
        session_creator.SESSIONS_DIR = self.original_sessions_dir
        self.temp_dir.cleanup()

    def _valid_kwargs(self, **overrides):
        kwargs = {
            "operator": "Operator A",
            "source_id": "keysight_source",
            "dut_id": "keysight_34461a",
            "procedure": "keysight_source_to_34461a",
            "supervisor": "Supervisor B",
            "label": "Unit test session",
            "metadata": {"site": "Local Dev"},
            "session_id": "ACB-test-session",
        }
        kwargs.update(overrides)
        return kwargs

    def test_create_session_valid(self):
        session_file = session_creator.create_session(**self._valid_kwargs())
        self.assertTrue(os.path.isfile(session_file))
        session = load_session(session_file)
        self.assertEqual(session.session_id, "ACB-test-session")
        self.assertEqual(session.operator, "Operator A")
        self.assertEqual(session.source_id, "keysight_source")
        self.assertEqual(session.dut_id, "keysight_34461a")
        self.assertEqual(session.procedure, "keysight_source_to_34461a")

    def test_missing_operator_raises(self):
        with self.assertRaises(session_creator.SessionCreationError):
            session_creator.create_session(
                **self._valid_kwargs(operator="")
            )

    def test_same_source_and_dut_raises(self):
        with self.assertRaises(session_creator.SessionCreationError):
            session_creator.create_session(
                **self._valid_kwargs(
                    source_id="keysight_source",
                    dut_id="keysight_source",
                )
            )

    def test_unregistered_source_raises(self):
        with self.assertRaises(session_creator.SessionCreationError):
            session_creator.create_session(
                **self._valid_kwargs(source_id="does-not-exist")
            )

    def test_invalid_procedure_raises(self):
        with self.assertRaises(session_creator.SessionCreationError):
            session_creator.create_session(
                **self._valid_kwargs(procedure="does-not-exist")
            )

    def test_metadata_not_mapping_raises(self):
        with self.assertRaises(session_creator.SessionCreationError):
            session_creator.create_session(
                **self._valid_kwargs(metadata="not-a-mapping")
            )

    def test_generated_session_id_is_unique(self):
        kwargs = self._valid_kwargs()
        kwargs.pop("session_id")
        file1 = session_creator.create_session(**kwargs)
        file2 = session_creator.create_session(**kwargs)
        self.assertNotEqual(
            os.path.basename(file1),
            os.path.basename(file2),
        )


if __name__ == "__main__":
    unittest.main()
