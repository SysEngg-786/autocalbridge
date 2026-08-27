# File: src/cli/registry_commands.py
# Path: /d/Projects/autocalbridge/src/cli/registry_commands.py
# Purpose: Registry management command implementations.
#          These functions are reusable by CLI, CICD, and future GUI layers.
#          Includes structured operational and audit logging.

import os
import sys

# Ensure project root is on sys.path when imported directly.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import yaml

from src.cli.common import get_registry
from src.utils.instrument_registry import REGISTRY_FILE, PROFILE_DIR
from src.utils.registry_validator import validate_registry, RegistryValidationError
from src.utils.structured_logger import get_operational_logger, get_audit_logger


def _load_raw_registry(registry_file=REGISTRY_FILE):
    """
    Load the raw registry YAML as a dictionary without normalizing it.

    Returns a dictionary containing at least the 'instruments' key.
    If the file does not exist, returns a fresh structure.
    """
    if os.path.isfile(registry_file):
        with open(registry_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {"instruments": []}
        if not isinstance(data, dict):
            raise ValueError(f"Registry file is not a mapping: {registry_file}")
    else:
        data = {"instruments": []}

    data.setdefault("instruments", [])
    return data


def _write_raw_registry(data, registry_file=REGISTRY_FILE):
    """
    Write a raw registry dictionary back to the YAML file.

    Uses yaml.safe_dump, which does not preserve comments. This limitation
    is accepted for now and logged in the design doc.
    """
    with open(registry_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)


def list_instruments():
    """
    List all registered instruments.

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
            extra={"event_type": "registry_list_failed", "error": str(e)},
        )
        print(f"Error: {e}")
        return 1
    except RegistryValidationError as e:
        operational_logger.error(
            "Registry validation failed",
            extra={"event_type": "registry_list_failed", "error": str(e)},
        )
        print("Registry validation failed:")
        print(e)
        return 1

    audit_logger.info(
        "Registry listed",
        extra={"event_type": "registry_list", "entry_count": len(registry)},
    )

    if len(registry) == 0:
        print("No instruments registered.")
        return 0

    print(f"{'ID':<20} {'KIND':<10} {'PROFILE':<25} {'DISPLAY NAME':<20} CONNECTION")
    print("-" * 100)
    for entry in registry:
        print(
            f"{entry.id:<20} {entry.kind:<10} {entry.profile:<25} "
            f"{entry.display_name:<20} {entry.connection}"
        )
    return 0


def register_instrument(
    entry_id,
    profile,
    kind,
    display_name,
    connection,
    role="any",
):
    """
    Add a new instrument entry to the registry.

    Args:
        entry_id: Unique instrument instance ID.
        profile: Capability profile file name.
        kind: "physical" or "virtual".
        display_name: Human-readable display name.
        connection: VISA resource string or sim:// URI.
        role: Default role hint ("any", "source", or "dut").

    Returns:
        int: 0 on success, 1 on failure.
    """
    operational_logger = get_operational_logger()
    audit_logger = get_audit_logger()

    new_entry = {
        "id": entry_id,
        "profile": profile,
        "kind": kind,
        "display_name": display_name,
        "connection": connection,
        "role": role,
        "safety_limits": {},
        "metadata": {},
    }

    try:
        data = _load_raw_registry()
        data["instruments"].append(new_entry)

        # Validate the entire proposed registry before writing. This catches
        # duplicate IDs, missing profiles, bad kinds, and connection rule
        # violations before the file is modified.
        validate_registry(data, profile_dir=PROFILE_DIR)

        _write_raw_registry(data)
    except (FileNotFoundError, ValueError, RegistryValidationError, yaml.YAMLError) as e:
        operational_logger.error(
            "Instrument registration failed",
            extra={
                "event_type": "registry_register_failed",
                "instrument_id": entry_id,
                "error": str(e),
            },
        )
        print("Registration failed:")
        print(e)
        return 1

    audit_logger.info(
        "Instrument registered",
        extra={
            "event_type": "registry_register",
            "instrument_id": entry_id,
            "profile": profile,
            "kind": kind,
            "connection": connection,
        },
    )

    print(f"Registered instrument: {new_entry['id']}")
    return 0


def unregister_instrument(entry_id):
    """
    Remove an instrument entry from the registry by ID.

    Args:
        entry_id: Instrument instance ID to remove.

    Returns:
        int: 0 on success, 1 on failure.
    """
    operational_logger = get_operational_logger()
    audit_logger = get_audit_logger()

    try:
        data = _load_raw_registry()
        instruments = data.get("instruments", [])

        matching = [entry for entry in instruments if entry.get("id") == entry_id]
        if not matching:
            operational_logger.error(
                "Unregister failed: instrument not found",
                extra={
                    "event_type": "registry_unregister_failed",
                    "instrument_id": entry_id,
                },
            )
            print(f"Unregister failed: no instrument found with id '{entry_id}'.")
            return 1

        instruments.remove(matching[0])

        # Validate the remaining registry before writing.
        validate_registry(data, profile_dir=PROFILE_DIR)

        _write_raw_registry(data)
    except (FileNotFoundError, ValueError, RegistryValidationError, yaml.YAMLError) as e:
        operational_logger.error(
            "Unregister failed",
            extra={
                "event_type": "registry_unregister_failed",
                "instrument_id": entry_id,
                "error": str(e),
            },
        )
        print("Unregister failed:")
        print(e)
        return 1

    audit_logger.info(
        "Instrument unregistered",
        extra={
            "event_type": "registry_unregister",
            "instrument_id": entry_id,
        },
    )

    print(f"Unregistered instrument: {entry_id}")
    return 0