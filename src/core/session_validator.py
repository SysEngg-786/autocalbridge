# File: src/core/session_validator.py
# Path: /d/Projects/autocalbridge/src/core/session_validator.py
# Purpose: Validation rules for AutoCalBridge session configuration.
#          Separated from the session loader to keep validation modular.

ALLOWED_SESSION_FIELDS = {
    "session_id",
    "label",
    "operator",
    "supervisor",
    "source_id",
    "dut_id",
    "procedure",
    "metadata",
}


class SessionValidationError(Exception):
    """Raised when one or more session configuration entries fail validation."""

    def __init__(self, errors):
        self.errors = errors
        message = f"Session validation failed with {len(errors)} error(s):\n" + "\n".join(
            f"  {e}" for e in errors
        )
        super().__init__(message)


def validate_session_data(data, registry):
    """
    Validate a loaded session configuration dictionary.

    Args:
        data: Dictionary from YAML-safe-load of one session file.
        registry: InstrumentRegistry instance used to check source/dut IDs.

    Raises:
        SessionValidationError: If any validation rule is violated.
    """
    errors = []

    if not isinstance(data, dict):
        raise SessionValidationError(["Session configuration must be a mapping."])

    # Unknown-field rejection keeps the schema honest.
    unknown_fields = set(data.keys()) - ALLOWED_SESSION_FIELDS
    if unknown_fields:
        errors.append(f"Unknown session fields: {sorted(unknown_fields)}")

    # Required fields.
    required_fields = ["session_id", "operator", "source_id", "dut_id"]
    for field in required_fields:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Missing or empty required field '{field}'.")

    # Optional string fields, if present, must be strings.
    for field in ("label", "supervisor", "procedure"):
        if field in data and not isinstance(data[field], str):
            errors.append(f"Field '{field}' must be a string.")

    # metadata must be a mapping if present.
    if "metadata" in data and not isinstance(data["metadata"], dict):
        errors.append("Field 'metadata' must be a mapping.")

    # Check instrument IDs if they are present as strings.
    source_id = data.get("source_id")
    dut_id = data.get("dut_id")

    if isinstance(source_id, str) and source_id.strip():
        if registry.get(source_id) is None:
            errors.append(f"source_id '{source_id}' is not a registered instrument.")
    else:
        source_id = None

    if isinstance(dut_id, str) and dut_id.strip():
        if registry.get(dut_id) is None:
            errors.append(f"dut_id '{dut_id}' is not a registered instrument.")
    else:
        dut_id = None

    # Source and DUT must be distinct when both are valid.
    if source_id and dut_id and source_id == dut_id:
        errors.append("source_id and dut_id must be different instruments.")

    if errors:
        raise SessionValidationError(errors)