# File: scripts/demo.py
# Path: /autocalbridge/scripts/demo.py
# Purpose: Demo script showing two-ended calibration with synchronization and
#          error handling through the implicit endpoint path.

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.test_engine import TestEngine
from src.core.report_generator import ReportGenerator
from src.utils.logger import setup_logging


def main():
    """Run the two-ended calibration demo using sim:// endpoints."""
    print("\n" + "=" * 60)
    print("AutoCalBridge Demo - Two-Ended Calibration with Sync & Error Handling")
    print("=" * 60)

    # Setup logging
    setup_logging("INFO")

    # Create test engine
    print("\n[1] Initializing test engine...")
    engine = TestEngine()

    # Configure synchronization
    engine.set_sync_config(
        enabled=True,
        method="opc",  # "opc", "wai", or "delay"
        delay_ms=100
    )
    print(f"    Sync enabled: True")
    print(f"    Sync method: opc")

    # Configure error handling
    engine.set_error_config(
        enabled=True,
        stop_on_error=True
    )
    print(f"    Error checking enabled: True")
    print(f"    Stop on error: True")

    # Connect to simulator endpoints using implicit resource strings.
    # ACB does not need to know whether these are simulators or physical VISA
    # instruments. The endpoint factory interprets the resource strings.
    print("\n[2] Connecting source and DUT endpoints...")
    source_connected = engine.connect_source("sim://keysight_source")
    dut_connected = engine.connect_dut("sim://keysight_34461a")

    if not source_connected:
        print("    Source connection failed.")
        return 1
    if not dut_connected:
        print("    DUT connection failed.")
        return 1

    # Query identities through the endpoint seam
    source_idn = engine.query_source_identity()
    dut_idn = engine.query_dut_identity()
    print(f"    Source connected: {source_idn}")
    print(f"    DUT connected: {dut_idn}")

    # Define test points
    test_points = [1.0, 2.5, 5.0, 10.0]
    tolerance = 0.005
    operator = "Demo_Operator"

    print(f"\n[3] Running two-ended calibration sequence...")
    print(f"    Test Points: {test_points} V")
    print(f"    Tolerance: {tolerance} V")
    print(f"    Operator: {operator}")

    # Run test
    results = engine.run_calibration_sequence(test_points, tolerance, operator)
    print(f"\n[4] Test completed: {len(results)} measurements")

    # Check for errors
    errors = engine.get_errors()
    if errors:
        print(f"\n[!] Errors encountered: {len(errors)}")
        for err in errors:
            print(f"    {err['instrument']}: {err['message']}")

    # Generate report
    print("\n[5] Generating report...")
    report_generator = ReportGenerator()
    report_path = report_generator.generate_report(results, prefix="Demo")
    print(f"    Report saved to: {report_path}")

    # Show summary
    summary = report_generator.generate_summary(results)
    print(f"\n[6] Summary:")
    print(f"    Total Tests: {summary['total']}")
    print(f"    Passed: {summary['passed']}")
    print(f"    Failed: {summary['failed']}")
    print(f"    Pass Rate: {summary['pass_rate']}%")

    # Cleanup
    engine.close()

    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())