# File: src/cli/instrument_commands.py
# Path: /d/Projects/autocalbridge/src/cli/instrument_commands.py
# Purpose: Instrument interaction command implementations.
#          Reusable by CLI, CICD, and future GUI layers.
#          These commands open a registered instrument through the standard
#          endpoint factory and execute SCPI queries/checks.
#          Structured operational and audit logging is included.

import os
import sys

# Ensure project root is on sys.path when imported directly.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.cli.common import get_registry, find_entry, open_endpoint_for_entry
from src.core.endpoints.instrument_endpoint import InstrumentEndpointError
from src.utils.registry_validator import RegistryValidationError
from src.utils.structured_logger import get_operational_logger, get_audit_logger

# Read-only commands used for basic-check. These are safe standard queries
# that do not change instrument state. Commands use valid SCPI forms;
# documentation bracket notation is not used on the wire.
BASIC_READ_ONLY_COMMANDS = [
    "*IDN?",
    "*ESR?",
    "*STB?",
    "SYST:ERR?",
    "SYST:ERR:ALL?",
]

# Write commands used for write-check. Each command is followed by SYST:ERR?
# to confirm the instrument accepted it without error.
# These are safe and reversible state changes that should be visible on a
# real R&S RTC1002 oscilloscope.
WRITE_CHECK_COMMANDS = [
    "*CLS",
    "*WAI",
    "ACQ:STAT RUN",
    "CHAN1:STAT ON",
    "CHAN1:SCAL 0.01",
    "TIM:SCAL 0.001",
    "TIM:POS 0",
]

# Non-intrusive diagnostic queries. These provide status, options, and
# event-register information without changing instrument state or running
# self-tests/calibration.
DIAGNOSTIC_QUERIES = [
    "SYST:ERR:ALL?",
    "*ESR?",
    "*STB?",
    "STAT:OPER:EVEN?",
    "STAT:QUES:EVEN?",
    "*OPT?",
]

# Maximum acceptable length for one SCPI command received from the CLI.
MAX_SCPI_COMMAND_LENGTH = 1024


def _sanitize_scpi_command(raw_command):
    """
    Sanitize a single SCPI command string from user input.

    Rules:
        1. Must be a string.
        2. Must not be empty or whitespace-only.
        3. Length must not exceed MAX_SCPI_COMMAND_LENGTH.
        4. May contain printable ASCII characters only.
           This blocks newline, carriage return, null, and other control
           characters that could inject additional commands or corrupt
           the SCPI transport.

    Args:
        raw_command: Raw user-supplied command string.

    Returns:
        str: Stripped safe command string.

    Raises:
        ValueError: If the command violates any sanitization rule.
    """
    if not isinstance(raw_command, str):
        raise ValueError("Command must be a string.")

    command = raw_command.strip()
    if not command:
        raise ValueError("Command is empty.")

    if len(command) > MAX_SCPI_COMMAND_LENGTH:
        raise ValueError(
            f"Command exceeds maximum allowed length of {MAX_SCPI_COMMAND_LENGTH} characters."
        )

    # Printable ASCII is the SCPI character set used by this project.
    # This check intentionally rejects all control characters.
    if not all(0x20 <= ord(char) <= 0x7E for char in command):
        raise ValueError("Command contains non-printable or control characters.")

    return command


def _resolve_and_open(entry_id):
    """
    Resolve a registry entry ID and open an endpoint for it.

    Args:
        entry_id: Instrument instance ID from registry.

    Returns:
        tuple: (entry, endpoint) on success.

    Raises:
        LookupError: If entry not found.
        InstrumentEndpointError: If endpoint open fails.
    """
    try:
        registry = get_registry()
    except FileNotFoundError as e:
        raise LookupError(f"Registry file missing: {e}") from e
    except RegistryValidationError as e:
        raise LookupError(f"Registry validation failed: {e}") from e

    entry = find_entry(registry, entry_id)
    if entry is None:
        raise LookupError(f"No instrument found with id '{entry_id}'.")

    endpoint = open_endpoint_for_entry(entry)
    return entry, endpoint


