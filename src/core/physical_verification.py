# File: src/core/physical_verification.py
# Path: /d/Projects/autocalbridge/src/core/physical_verification.py
# Purpose: Reusable physical two-ended verification functions.
#          Contains:
#          - run_physical_freq_sweep
#          - run_waveform_spot_check
#          Defaults are tuned for Rigol DG2102 -> R&S RTC1002, but
#          functions accept optional arguments for future flexibility.

"""
Physical verification module.

This module contains reusable verification functions used by CLI and GUI.

Design principle:
    Build today's demo capability as a permanent, config-driven suite,
    not a throwaway script. Future instruments, waveforms, and measurement
    strategies should attach to these seams without rewriting core logic.
"""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from src.cli.instrument_commands import run_single_command


# ---------------------------------------------------------------------------
# Default values for current physical pair
# ---------------------------------------------------------------------------

DEFAULT_FREQUENCY_POINTS = [
    1000,
    10000,
    100000,
    1000000,
    5000000,
]

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

DEFAULT_SOURCE_FREQ_COMMAND_TEMPLATE = "SOUR1:FREQ {value}"
DEFAULT_DUT_QUERY_COMMAND = "MEAS1:RES?"

INVALID_MEASUREMENT_SENTINEL = 9.91e37

# Supported waveform types for spot check.
WAVEFORM_COMMANDS: Dict[str, str] = {
    "SIN": "SOUR1:FUNC SIN",
    "SQU": "SOUR1:FUNC SQU",
    "RAMP": "SOUR1:FUNC RAMP",
    "PULS": "SOUR1:FUNC PULS",
    "NOIS": "SOUR1:FUNC NOIS",
}


class PhysicalVerificationError(Exception):
    """Raised when physical verification cannot start or complete."""

    def __init__(self, message: str):
        super().__init__(message)


