# File: security/config_security.py
# Path: /d/Projects/autocalbridge/security/config_security.py
# Purpose: Secure configuration loading and redaction helpers for ACB.

"""
Secure configuration helpers.

This module provides safe, reusable helpers for loading and redacting external
configuration.

Design rules:

- contains logic only
- sensitive field names are supplied externally
- no hardcoded secret field names
- no operational IP addresses, usernames, passwords, or file paths
- uses Python's safe YAML loader and standard JSON parser only
- rejected input raises controlled SecurityValidationError

Use in ACB config loading and logging layers as:

    redacted = redact_config(config, sensitive_fields={"visa_address"})
"""

import json
import os
from typing import Any, Dict, Iterable, Optional

import yaml

from .validators import SecurityValidationError


def redact_config(
    config: Any,
    sensitive_fields: Optional[Iterable[str]] = None,
) -> Any:
    """
    Return a redacted copy of a configuration object.

    Any dictionary key whose name is in sensitive_fields is replaced with
    "***". Lists and nested dictionaries are handled recursively. Other values
    are returned unchanged.

    Args:
        config: Configuration value to redact.
        sensitive_fields: Optional iterable of field names to redact.

    Returns:
        A new object with sensitive fields redacted.
    """
    sensitive = set(sensitive_fields or set())

    if isinstance(config, dict):
        return {
            key: (
                "***"
                if key in sensitive
                else redact_config(value, sensitive)
            )
            for key, value in config.items()
        }

    if isinstance(config, list):
        return [redact_config(item, sensitive) for item in config]

    return config


def load_json_config(
    path: str,
    sensitive_fields: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """
    Load a JSON configuration file safely.

    Args:
        path: Path to the JSON file.
        sensitive_fields: Optional iterable of field names whose values should
            be redacted when logging or returning to untrusted callers.

    Returns:
        dict: Parsed configuration dictionary.

    Raises:
        SecurityValidationError: If the path is invalid, the file cannot be
            parsed, or the root value is not a dictionary.
    """
    if not isinstance(path, str) or not path.strip():
        raise SecurityValidationError("Configuration path is empty")

    if not os.path.exists(path):
        raise SecurityValidationError("Configuration file not found")

    try:
        with open(path, "r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except json.JSONDecodeError as exc:
        raise SecurityValidationError(
            f"Invalid JSON configuration: {exc}"
        ) from exc

    if not isinstance(config, dict):
        raise SecurityValidationError(
            "Configuration root must be a JSON object"
        )

    return config


def load_yaml_config(
    path: str,
    sensitive_fields: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """
    Load a YAML configuration file safely.

    This function uses yaml.safe_load and never yaml.load.

    Args:
        path: Path to the YAML file.
        sensitive_fields: Optional iterable of field names whose values should
            be redacted when logging or returning to untrusted callers.

    Returns:
        dict: Parsed configuration dictionary.

    Raises:
        SecurityValidationError: If the path is invalid, the file cannot be
            parsed, or the root value is not a dictionary.
    """
    if not isinstance(path, str) or not path.strip():
        raise SecurityValidationError("Configuration path is empty")

    if not os.path.exists(path):
        raise SecurityValidationError("Configuration file not found")

    try:
        with open(path, "r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)
    except yaml.YAMLError as exc:
        raise SecurityValidationError(
            f"Invalid YAML configuration: {exc}"
        ) from exc

    if not isinstance(config, dict):
        raise SecurityValidationError(
            "Configuration root must be a YAML mapping"
        )

    return config