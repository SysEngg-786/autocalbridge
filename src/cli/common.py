# File: src/cli/common.py
# Path: /d/Projects/autocalbridge/src/cli/common.py
# Purpose: Shared helpers for CLI command modules.
#          Keeps registry lookup and endpoint opening in one place so
#          command implementations stay small and consistent.
#          Builds command policies for physical endpoints from profiles.
#          Loads transport config for physical entries when transport is set.

import os
import sys

# Ensure the project root is on sys.path when modules are imported from
# outside the package, e.g. by thin scripts or CICD runners.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils.instrument_registry import load_registry
from src.utils.registry_validator import RegistryValidationError
from src.core.endpoints.endpoint_factory import create_from_resource_string
from src.core.endpoints.instrument_endpoint import InstrumentEndpointError
from src.utils.transport_config import load_transport_config, TransportConfigError
from security.policy_loader import build_policy_from_source

# Directory containing instrument capability profiles.
INSTRUMENTS_DIR = "config/instruments"


def get_registry():
    """
    Load the instrument registry.

    Returns:
        InstrumentRegistry: Validated registry object.

    Raises:
        FileNotFoundError: If registry file is missing.
        RegistryValidationError: If registry content is invalid.
    """
    return load_registry()


def find_entry(registry, entry_id):
    """
    Find an instrument entry by ID.

    Args:
        registry: InstrumentRegistry instance.
        entry_id: ID string.

    Returns:
        InstrumentRegistryEntry or None.
    """
    return registry.get(entry_id)


def open_endpoint_for_entry(entry, timeout_ms=5000):
    """
    Create and open an endpoint for a registry entry.

    Uses the standard endpoint factory so the same path works for
    physical and virtual instruments.

    For physical endpoints:
    - A command policy is built from the entry's capability profile.
    - If the entry has a `transport`, the corresponding transport config
      is loaded and supplied to the endpoint.

    Simulator endpoints build their own policy inside the factory and
    ignore the passed policy/transport config.

    Args:
        entry: InstrumentRegistryEntry instance.
        timeout_ms: Fallback operation timeout in milliseconds.

    Returns:
        Opened InstrumentEndpoint.

    Raises:
        InstrumentEndpointError: If factory or open fails, or if transport
            config cannot be loaded.
    """
    resource_string = entry.connection

    # Build a command policy from the profile for physical endpoints.
    profile_path = os.path.join(INSTRUMENTS_DIR, entry.profile)
    command_policy = None
    if os.path.isfile(profile_path):
        command_policy = build_policy_from_source(profile_path)

    # Load transport config if the registry entry specifies one.
    transport_config = None
    if getattr(entry, "transport", None):
        try:
            transport_config = load_transport_config(entry.transport)
        except TransportConfigError as exc:
            raise InstrumentEndpointError(
                f"Failed to load transport config '{entry.transport}': {exc}",
                endpoint_type="visa",
                resource_string=resource_string,
                cause=exc,
            ) from exc

    endpoint = create_from_resource_string(
        resource_string,
        command_policy=command_policy,
        transport_config=transport_config,
    )
    endpoint.open(resource_string, timeout_ms=timeout_ms)
    return endpoint