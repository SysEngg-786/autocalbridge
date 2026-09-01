# File: src/core/physical_verification.py
# Path: /d/Projects/autocalbridge/src/core/physical_verification.py
# Purpose: Reusable physical two-ended frequency verification sweep.
#          Currently defaulted for Rigol DG2102 -> R&S RTC1002, but the
#          function accepts optional arguments so user-defined verification
#          can be added later without rewriting core logic.

"""
Physical verification sweep.

This module extracts the proven physical frequency sweep logic from the CLI
script into a reusable function. It is used by:

- scripts/verify_physical_freq_sweep.py  (CLI)
- GUI verification button later

The default values are tuned for the current concept-validation setup:

    Source: Rigol DG2102 via USB
    DUT:    R&S RTC1002 via LAN

No GUI or CLI dependencies exist in this module. It calls the existing
command layer through run_single_command().
"""

import time
from dataclasses import dataclass
from typing import List, Optional

from src.cli.instrument_commands import run_single_command


# Default verification points in Hz.
DEFAULT_FREQUENCY_POINTS = [
    1000,
    10000,
    100000,
    1000000,
    5000000,
]

# Default setup commands for the current physical pair.
DEFAULT_SOURCE_SETUP_COMMANDS = [
    "SOUR1:FUNC SIN",
    "SOUR1:VOLT 1",
    "OUTP1 ON",
]

DEFAULT_DUT_SETUP_COMMANDS = [
    "ACQ:STAT RUN",
    "CHAN1:STAT ON",
    "MEAS1:SOUR CH1",
    "MEAS1:MAIN FREQ",
    "MEAS1:ENAB ON",
]

# Default source command template and DUT query.
DEFAULT_SOURCE_FREQ_COMMAND_TEMPLATE = "SOUR1:FREQ {value}"
DEFAULT_DUT_QUERY_COMMAND = "MEAS1:RES?"

# Sentinel value used by RTC when a measurement is unavailable.
INVALID_MEASUREMENT_SENTINEL = 9.91e37


class PhysicalVerificationError(Exception):
    """Raised when physical verification cannot start or complete."""

    def __init__(self, message: str):
        super().__init__(message)


@dataclass
class VerificationPointResult:
    """
    One verification point result.

    Attributes:
        target: Expected frequency in Hz.
        measured: DUT measurement in Hz. May be the invalid sentinel.
        status: "OK" or "FAIL".
        error: Absolute error in Hz, or None if measurement invalid.
    """

    target: float
    measured: float
    status: str
    error: Optional[float] = None


def run_physical_freq_sweep(
    source_id: str,
    dut_id: str,
    points: Optional[List[float]] = None,
    settle_delay: float = 1.5,
    source_setup_commands: Optional[List[str]] = None,
    dut_setup_commands: Optional[List[str]] = None,
    source_freq_command_template: Optional[str] = None,
    dut_query_command: Optional[str] = None,
) -> List[VerificationPointResult]:
    """
    Run a physical two-ended frequency verification sweep.

    Args:
        source_id: Registry ID of the source instrument.
        dut_id: Registry ID of the DUT instrument.
        points: Optional list of frequencies in Hz. If None, defaults are used.
        settle_delay: Seconds to wait after each source change.
        source_setup_commands: Optional list of source setup write commands.
        dut_setup_commands: Optional list of DUT setup write commands.
        source_freq_command_template: Optional template with {value} placeholder.
        dut_query_command: Optional DUT query command.

    Returns:
        List[VerificationPointResult]: One result per frequency point.

    Raises:
        PhysicalVerificationError: If setup commands fail.
    """
    # Apply defaults where arguments are not supplied. This is the seam for
    # future user-defined verification without changing the function core.
    points = points or DEFAULT_FREQUENCY_POINTS
    source_setup_commands = source_setup_commands or DEFAULT_SOURCE_SETUP_COMMANDS
    dut_setup_commands = dut_setup_commands or DEFAULT_DUT_SETUP_COMMANDS
    source_freq_command_template = (
        source_freq_command_template or DEFAULT_SOURCE_FREQ_COMMAND_TEMPLATE
    )
    dut_query_command = dut_query_command or DEFAULT_DUT_QUERY_COMMAND

    # Run source setup once.
    for cmd in source_setup_commands:
        ok, resp = run_single_command(source_id, cmd)
        if not ok:
            raise PhysicalVerificationError(
                f"Source setup failed: {cmd} -> {resp}"
            )

    # Run DUT setup once.
    for cmd in dut_setup_commands:
        ok, resp = run_single_command(dut_id, cmd)
        if not ok:
            raise PhysicalVerificationError(
                f"DUT setup failed: {cmd} -> {resp}"
            )

    results: List[VerificationPointResult] = []

    # Sweep each frequency point.
    for freq in points:
        source_command = source_freq_command_template.format(value=freq)

        ok_set, resp_set = run_single_command(source_id, source_command)
        if not ok_set:
            raise PhysicalVerificationError(
                f"Source frequency set failed for {freq}: {resp_set}"
            )

        # Set DUT timebase to show about 10 cycles across 12 divisions.
        # This is required by the RTC1002 automatic frequency measurement.
        period = 1.0 / freq
        timebase = (10 * period) / 12.0
        run_single_command(dut_id, f"TIM:SCAL {timebase:.10g}")
        run_single_command(dut_id, "CHAN1:SCAL 0.2")

        time.sleep(settle_delay)

        ok_meas, resp_meas = run_single_command(dut_id, dut_query_command)

        if not ok_meas:
            raise PhysicalVerificationError(
                f"DUT measurement failed for {freq}: {resp_meas}"
            )

        try:
            measured = float(resp_meas)
        except ValueError as exc:
            raise PhysicalVerificationError(
                f"DUT returned non-numeric measurement for {freq}: {resp_meas}"
            ) from exc

        if measured == INVALID_MEASUREMENT_SENTINEL:
            status = "FAIL"
            error = None
        else:
            status = "OK"
            error = abs(measured - freq)

        results.append(
            VerificationPointResult(
                target=freq,
                measured=measured,
                status=status,
                error=error,
            )
        )

    return results