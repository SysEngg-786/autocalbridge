# File: src/core/session_context.py
# Path: /d/Projects/autocalbridge/src/core/session_context.py
# Purpose: Session identity and traceability context for AutoCalBridge.
#          Uses contextvars so CLI, GUI, CICD, and background tasks can
#          share one session identity without passing it through every
#          function signature.

"""
Session context.

AutoCalBridge calibration runs are traceability-critical. Every action must
be attributable to:

- session_id
- operator
- supervisor
- instrument assignments and roles
- start time

This module provides a contextvars-backed context object. The context is
implicitly available inside any call running under an active session, while
remaining isolated between sessions and threads.

Design decision reference:
    docs/dev/ACB_logging_session_architecture_decision.md
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass(frozen=True)
class SessionContext:
    """
    Immutable session identity snapshot.

    All fields are required except instrument_roles and extra. The frozen
    dataclass prevents accidental mutation after a session starts.
    """

    session_id: str
    operator: str
    supervisor: Optional[str] = None
    instrument_roles: Dict[str, str] = field(default_factory=dict)
    extra: Dict[str, str] = field(default_factory=dict)
    start_time: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        """
        Return a plain dictionary representation for structured logging.

        The start_time is rendered as ISO 8601 UTC because JSON log output
        must not depend on the local timezone of the host machine.
        """
        return {
            "session_id": self.session_id,
            "operator": self.operator,
            "supervisor": self.supervisor,
            "instrument_roles": dict(self.instrument_roles),
            "extra": dict(self.extra),
            "start_time": self.start_time.isoformat(),
        }


# ContextVar holding the active session context.
# The default is None because most application startup code runs outside
# any calibration session.
_current_session_context: ContextVar[Optional[SessionContext]] = ContextVar(
    "acb_session_context",
    default=None,
)


def set_session_context(ctx: SessionContext) -> None:
    """
    Activate a session context for the current execution context.

    Args:
        ctx: Immutable SessionContext instance.
    """
    _current_session_context.set(ctx)


def get_session_context() -> Optional[SessionContext]:
    """
    Return the currently active session context, if any.

    Returns:
        SessionContext or None when no session is active.
    """
    return _current_session_context.get()


def reset_session_context() -> None:
    """
    Clear the current session context.

    This must be called at the end of every session to prevent the next
    session from inheriting stale identity information.
    """
    _current_session_context.set(None)


@contextmanager
def session_context(ctx: SessionContext):
    """
    Context manager for running a block under an active session context.

    Usage:

        ctx = SessionContext(
            session_id="session-20260826-001",
            operator="operator-a",
            supervisor="supervisor-b",
            instrument_roles={"source": "keysight-source-1", "dut": "rtc1002-lab1"},
        )

        with session_context(ctx):
            run_calibration()

    The context is automatically cleared when the block exits, even if an
    exception occurs.
    """
    token = _current_session_context.set(ctx)
    try:
        yield ctx
    finally:
        _current_session_context.reset(token)