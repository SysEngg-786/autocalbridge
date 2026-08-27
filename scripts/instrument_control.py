# File: scripts/instrument_control.py
# Path: /d/Projects/autocalbridge/scripts/instrument_control.py
# Purpose: Thin entrypoint for instrument interaction commands.
#          All logic lives in src/cli/instrument_commands.py so it can be
#          reused by CICD, tests, and future GUI layers without duplicating
#          endpoint or registry handling.
#          Initializes structured logging before command dispatch.

import argparse
import os
import sys

# Ensure project root is on sys.path when this script is run directly
# or as a module, so `src.cli` imports work consistently.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.cli.instrument_commands import (
    test_instrument,
    basic_check_instrument,
    write_check_instrument,
    diagnostics_instrument,
    send_instrument,
)

# Structured logging must be initialized before any command runs so endpoint
# and audit log messages are written to the correct log directories.
from src.utils.structured_logger import setup_logging


def build_parser():
    """Build argument parser for the instrument control CLI."""
    parser = argparse.ArgumentParser(
        prog="instrument_control",
        description="Interact with registered AutoCalBridge instruments.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # test command: basic identity connectivity check.
    test_parser = subparsers.add_parser(
        "test",
        help="Test connectivity to a registered instrument",
    )
    test_parser.add_argument("id", help="Instrument instance ID to test")

    # basic-check command: read-only standard SCPI queries.
    basic_check_parser = subparsers.add_parser(
        "basic-check",
        help="Run read-only standard SCPI queries",
    )
    basic_check_parser.add_argument("id", help="Instrument instance ID to check")

    # write-check command: safe write-path verification with error checks.
    write_check_parser = subparsers.add_parser(
        "write-check",
        help="Run safe write commands and verify error queue",
    )
    write_check_parser.add_argument("id", help="Instrument instance ID to check")

    # diagnostics command: non-intrusive diagnostic queries.
    diagnostics_parser = subparsers.add_parser(
        "diagnostics",
        help="Run non-intrusive diagnostic queries",
    )
    diagnostics_parser.add_argument("id", help="Instrument instance ID to check")

    # send command: send one sanitized SCPI command.
    send_parser = subparsers.add_parser(
        "send",
        help="Send one SCPI command to a registered instrument",
    )
    send_parser.add_argument("id", help="Instrument instance ID")
    send_parser.add_argument("scpi_command", help="SCPI command or query")

    return parser


def main(argv=None):
    """Run the instrument control CLI."""
    # Ensure loggers and handlers exist before any command executes.
    setup_logging()

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "test":
        return test_instrument(args.id)
    if args.command == "basic-check":
        return basic_check_instrument(args.id)
    if args.command == "write-check":
        return write_check_instrument(args.id)
    if args.command == "diagnostics":
        return diagnostics_instrument(args.id)
    if args.command == "send":
        return send_instrument(args.id, args.scpi_command)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())