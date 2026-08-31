# File: scripts/verify_physical_freq_sweep.py
# Path: /d/Projects/autocalbridge/scripts/verify_physical_freq_sweep.py
# Purpose: Reusable physical two-ended frequency sweep verification.
#          Sets source frequency and reads DUT measurement using existing
#          ACB CLI command functions. No session/procedure files required.

import argparse
import sys
import time

# Ensure project root is on sys.path when running directly or as module.
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.cli.instrument_commands import run_single_command


def run_setup_commands(entry_id, commands, label):
    """Run a list of write commands on an instrument entry."""
    print(f"--- {label} setup ---")
    for cmd in commands:
        ok, resp = run_single_command(entry_id, cmd)
        if not ok:
            print(f"  FAIL {cmd}: {resp}")
            return False
        print(f"  OK   {cmd}")
    return True


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
        "--dut-query",
        default="MEAS1:RES?",
        help="DUT query command for measurement result",
    )

    args = parser.parse_args()

    points = [float(x.strip()) for x in args.points.split(",") if x.strip()]
    source_setup = [x.strip() for x in args.source_setup.split(";") if x.strip()]
    dut_setup = [x.strip() for x in args.dut_setup.split(";") if x.strip()]

    # Run setup once before sweep.
    if not run_setup_commands(args.source_id, source_setup, "Source"):
        print("Source setup failed. Aborting.")
        return 1
    if not run_setup_commands(args.dut_id, dut_setup, "DUT"):
        print("DUT setup failed. Aborting.")
        return 1

    print("\n--- Frequency sweep ---")
    print(f"{'Target (Hz)':>14} | {'Measured (Hz)':>14} | {'Status':<6}")
    print("-" * 44)

    all_ok = True
    for freq in points:
        # Set source frequency.
        ok_set, resp_set = run_single_command(
            args.source_id, f"SOUR1:FREQ {freq}"
        )
        if not ok_set:
            print(f"Source frequency set failed for {freq}: {resp_set}")
            all_ok = False
            continue

        # Set DUT timebase to show about 10 cycles across 12 divisions.
        period = 1.0 / freq
        timebase = (10 * period) / 12.0
        run_single_command(args.dut_id, f"TIM:SCAL {timebase:.10g}")
        run_single_command(args.dut_id, "CHAN1:SCAL 0.2")

        time.sleep(args.settle_delay)

        ok_meas, resp_meas = run_single_command(args.dut_id, args.dut_query)
        if ok_meas:
            try:
                measured = float(resp_meas)
                status = "OK" if measured != 9.91e37 else "FAIL"
                if status == "FAIL":
                    all_ok = False
                print(f"{freq:>14.0f} | {measured:>14.6e} | {status:<6}")
            except Exception:
                print(f"{freq:>14.0f} | {resp_meas:>14} | FAIL")
                all_ok = False
        else:
            print(f"{freq:>14.0f} | {'ERROR':>14} | FAIL")
            all_ok = False

    print("-" * 44)
    if all_ok:
        print("Verification sweep passed.")
        return 0
    else:
        print("Verification sweep completed with failures.")
        return 1


if __name__ == "__main__":
    sys.exit(main())