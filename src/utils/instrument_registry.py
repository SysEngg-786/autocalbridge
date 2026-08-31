# File: src/utils/instrument_registry.py
# Path: /d/Projects/autocalbridge/src/utils/instrument_registry.py
# Purpose: Load and normalize the AutoCalBridge instrument registry.
#          Delegates validation to registry_validator to keep loading and
#          rule enforcement separate.
#          Includes transport field for physical instrument entries.

import os
import yaml

from src.utils.registry_validator import validate_registry, RegistryValidationError

# Expected path of the registry file relative to the project root.
REGISTRY_FILE = "config/instruments_registry.yaml"

# Default directory containing instrument capability profiles.
PROFILE_DIR = "config/instruments"


class InstrumentRegistryEntry:
    """
    Normalized view of one instrument registry entry.

    This class carries the fields ACB uses to create an endpoint and
    understand the instance. It does not contain instrument SCPI behavior.
    """

    def __init__(self, raw_entry):
        self.id = raw_entry.get("id")
        self.profile = raw_entry.get("profile")
        self.kind = raw_entry.get("kind")
        self.display_name = raw_entry.get("display_name")
        self.connection = raw_entry.get("connection")
        self.transport = raw_entry.get("transport", "")
        self.role = raw_entry.get("role", "any")
        self.safety_limits = raw_entry.get("safety_limits", {})
        self.metadata = raw_entry.get("metadata", {})

    def to_dict(self):
        """Return a plain dictionary representation for consumers."""
        return {
            "id": self.id,
            "profile": self.profile,
            "kind": self.kind,
            "display_name": self.display_name,
            "connection": self.connection,
            "transport": self.transport,
            "role": self.role,
            "safety_limits": self.safety_limits,
            "metadata": self.metadata,
        }


class InstrumentRegistry:
    """
    Collection of normalized registry entries.

    Provides lookup by ID and iteration over all registered instruments.
    """

    def __init__(self, entries):
        self._entries = entries
        self._by_id = {entry.id: entry for entry in entries}

    def __iter__(self):
        return iter(self._entries)

    def __len__(self):
        return len(self._entries)

    def get(self, entry_id):
        """Return the entry with the given ID, or None if not present."""
        return self._by_id.get(entry_id)

    def ids(self):
        """Return all registered instrument IDs in file order."""
        return [entry.id for entry in self._entries]


def load_registry(registry_file=REGISTRY_FILE, profile_dir=PROFILE_DIR):
    """
    Load and validate the instrument registry.

    Parameters
    ----------
    registry_file : str
        Path to the registry YAML file.
    profile_dir : str
        Directory containing capability profile YAML files.

    Returns
    -------
    InstrumentRegistry
        A normalized, validated registry object.

    Raises
    ------
    FileNotFoundError
        If the registry file does not exist.
    RegistryValidationError
        If the registry contains invalid data.
    """
    if not os.path.isfile(registry_file):
        raise FileNotFoundError(f"Instrument registry not found: {registry_file}")

    with open(registry_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Validate before normalization. If the file is invalid, we do not
    # return a partial registry.
    validate_registry(data, profile_dir=profile_dir)

    raw_entries = data.get("instruments", [])
    normalized_entries = [InstrumentRegistryEntry(entry) for entry in raw_entries]

    return InstrumentRegistry(normalized_entries)