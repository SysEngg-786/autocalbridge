# File: security/policy_loader.py
# Path: /d/Projects/autocalbridge/security/policy_loader.py
# Purpose: Load allowed SCPI command sets from an instrument profile and build
#          a reusable CommandPolicy instance.

"""
Policy loader.

This module separates policy data from policy logic.

CommandPolicy contains only validation logic. This module loads command data
from an external source, currently the existing instrument YAML profiles.

Allowed queries are taken from:

- a central set of common IEEE 488.2 / SCPI queries
- the profile's `responses` keys

Allowed write roots are taken from:

- a central set of common IEEE 488.2 / SCPI settings
- the profile's `write_commands`

The central common-command sets remove the need to repeat common commands in
every instrument profile. This avoids drift between profile files and keeps
policy knowledge in one place.
"""

import os
from typing import Any, Dict, Optional

import yaml

from .command_policy import CommandPolicy

# ---------------------------------------------------------------------------
# Central common command sets
# ---------------------------------------------------------------------------
# These commands are common across instrument profiles and are always allowed
# for simulator endpoints. They must not be redefined per profile. Profile
# files should only contain instrument-specific commands.
# ---------------------------------------------------------------------------

COMMON_ALLOWED_QUERIES = {
    "*IDN?",
    "*ESR?",
    "*OPC?",
    "SYST:ERR?",
}

COMMON_ALLOWED_WRITES = {
    "*RST",
    "*CLS",
    "*WAI",
}


def build_from_yaml(profile_path: str) -> CommandPolicy:
    """
    Load an instrument YAML profile and build a CommandPolicy.

    Args:
        profile_path: Path to a YAML instrument profile.

    Returns:
        CommandPolicy: Policy configured with common commands plus the
            profile's allowed queries and write commands.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        yaml.YAMLError: If the YAML file cannot be parsed.
        KeyError: If required command sections are missing from the profile.
    """
    if not os.path.exists(profile_path):
        raise FileNotFoundError(f"Profile not found: {profile_path}")

    with open(profile_path, "r", encoding="utf-8") as profile_file:
        config = yaml.safe_load(profile_file)

    return build_from_config(config)


def build_from_config(config: Dict[str, Any]) -> CommandPolicy:
    """
    Build a CommandPolicy from an already-loaded configuration dictionary.

    Args:
        config: Dictionary containing:
            responses: dict of query commands
            write_commands: list of write roots

    Returns:
        CommandPolicy: Configured policy object.
    """
    allowed_queries = set(config.get("responses", {}).keys())
    allowed_queries.update(COMMON_ALLOWED_QUERIES)

    allowed_writes = set(config.get("write_commands", []))
    allowed_writes.update(COMMON_ALLOWED_WRITES)

    return CommandPolicy(
        allowed_queries=allowed_queries,
        allowed_writes=allowed_writes,
    )


def build_policy_from_source(profile_path: Optional[str] = None) -> CommandPolicy:
    """
    Convenience wrapper that returns a policy from a YAML profile.

    This name is intentionally generic. Later it may be extended to support
    JSON policy files or other external policy sources without changing the
    endpoint adapters.

    Args:
        profile_path: Optional path to a YAML profile.

    Returns:
        CommandPolicy: Policy configured from the profile.

    Raises:
        ValueError: If profile_path is empty.
    """
    if not profile_path:
        raise ValueError("profile_path is required")

    return build_from_yaml(profile_path)