def run_single_command(entry_id, raw_command):
    """
    Execute a single sanitized SCPI command/query on a registered instrument.

    This function does not print anything. It returns a tuple of
    (success, response_text). For a query, response_text contains the
    instrument's response. For a write, response_text is empty.

    Args:
        entry_id: Instrument instance ID from registry.
        raw_command: Raw SCPI command string.

    Returns:
        tuple: (bool, str). bool is True on success, False on failure.
    """
    try:
        command = _sanitize_scpi_command(raw_command)
    except ValueError as e:
        return False, str(e)

    try:
        entry, endpoint = _resolve_and_open(entry_id)
    except (LookupError, InstrumentEndpointError) as e:
        return False, str(e)

    try:
        if command.endswith("?"):
            response = endpoint.query(command)
            return True, (response.strip() if response else "")
        else:
            endpoint.write(command)
            return True, ""
    except InstrumentEndpointError as e:
        return False, e.message
    finally:
        endpoint.close()


def test_instrument(entry_id):
    """
    Test basic connectivity to a registered instrument.

    Opens the endpoint through the standard factory using the entry's
    connection string, sends *IDN?, reports result, and closes.

    Args:
        entry_id: Instrument instance ID from registry.

    Returns:
        int: 0 on success, 1 on failure.
    """
    operational_logger = get_operational_logger()
    audit_logger = get_audit_logger()

    try:
        registry = get_registry()
    except FileNotFoundError as e:
        operational_logger.error(
            "Registry file missing",
            extra={"event_type": "test_failed", "instrument_id": entry_id, "error": str(e)},
        )
        print(f"Error: {e}")
        return 1
    except RegistryValidationError as e:
        operational_logger.error(
            "Registry validation failed",
            extra={"event_type": "test_failed", "instrument_id": entry_id, "error": str(e)},
        )
        print("Registry validation failed:")
        print(e)
        return 1

    entry = find_entry(registry, entry_id)
    if entry is None:
        operational_logger.error(
            "Instrument not found",
            extra={"event_type": "test_failed", "instrument_id": entry_id},
        )
        print(f"Test failed: no instrument found with id '{entry_id}'.")
        return 1

    audit_logger.info(
        "Connectivity test started",
        extra={"event_type": "test_start", "instrument_id": entry_id},
    )

    print(f"Testing {entry.id} ({entry.display_name}) using {entry.connection} ...")

    try:
        endpoint = open_endpoint_for_entry(entry)
        try:
            idn = endpoint.query("*IDN?")
            if idn and idn.strip():
                print(f"IDN response: {idn.strip()}")
                audit_logger.info(
                    "Connectivity test passed",
                    extra={"event_type": "test_success", "instrument_id": entry_id, "response": idn.strip()},
                )
                return 0
            else:
                print("Test failed: empty IDN response.")
                operational_logger.error(
                    "Empty IDN response",
                    extra={"event_type": "test_failed", "instrument_id": entry_id},
                )
                return 1
        except InstrumentEndpointError as e:
            print(f"Test failed: {e.message}")
            operational_logger.error(
                "Endpoint error during test",
                extra={"event_type": "test_failed", "instrument_id": entry_id, "error": e.message},
            )
            return 1
        finally:
            endpoint.close()
    except InstrumentEndpointError as e:
        print(f"Test failed: {e.message}")
        operational_logger.error(
            "Endpoint open failed during test",
            extra={"event_type": "test_failed", "instrument_id": entry_id, "error": e.message},
        )
        return 1