@dataclass
class VerificationPointResult:
    """
    One verification point result.

    Attributes:
        target: Expected frequency in Hz. May be None for stimulus-only.
        measured: DUT measurement in Hz. May be None if not measured.
        status: "OK", "FAIL", or "STIMULUS_SENT".
        error: Absolute error in Hz, or None if not applicable.
    """

    target: Optional[float]
    measured: Optional[float]
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
        points: Optional list of frequencies in Hz.
        settle_delay: Seconds to wait after each source change.
        source_setup_commands: Optional list of source setup write commands.
        dut_setup_commands: Optional list of DUT setup write commands.
        source_freq_command_template: Optional template with {value} placeholder.
        dut_query_command: Optional DUT query command.

    Returns:
        List[VerificationPointResult]: One result per frequency point.
    """
    points = points or DEFAULT_FREQUENCY_POINTS
    source_setup_commands = source_setup_commands or DEFAULT_SOURCE_SETUP_COMMANDS
    dut_setup_commands = dut_setup_commands or DEFAULT_DUT_SETUP_COMMANDS
    source_freq_command_template = (
        source_freq_command_template or DEFAULT_SOURCE_FREQ_COMMAND_TEMPLATE
    )
    dut_query_command = dut_query_command or DEFAULT_DUT_QUERY_COMMAND

    # Source setup.
    for cmd in source_setup_commands:
        ok, resp = run_single_command(source_id, cmd)
        if not ok:
            raise PhysicalVerificationError(f"Source setup failed: {cmd} -> {resp}")

    # DUT setup.
    for cmd in dut_setup_commands:
        ok, resp = run_single_command(dut_id, cmd)
        if not ok:
            raise PhysicalVerificationError(f"DUT setup failed: {cmd} -> {resp}")

    results: List[VerificationPointResult] = []

    for freq in points:
        source_command = source_freq_command_template.format(value=freq)
        ok_set, resp_set = run_single_command(source_id, source_command)
        if not ok_set:
            raise PhysicalVerificationError(
                f"Source frequency set failed for {freq}: {resp_set}"
            )

        # Set DUT timebase to show roughly 10 cycles across 12 divisions.
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


def run_waveform_spot_check(
    source_id: str,
    dut_id: str,
    waveform: str,
    frequency: Optional[float] = None,
    amplitude: float = 1.0,
    offset: float = 0.0,
    settle_delay: float = 1.5,
) -> VerificationPointResult:
    """
    Run a single waveform spot check.

    For Noise:
        - frequency is ignored
        - no frequency measurement is performed
        - status is "STIMULUS_SENT"

    For all other supported waveforms:
        - frequency, amplitude, offset are set on source
        - DUT frequency is measured and compared

    Args:
        source_id: Registry ID of source instrument.
        dut_id: Registry ID of DUT instrument.
        waveform: One of "SIN", "SQU", "RAMP", "PULS", "NOIS".
        frequency: Frequency in Hz. Required except for NOIS.
        amplitude: Amplitude in Vpp.
        offset: DC offset in V.
        settle_delay: Settle time in seconds after source changes.

    Returns:
        VerificationPointResult
    """
    waveform_key = waveform.strip().upper()

    if waveform_key not in WAVEFORM_COMMANDS:
        raise PhysicalVerificationError(
            f"Unsupported waveform '{waveform}'. "
            f"Supported: {sorted(WAVEFORM_COMMANDS.keys())}"
        )

    # Select waveform.
    ok, resp = run_single_command(source_id, WAVEFORM_COMMANDS[waveform_key])
    if not ok:
        raise PhysicalVerificationError(f"Waveform set failed: {resp}")

    # Set amplitude and offset.
    for cmd in [
        f"SOUR1:VOLT {amplitude}",
        f"SOUR1:VOLT:OFFS {offset}",
    ]:
        ok, resp = run_single_command(source_id, cmd)
        if not ok:
            raise PhysicalVerificationError(f"Source parameter failed: {cmd} -> {resp}")

    # Enable output.
    ok, resp = run_single_command(source_id, "OUTP1 ON")
    if not ok:
        raise PhysicalVerificationError(f"Output enable failed: {resp}")

    # Noise is stimulus-only.
    if waveform_key == "NOIS":
        time.sleep(settle_delay)
        return VerificationPointResult(
            target=None,
            measured=None,
            status="STIMULUS_SENT",
            error=None,
        )

    # Non-noise waveforms require frequency.
    if frequency is None:
        raise PhysicalVerificationError(
            f"Frequency is required for waveform '{waveform}'."
        )

    # Set frequency.
    ok, resp = run_single_command(source_id, f"SOUR1:FREQ {frequency}")
    if not ok:
        raise PhysicalVerificationError(f"Frequency set failed: {resp}")

    # Ensure DUT measurement setup for frequency.
    dut_setup_commands = [
        "ACQ:STAT RUN",
        "CHAN1:STAT ON",
        "MEAS1:SOUR CH1",
        "MEAS1:MAIN FREQ",
        "MEAS1:ENAB ON",
    ]
    for cmd in dut_setup_commands:
        ok, resp = run_single_command(dut_id, cmd)
        if not ok:
            raise PhysicalVerificationError(f"DUT setup failed: {cmd} -> {resp}")

    # Set DUT timebase for this frequency.
    period = 1.0 / frequency
    timebase = (10 * period) / 12.0
    run_single_command(dut_id, f"TIM:SCAL {timebase:.10g}")
    run_single_command(dut_id, "CHAN1:SCAL 0.2")

    time.sleep(settle_delay)

    ok_meas, resp_meas = run_single_command(dut_id, DEFAULT_DUT_QUERY_COMMAND)
    if not ok_meas:
        raise PhysicalVerificationError(
            f"DUT measurement failed for {frequency}: {resp_meas}"
        )

    try:
        measured = float(resp_meas)
    except ValueError as exc:
        raise PhysicalVerificationError(
            f"DUT returned non-numeric measurement for {frequency}: {resp_meas}"
        ) from exc

    if measured == INVALID_MEASUREMENT_SENTINEL:
        status = "FAIL"
        error = None
    else:
        status = "OK"
        error = abs(measured - frequency)

    return VerificationPointResult(
        target=frequency,
        measured=measured,
        status=status,
        error=error,
    )