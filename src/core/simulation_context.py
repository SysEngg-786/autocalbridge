# File: src/core/simulation_context.py
# Path: /d/Projects/autocalbridge/src/core/simulation_context.py
# Purpose: Hidden simulator-layer link for sharing simulated signal values
#          between a source simulator and a DUT simulator.

"""
SimulationContext.

This class belongs to the simulator layer, not the instrument endpoint layer.

It exists so a source simulator can publish a simulated stimulus value and a
DUT simulator can read that value later. This forms the simulated equivalent
of the physical signal path between a reference source and a unit under test.

Important boundary rule:
    ACB must never see, import, create, or manage SimulationContext.
    It is injected and used only inside the simulator layer.

This first version is intentionally simple and in-process only:

- one shared context
- no locking
- no network distribution
- no persistence
- no link identifiers

Future simulator deployments may replace this object with a network-backed or
keyed implementation behind the same simulator-layer seam.
"""


class SimulationContext:
    """
    Small shared-state store for simulated signal values.

    Source simulator updates a signal value, for example:

        context.set_value("voltage", 5.0)

    DUT simulator reads the same value later, for example:

        target = context.get_value("voltage", default=0.0)

    The context intentionally has no knowledge of instruments, profiles, ACB,
    reports, or calibration logic. It only stores values by name.
    """

    def __init__(self) -> None:
        """
        Initialise an empty simulation context.
        """
        self._values = {}

    def set_value(self, name: str, value: object) -> None:
        """
        Store a simulated signal value.

        Args:
            name: Signal name, e.g. "voltage", "current", "frequency".
            value: Current simulated value for that signal.
        """
        self._values[str(name)] = value

    def get_value(self, name: str, default: object = None) -> object:
        """
        Retrieve a simulated signal value.

        Args:
            name: Signal name to retrieve.
            default: Value returned if the named signal has not been set.

        Returns:
            The stored value or the supplied default.
        """
        return self._values.get(str(name), default)