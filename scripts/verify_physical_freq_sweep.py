# File: scripts/verify_physical_freq_sweep.py
# Path: /d/Projects/autocalbridge/scripts/verify_physical_freq_sweep.py
# Purpose: Thin CLI wrapper for the reusable physical verification sweep.
#          Uses src.core.physical_verification.run_physical_freq_sweep.

import argparse
import sys

# Ensure project root is on sys.path when running directly or as module.
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.physical_verification import (
    run_physical_freq_sweep,
    PhysicalVerificationError,
)


def main():
    parser = argparse.ArgumentParser(
        description="Verify physical source/DUT frequency sweep."
    )
    parser.add_argument(
        "--source-id",
        default="rigol_dg2102_usb",
        help="Registry ID of source instrument",
    )
    parser.add_argument(
        "--dut-id",
        default="rtc1002-lab1",
        help="Registry ID of DUT instrument",
    )
    parser.add_argument(
        "--points",
        default="1000,10000,100000,1000000,5000000",
        help="Comma-separated frequency points in Hz",
    )
    parser.add_argument(
        "--settle-delay",
        type=float,
        default=1.5,
        help="Settle delay in seconds after each source change",
    )
    parser.add_argument(
        "--source-setup",
        default="SOUR1:FUNC SIN;SOUR1:VOLT 1;OUTP1 ON",
        help="Semicolon-separated source setup commands",
    )
    parser.add_argument(
        "--dut-setup",
        default="ACQ:STAT RUN;CHAN1:STAT ON;MEAS1:SOUR CH1;MEAS1:MAIN FREQ;MEAS1:ENAB ON",
        help="Semicolon-separated DUT setup commands",
    )
    parser.add_argument(
        "--source-freq-template",
        default="SOUR1:FREQ {value}",
        help="Source frequency command template with {value} placeholder",
    )
    parser.add_argument(
        "--dut-query",
        default="MEAS1:RES?",
        help="DUT query command for measurement result",
    )

    args = parser.parse_args()

    points = [float(x.strip()) for x in args.points.split(",") if x.strip()]
    source_setup = [x.strip() for x in args.source_setup.split(";") if x.strip()]
    dut_setup = [x.strip() for x in args.dut_setup.split(";") if x.strip()]

    try:
        results = run_physical_freq_sweep(
            source_id=args.source_id,
            dut_id=args.dut_id,
            points=points,
            settle_delay=args.settle_delay,
            source_setup_commands=source_setup,
            dut_setup_commands=dut_setup,
            source_freq_command_template=args.source_freq_template,
            dut_query_command=args.dut_query,
        )
    except PhysicalVerificationError as exc:
        print(f"Verification failed: {exc}")
        return 1

    print("\n--- Frequency sweep ---")
    print(f"{'Target (Hz)':>14} | {'Measured (Hz)':>14} | {'Status':<6}")
    print("-" * 44)

    all_ok = True
    for result in results:
        measured_str = f"{result.measured:.6e}" if result.measured is not None else "ERROR"
        if result.status != "OK":
            all_ok = False
        print(f"{result.target:>14.0f} | {measured_str:>14} | {result.status:<6}")

    print("-" * 44)
    if all_ok:
        print("Verification sweep passed.")
        return 0
    else:
        print("Verification sweep completed with failures.")
        return 1


if __name__ == "__main__":
    sys.exit(main())