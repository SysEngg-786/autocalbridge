# File: tests/test_utils/test_safety_limits.py
# Path: /d/Projects/autocalbridge/tests/test_utils/test_safety_limits.py
# Purpose: Unit tests for safety limit merging and TestEngine safety checks.

import unittest

from src.core.test_engine import TestEngine
from src.core.session_runner import _merge_safety_limits, SessionRunnerError


class TestSafetyLimitMerge(unittest.TestCase):
    """Profile and registry safety limit merging rules."""

    def test_registry_narrower_limits_are_accepted(self):
        profile = {"SOUR:VOLT": {"min": 0.0, "max": 10.0}}
        registry = {"SOUR:VOLT": {"min": 1.0, "max": 5.0}}
        merged = _merge_safety_limits(profile, registry)
        self.assertEqual(merged["SOUR:VOLT"], {"min": 1.0, "max": 5.0})

    def test_registry_wider_min_is_rejected(self):
        profile = {"SOUR:VOLT": {"min": 0.0, "max": 10.0}}
        registry = {"SOUR:VOLT": {"min": -1.0, "max": 5.0}}
        with self.assertRaises(SessionRunnerError):
            _merge_safety_limits(profile, registry)

    def test_registry_wider_max_is_rejected(self):
        profile = {"SOUR:VOLT": {"min": 0.0, "max": 10.0}}
        registry = {"SOUR:VOLT": {"min": 1.0, "max": 11.0}}
        with self.assertRaises(SessionRunnerError):
            _merge_safety_limits(profile, registry)

    def test_new_registry_root_is_accepted(self):
        profile = {"SOUR:VOLT": {"min": 0.0, "max": 10.0}}
        registry = {"SOUR:CURR": {"min": 0.0, "max": 1.0}}
        merged = _merge_safety_limits(profile, registry)
        self.assertEqual(merged["SOUR:CURR"], {"min": 0.0, "max": 1.0})


class TestSourceSafetyCheck(unittest.TestCase):
    """TestEngine source safety limit enforcement."""

    def setUp(self):
        self.engine = TestEngine()
        self.engine.set_source_safety_limits(
            {"SOUR:VOLT": {"min": 0.0, "max": 10.0}}
        )

    def test_value_within_limits_passes(self):
        self.assertTrue(
            self.engine._check_source_safety("SOUR:VOLT 5", 5.0)
        )

    def test_value_below_min_fails(self):
        self.assertFalse(
            self.engine._check_source_safety("SOUR:VOLT -1", -1.0)
        )

    def test_value_above_max_fails(self):
        self.assertFalse(
            self.engine._check_source_safety("SOUR:VOLT 11", 11.0)
        )


if __name__ == "__main__":
    unittest.main()