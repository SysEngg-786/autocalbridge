# File: scripts/register_instrument.py
# Path: /d/Projects/autocalbridge/scripts/register_instrument.py
# Purpose: Thin entrypoint for instrument registry management commands.
#          All logic lives in src/cli/registry_commands.py so it can be
#          reused by CICD, tests, and future GUI layers.
#          Initializes structured logging before command dispatch.

import argparse
import os
import sys

# Ensure project root is on sys.path when this script is run directly
# or as a module, so `src.cli` imports work consistently.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.cli.registry_commands import (
    list_instruments,
    register_instrument,
    unregister_instrument,
)

# Structured logging must be initialized before any command runs so registry
# actions are written to the correct log directories.
from src.utils.structured_logger import setup_logging


def build_parser():
    """Build argument parser for the registry management CLI."""
    parser = argparse.ArgumentParser(
        prog="register_instrument",
        description="Manage AutoCalBridge instrument registry entries.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list command: no arguments.
    subparsers.add_parser("list", help="List registered instruments")

    # register command.
    register_parser = subparsers.add_parser("register", help="Register a new instrument")
    register_parser.add_argument("--id", required=True, help="Unique instrument instance ID")
    register_parser.add_argument("--profile", required=True, help="Capability profile file name")
    register_parser.add_argument(
        "--kind", required=True, choices=["physical", "virtual"],
        help="Instrument kind: physical or virtual"
    )
    register_parser.add_argument("--display-name", required=True, help="Human-readable display name")
    register_parser.add_argument("--connection", required=True, help="VISA resource string or sim:// URI")
    register_parser.add_argument(
        "--role", default="any", choices=["any", "source", "dut"],
        help="Default role hint; actual role set per session/test config"
    )

    # unregister command.
    unregister_parser = subparsers.add_parser("unregister", help="Remove an instrument by ID")
    unregister_parser.add_argument("id", help="Instrument instance ID to remove")

    return parser


def main(argv=None):
    """Run the registry CLI."""
    # Ensure loggers and handlers exist before any command executes.
    setup_logging()

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list":
        return list_instruments()
    if args.command == "register":
        return register_instrument(
            entry_id=args.id,
            profile=args.profile,
            kind=args.kind,
            display_name=args.display_name,
            connection=args.connection,
            role=args.role,
        )
    if args.command == "unregister":
        return unregister_instrument(args.id)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())