# File: tests/test_utils/test_procedure_logging.py
# Path: /d/Projects/autocalbridge/tests/test_utils/test_procedure_logging.py
# Purpose: Unit tests for calibration procedure audit logging completeness.
#          Captures log records in memory so file-handler quirks cannot
#          mask missing traceability fields.

import logging
import unittest

from src.core.test_engine import TestEngine
from src.core.procedure_config import ProcedureConfig
from src.core.session_context import SessionContext, session_context
from src.utils.structured_logger import get_audit_logger


class _CaptureHandler(logging.Handler):
    """Collect emitted LogRecord objects for inspection."""

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class _SharedState:
    """Shared state so source write is visible to DUT read."""

    def __init__(self):
        self.source_value = None


class _FakeEndpoint:
    """Minimal endpoint backed by shared state."""

    def __init__(self, shared_state, is_source):
        self._shared_state = shared_state
        self._is_source = is_source

    def write(self, command):
        parts = command.strip().split()
        if len(parts) >= 2:
            try:
                value = float(parts[-1])
                if self._is_source:
                    self._shared_state.source_value = value
            except ValueError:
                pass

    def query(self, command):
        cmd = command.strip()
        if cmd.startswith("SYST:ERR"):
            return "0,\"No error\""
        if cmd.startswith("*ESR"):
            return "0"
        if cmd.startswith("READ?"):
            value = self._shared_state.source_value
            return str(value if value is not None else 0.0)
        if cmd.startswith("*OPC?"):
            return "1"
        return "0"


class TestProcedureAuditLogging(unittest.TestCase):
    """Audit log fields emitted by run_procedure."""

    def setUp(self):
        self.audit_logger = get_audit_logger()
        self.audit_logger.setLevel(logging.INFO)
        self.audit_logger.propagate = False

        self.handler = _CaptureHandler()
        self.audit_logger.addHandler(self.handler)
        self.addCleanup(self.audit_logger.removeHandler, self.handler)

    def _make_engine(self):
        shared = _SharedState()
        engine = TestEngine()
        engine.source = _FakeEndpoint(shared, is_source=True)
        engine.dut = _FakeEndpoint(shared, is_source=False)
        return engine

    def test_point_result_contains_traceability_fields(self):
        engine = self._make_engine()

        procedure = ProcedureConfig(
            procedure_id="proc-log-test",
            source_command_template="SOUR:VOLT {value}",
            dut_query_command="READ?",
            points=[1.0],
            tolerance=0.1,
        )

        ctx = SessionContext(
            session_id="session-log-test",
            operator="operator-log",
            supervisor="supervisor-log",
            instrument_roles={"source": "src-id", "dut": "dut-id"},
        )

        with session_context(ctx):
            engine.run_procedure(procedure, operator_name="operator-log")

        point_result_records = [
            r for r in self.handler.records
            if getattr(r, "event_type", None) == "point_result"
        ]
        self.assertTrue(point_result_records, "No point_result audit record emitted")

        record = point_result_records[0]

        self.assertEqual(record.procedure_id, "proc-log-test")
        self.assertEqual(record.target, 1.0)
        self.assertEqual(record.measured, 1.0)
        self.assertEqual(record.status, "PASS")
        self.assertAlmostEqual(record.error, 0.0, places=4)

    def test_procedure_complete_record_has_counts(self):
        engine = self._make_engine()

        procedure = ProcedureConfig(
            procedure_id="proc-log-complete",
            source_command_template="SOUR:VOLT {value}",
            dut_query_command="READ?",
            points=[1.0, 2.0],
            tolerance=0.1,
        )

        with session_context(SessionContext("s", "o")):
            engine.run_procedure(procedure)

        complete_records = [
            r for r in self.handler.records
            if getattr(r, "event_type", None) == "procedure_complete"
        ]
        self.assertTrue(complete_records)
        record = complete_records[0]
        self.assertEqual(record.passed, 2)
        self.assertEqual(record.total, 2)
        self.assertEqual(record.error_count, 0)


if __name__ == "__main__":
    unittest.main()