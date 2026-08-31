# File: src/utils/registry_validator.py
# Path: /d/Projects/autocalbridge/src/utils/registry_validator.py
# Purpose: Validation rules for the AutoCalBridge instrument registry.
#          Separated from the loader to keep validation modular and reusable.

import os

# Allowed top-level entry fields. Unknown fields are rejected to catch typos
# and prevent silent drift in the registry schema.
ALLOWED_ENTRY_FIELDS = {
    "id",
    "profile",
    "kind",
    "display_name",
    "connection",
    "transport",
    "role",
    "safety_limits",
    "metadata",
}

# Allowed values for the instrument kind.
ALLOWED_KINDS = {"physical", "virtual"}

# Allowed values for the default role hint.
ALLOWED_ROLES = {"any", "source", "dut"}


class RegistryValidationError(Exception):
    """Raised when one or more registry entries fail validation."""

    def __init__(self, errors):
        self.errors = errors
        message = f"Registry validation failed with {len(errors)} error(s):\n" + "\n".join(
            f"  {e}" for e in errors
        )
        super().__init__(message)


def validate_registry(data, profile_dir="config/instruments"):
    """
    Validate a loaded instrument registry dictionary.

    Parameters
    ----------
    data : dict
        The result of yaml.safe_load on the registry file.
    profile_dir : str
        Directory containing capability profile YAML files.

    Raises
    ------
    RegistryValidationError
        If any validation rule is violated. The exception collects all
        errors so the operator can fix them in one pass.
    """
    errors = []

    if not isinstance(data, dict):
        raise RegistryValidationError(["Top-level registry structure must be a mapping."])

    instruments = data.get("instruments")
    if not isinstance(instruments, list) or not instruments:
        errors.append("Top-level key 'instruments' must be a non-empty list.")

    if not errors:
        seen_ids = set()
        for index, entry in enumerate(instruments):
            if not isinstance(entry, dict):
                errors.append(f"Entry {index} is not a mapping.")
                continue

            # ID uniqueness is checked across the whole list.
            entry_id = entry.get("id")
            if entry_id in seen_ids:
                errors.append(f"Entry {index}: duplicate id '{entry_id}'.")
            if isinstance(entry_id, str) and entry_id:
                seen_ids.add(entry_id)

            _validate_entry(entry, index, profile_dir, errors)

    if errors:
        raise RegistryValidationError(errors)


def _validate_entry(entry, index, profile_dir, errors):
    """
    Validate a single registry entry.

    All checks for one entry are performed here. The function appends
    descriptive errors to the shared errors list.
    """
    # Unknown-field rejection keeps the schema honest and prevents
    # accidentally accepted misspellings from becoming hidden behavior.
    unknown_fields = set(entry.keys()) - ALLOWED_ENTRY_FIELDS
    if unknown_fields:
        errors.append(
            f"Entry {index}: unknown fields {sorted(unknown_fields)}."
        )

    # Required fields.
    required = ["id", "profile", "kind", "display_name", "connection"]
    for field in required:
        if field not in entry:
            errors.append(f"Entry {index}: missing required field '{field}'.")
            return

        value = entry[field]
        if not isinstance(value, str) or not value.strip():
            errors.append(
                f"Entry {index}: field '{field}' must be a non-empty string."
            )

    entry_id = entry.get("id", "")
    entry_profile = entry.get("profile", "")
    entry_kind = entry.get("kind", "")
    entry_connection = entry.get("connection", "")

    # Kind must be one of the supported values.
    if entry_kind not in ALLOWED_KINDS:
        errors.append(
            f"Entry {index} ('{entry_id}'): kind must be one of {sorted(ALLOWED_KINDS)}."
        )

    # Profile must exist in the capability profile directory.
    if entry_profile:
        profile_path = os.path.join(profile_dir, entry_profile)
        if not os.path.isfile(profile_path):
            errors.append(
                f"Entry {index} ('{entry_id}'): profile '{entry_profile}' not found under '{profile_dir}'."
            )

    # Connection rules differ by kind.
    if entry_kind == "physical":
        # Physical endpoints use a VISA resource string and must not start
        # with sim://, which is reserved for virtual endpoints.
        if entry_connection.startswith("sim://"):
            errors.append(
                f"Entry {index} ('{entry_id}'): physical connection must not use sim:// scheme."
            )
    elif entry_kind == "virtual":
        # Virtual endpoints must use sim://<profile_name>. This keeps the
        # simulated instance tied to a real capability profile.
        if not entry_connection.startswith("sim://"):
            errors.append(
                f"Entry {index} ('{entry_id}'): virtual connection must start with 'sim://'."
            )
        else:
            # The part after sim:// should match an existing profile name.
            # Optional consistency check for future; not fully enforced now.
            sim_name = entry_connection[len("sim://"):]
            if sim_name and not os.path.isfile(os.path.join(profile_dir, f"{sim_name}.yaml")):
                errors.append(
                    f"Entry {index} ('{entry_id}'): virtual connection references unknown simulator '{sim_name}'."
                )

    # Optional role, if present, must be one of the allowed role hints.
    if "role" in entry and entry["role"] not in ALLOWED_ROLES:
        errors.append(
            f"Entry {index} ('{entry_id}'): role must be one of {sorted(ALLOWED_ROLES)}."
        )

    # safety_limits and metadata, if present, must be mappings.
    if "safety_limits" in entry and not isinstance(entry["safety_limits"], dict):
        errors.append(
            f"Entry {index} ('{entry_id}'): 'safety_limits' must be a mapping."
        )
    if "metadata" in entry and not isinstance(entry["metadata"], dict):
        errors.append(
            f"Entry {index} ('{entry_id}'): 'metadata' must be a mapping."
        )