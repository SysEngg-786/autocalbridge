# File: scripts/demo.py
# Path: /d/Projects/autocalbridge/scripts/demo.py
# Purpose: Demo script showing session-driven, procedure-driven two-ended
#          calibration. No hardcoded endpoints, points, or tolerance.

import sys
import os

# Add the project root to Python path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.session_runner import run_session, SessionRunnerError
from src.core.report_generator import ReportGenerator
from src.utils.logger import setup_logging


def main():
    """Run the two-ended calibration demo from a session file."""
    print("\n" + "=" * 60)
    print("AutoCalBridge Demo - Session + Procedure-Driven Calibration")
    print("=" * 60)

    # Setup logging using the current logger utility.
    setup_logging()

    # The session file is the single input that defines:
    # - operator/supervisor
    # - source and DUT instruments by registry ID
    # - procedure reference
    # The procedure file defines points, tolerance, source command template,
    # and DUT query command. No hardcoded run data remains here.
    session_file = "config/sessions/session-keysight-virtual.yaml"

    print(f"\n[1] Session file: {session_file}")

    print("\n[2] Running session + procedure-driven calibration...")
    try:
        results, errors = run_session(session_file)
    except SessionRunnerError as exc:
        print(f"    Session run failed: {exc}")
        return 1

    print(f"\n[3] Test completed: {len(results)} measurements")

    if errors:
        print(f"\n[!] Errors encountered: {len(errors)}")
        for err in errors:
            print(f"    {err['instrument']}: {err['message']}")

    print("\n[4] Generating report...")
    report_generator = ReportGenerator()
    report_path = report_generator.generate_report(results, prefix="Demo")
    print(f"    Report saved to: {report_path}")

    summary = report_generator.generate_summary(results)
    print(f"\n[5] Summary:")
    print(f"    Total Tests: {summary['total']}")
    print(f"    Passed: {summary['passed']}")
    print(f"    Failed: {summary['failed']}")
    print(f"    Pass Rate: {summary['pass_rate']}%")

    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())