def basic_check_instrument(entry_id):
    """
    Run a read-only set of standard SCPI queries against a registered
    instrument and report each response.

    This checks the query path and common status registers without
    altering instrument state.

    Args:
        entry_id: Instrument instance ID from registry.

    Returns:
        int: 0 if all queries succeed, 1 if any fails.
    """
    operational_logger = get_operational_logger()
    audit_logger = get_audit_logger()

    try:
        registry = get_registry()
    except FileNotFoundError as e:
        operational_logger.error(
            "Registry file missing",
            extra={"event_type": "basic_check_failed", "instrument_id": entry_id, "error": str(e)},
        )
        print(f"Error: {e}")
        return 1
    except RegistryValidationError as e:
        operational_logger.error(
            "Registry validation failed",
            extra={"event_type": "basic_check_failed", "instrument_id": entry_id, "error": str(e)},
        )
        print("Registry validation failed:")
        print(e)
        return 1

    entry = find_entry(registry, entry_id)
    if entry is None:
        operational_logger.error(
            "Instrument not found",
            extra={"event_type": "basic_check_failed", "instrument_id": entry_id},
        )
        print(f"Basic check failed: no instrument found with id '{entry_id}'.")
        return 1

    audit_logger.info(
        "Basic read-only check started",
        extra={"event_type": "basic_check_start", "instrument_id": entry_id},
    )

    print(f"Running basic read-only check on {entry.id} using {entry.connection} ...")

    try:
        endpoint = open_endpoint_for_entry(entry)
        try:
            failed = False
            for command in BASIC_READ_ONLY_COMMANDS:
                try:
                    response = endpoint.query(command)
                    response_text = response.strip() if response else ""
                    print(f"{command:<30} -> {response_text}")
                except InstrumentEndpointError as e:
                    print(f"{command:<30} -> ERROR: {e.message}")
                    failed = True

            if failed:
                operational_logger.error(
                    "Basic check completed with errors",
                    extra={"event_type": "basic_check_failed", "instrument_id": entry_id},
                )
                return 1
            else:
                audit_logger.info(
                    "Basic check passed",
                    extra={"event_type": "basic_check_success", "instrument_id": entry_id},
                )
                return 0
        finally:
            endpoint.close()
    except InstrumentEndpointError as e:
        print(f"Basic check failed to open endpoint: {e.message}")
        operational_logger.error(
            "Endpoint open failed during basic check",
            extra={"event_type": "basic_check_failed", "instrument_id": entry_id, "error": e.message},
        )
        return 1


def write_check_instrument(entry_id):
    """
    Run a safe write-path verification sequence against a registered
    instrument.

    Each write command is followed by SYST:ERR? to confirm the instrument
    accepted it without error. This proves the endpoint write and query
    path works end-to-end before more complex command pipelines are added.

    Args:
        entry_id: Instrument instance ID from registry.

    Returns:
        int: 0 if all writes and error checks succeed, 1 if any fails.
    """
    operational_logger = get_operational_logger()
    audit_logger = get_audit_logger()

    try:
        registry = get_registry()
    except FileNotFoundError as e:
        operational_logger.error(
            "Registry file missing",
            extra={"event_type": "write_check_failed", "instrument_id": entry_id, "error": str(e)},
        )
        print(f"Error: {e}")
        return 1
    except RegistryValidationError as e:
        operational_logger.error(
            "Registry validation failed",
            extra={"event_type": "write_check_failed", "instrument_id": entry_id, "error": str(e)},
        )
        print("Registry validation failed:")
        print(e)
        return 1

    entry = find_entry(registry, entry_id)
    if entry is None:
        operational_logger.error(
            "Instrument not found",
            extra={"event_type": "write_check_failed", "instrument_id": entry_id},
        )
        print(f"Write check failed: no instrument found with id '{entry_id}'.")
        return 1

    audit_logger.info(
        "Write-path check started",
        extra={"event_type": "write_check_start", "instrument_id": entry_id},
    )

    print(f"Running write-path check on {entry.id} using {entry.connection} ...")

    try:
        endpoint = open_endpoint_for_entry(entry)
        try:
            failed = False

            for command in WRITE_CHECK_COMMANDS:
                try:
                    endpoint.write(command)
                    print(f"WRITE {command:<25} -> sent")

                    error_response = endpoint.query("SYST:ERR?")
                    error_text = error_response.strip() if error_response else ""
                    print(f"{'ERROR CHECK':<30} -> {error_text}")

                    if error_text and not error_text.startswith("0,"):
                        failed = True

                except InstrumentEndpointError as e:
                    print(f"WRITE {command:<25} -> ERROR: {e.message}")
                    failed = True

            if failed:
                operational_logger.error(
                    "Write check completed with errors",
                    extra={"event_type": "write_check_failed", "instrument_id": entry_id},
                )
                return 1
            else:
                audit_logger.info(
                    "Write check passed",
                    extra={"event_type": "write_check_success", "instrument_id": entry_id},
                )
                return 0
        finally:
            endpoint.close()
    except InstrumentEndpointError as e:
        print(f"Write check failed to open endpoint: {e.message}")
        operational_logger.error(
            "Endpoint open failed during write check",
            extra={"event_type": "write_check_failed", "instrument_id": entry_id, "error": e.message},
        )
        return 1


