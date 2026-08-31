# File: src/core/procedure_validator.py
# Path: /d/Projects/autocalbridge/src/core/procedure_validator.py
# Purpose: Validation rules for AutoCalBridge calibration procedure files.
#          Separated from the loader to keep validation modular.
#          Supports absolute and relative tolerance types.

ALLOWED_PROCEDURE_FIELDS = {
    "procedure_id",
    "label",
    "source_command_template",
    "dut_query_command",
    "points",
    "tolerance",
    "tolerance_type",
    "sync",
    "metadata",
}

ALLOWED_TOLERANCE_TYPES = {"absolute", "relative"}


class ProcedureValidationError(Exception):
    """Raised when one or more procedure configuration fields fail validation."""

    def __init__(self, errors):
        self.errors = errors
        message = f"Procedure validation failed with {len(errors)} error(s):\n" + "\n".join(
            f"  {e}" for e in errors
        )
        super().__init__(message)


def validate_procedure_data(data):
    """
    Validate a loaded procedure configuration dictionary.

    Args:
        data: Dictionary from YAML-safe-load of one procedure file.

    Raises:
        ProcedureValidationError: If any validation rule is violated.
    """
    errors = []

    if not isinstance(data, dict):
        raise ProcedureValidationError(["Procedure configuration must be a mapping."])

    # Unknown-field rejection keeps the schema honest.
    unknown_fields = set(data.keys()) - ALLOWED_PROCEDURE_FIELDS
    if unknown_fields:
        errors.append(f"Unknown procedure fields: {sorted(unknown_fields)}")

    # Required fields.
    required_string_fields = [
        "procedure_id",
        "source_command_template",
        "dut_query_command",
    ]
    for field in required_string_fields:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Missing or empty required field '{field}'.")

    # points must be a non-empty list of numbers.
    points = data.get("points")
    if not isinstance(points, list) or not points:
        errors.append("Field 'points' must be a non-empty list.")
    else:
        for index, point in enumerate(points):
            if not isinstance(point, (int, float)) or isinstance(point, bool):
                errors.append(f"points[{index}] must be a number.")

    # tolerance must be a number greater than zero.
    tolerance = data.get("tolerance")
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool):
        errors.append("Field 'tolerance' must be a number.")
    elif tolerance <= 0:
        errors.append("Field 'tolerance' must be greater than zero.")

    # tolerance_type must be one of the allowed values if present.
    tolerance_type = data.get("tolerance_type")
    if tolerance_type is not None:
        if not isinstance(tolerance_type, str):
            errors.append("Field 'tolerance_type' must be a string.")
        elif tolerance_type.strip().lower() not in ALLOWED_TOLERANCE_TYPES:
            errors.append(
                f"Field 'tolerance_type' must be one of {sorted(ALLOWED_TOLERANCE_TYPES)}."
            )

    # Optional label must be string if present.
    if "label" in data and not isinstance(data["label"], str):
        errors.append("Field 'label' must be a string.")

    # Optional sync must be mapping if present.
    if "sync" in data and not isinstance(data["sync"], dict):
        errors.append("Field 'sync' must be a mapping.")

    # Optional metadata must be mapping if present.
    if "metadata" in data and not isinstance(data["metadata"], dict):
        errors.append("Field 'metadata' must be a mapping.")

    if errors:
        raise ProcedureValidationError(errors)