def diagnostics_instrument(entry_id):
    """
    Run a set of non-intrusive diagnostic queries against a registered
    instrument.

    These queries provide status, options, and event-register information
    without changing instrument state or running self-tests/calibration.

    Args:
        entry_id: Instrument instance ID from registry.

    Returns:
        int: 0 if all queries succeed, 1 if any fails.
    """
    operational_logger = get_operational_logger()
    audit_logger = get_audit_logger()

    try:
        registry = get_registry()
    except FileNotFoundError as e:
        operational_logger.error(
            "Registry file missing",
            extra={"event_type": "diagnostics_failed", "instrument_id": entry_id, "error": str(e)},
        )
        print(f"Error: {e}")
        return 1
    except RegistryValidationError as e:
        operational_logger.error(
            "Registry validation failed",
            extra={"event_type": "diagnostics_failed", "instrument_id": entry_id, "error": str(e)},
        )
        print("Registry validation failed:")
        print(e)
        return 1

    entry = find_entry(registry, entry_id)
    if entry is None:
        operational_logger.error(
            "Instrument not found",
            extra={"event_type": "diagnostics_failed", "instrument_id": entry_id},
        )
        print(f"Diagnostics failed: no instrument found with id '{entry_id}'.")
        return 1

    audit_logger.info(
        "Diagnostics started",
        extra={"event_type": "diagnostics_start", "instrument_id": entry_id},
    )

    print(f"Running diagnostics on {entry.id} using {entry.connection} ...")

    try:
        endpoint = open_endpoint_for_entry(entry)
        try:
            failed = False
            for command in DIAGNOSTIC_QUERIES:
                try:
                    response = endpoint.query(command)
                    response_text = response.strip() if response else ""
                    print(f"{command:<30} -> {response_text}")
                except InstrumentEndpointError as e:
                    print(f"{command:<30} -> ERROR: {e.message}")
                    failed = True

            if failed:
                operational_logger.error(
                    "Diagnostics completed with errors",
                    extra={"event_type": "diagnostics_failed", "instrument_id": entry_id},
                )
                return 1
            else:
                audit_logger.info(
                    "Diagnostics passed",
                    extra={"event_type": "diagnostics_success", "instrument_id": entry_id},
                )
                return 0
        finally:
            endpoint.close()
    except InstrumentEndpointError as e:
        print(f"Diagnostics failed to open endpoint: {e.message}")
        operational_logger.error(
            "Endpoint open failed during diagnostics",
            extra={"event_type": "diagnostics_failed", "instrument_id": entry_id, "error": e.message},
        )
        return 1


def send_instrument(entry_id, scpi_command):
    """
    Send one user-supplied SCPI command to a registered instrument.

    This is a thin wrapper around run_single_command that prints the result
    to standard output for CLI use. GUI code should use run_single_command
    to capture the response directly.

    Args:
        entry_id: Instrument instance ID from registry.
        scpi_command: Raw SCPI command string from the CLI.

    Returns:
        int: 0 on success, 1 on failure.
    """
    success, response = run_single_command(entry_id, scpi_command)

    if success:
        if response:
            print(response)
        else:
            print("Command sent.")
        return 0
    else:
        print(f"Send failed: {response}")
        return 1