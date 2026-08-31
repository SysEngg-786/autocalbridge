# File: src/core/endpoints/endpoint_factory.py
# Path: /d/Projects/autocalbridge/src/core/endpoints/endpoint_factory.py
# Purpose: Config-driven and resource-string-driven factory for creating
#          instrument endpoints. Supports optional CommandPolicy and
#          TransportConfig for physical endpoints.

"""
Endpoint factory.

This module creates InstrumentEndpoint instances from either:

- a plain configuration dictionary, or
- a single implicit resource string.

ACB should use the resource-string form when possible so it never branches on
simulator vs physical endpoint type.

Supported implicit schemes:

    sim://<profile_name>          -> SimulatorEndpoint using
                                     config/instruments/<profile_name>.yaml

    anything else                 -> PyVisaEndpoint using the supplied VISA
                                     resource string

Examples:

    sim://keysight_34461a
    TCPIP0::192.168.1.50::inst0::INSTR
    USB0::0x0957::0x1507::MY12345678::INSTR
    GPIB0::1::INSTR
    ASRL1::INSTR

The factory returns an unopened endpoint. The caller is responsible for calling
open() with the desired resource string and timeout.

Simulator endpoints created from YAML profiles share one default
SimulationContext. This is the hidden simulator-layer link between a source
simulator and a DUT simulator. ACB never sees or manages this context.

Simulator endpoints created from YAML profiles also receive a CommandPolicy
built from the same profile. Physical endpoints may receive a CommandPolicy
passed by the caller, and optionally a TransportConfig for device-specific
connection behavior.
"""

from typing import Any, Dict, Optional

from .instrument_endpoint import InstrumentEndpoint, InstrumentEndpointError
from .simulator_endpoint import SimulatorEndpoint
from .visa_endpoint import PyVisaEndpoint

from src.core.simulation_context import SimulationContext
from security.policy_loader import build_policy_from_source

# Shared in-process simulation context for all simulator endpoints created by
# this factory. This is the simulated equivalent of the physical signal path
# between a reference source and a DUT.
#
# Future work may replace this with a keyed or network-backed implementation
# without changing the endpoint factory interface.
_default_simulation_context = SimulationContext()


def create(config: Dict[str, Any]) -> InstrumentEndpoint:
    """
    Create an instrument endpoint from an explicit configuration dictionary.

    Supported endpoint types:
        "simulator" -> SimulatorEndpoint
        "visa"      -> PyVisaEndpoint

    Example simulator config:
        {
            "type": "simulator",
            "profile_path": "config/instruments/keysight_34461a.yaml"
        }

    Example visa config:
        {
            "type": "visa",
            "visa_manager": optional_shared_visa_manager,
            "command_policy": optional_command_policy,
            "transport_config": optional_transport_config
        }

    Args:
        config: Dictionary describing the endpoint to create.

    Returns:
        InstrumentEndpoint: An unopened endpoint instance.

    Raises:
        InstrumentEndpointError: If the config is invalid, the endpoint type is
            unsupported, or a simulator profile cannot be loaded.
    """
    if not isinstance(config, dict):
        raise InstrumentEndpointError(
            "Endpoint config must be a dictionary.",
            endpoint_type="unknown",
        )

    endpoint_type = str(config.get("type", "")).strip().lower()

    if endpoint_type == "simulator":
        return _create_simulator_endpoint(config)

    if endpoint_type == "visa":
        return _create_visa_endpoint(config)

    raise InstrumentEndpointError(
        f"Unsupported endpoint type: {endpoint_type!r}",
        endpoint_type=endpoint_type,
    )


def create_from_resource_string(
    resource_string: str,
    visa_manager: Optional[Any] = None,
    command_policy: Optional[Any] = None,
    transport_config: Optional[Any] = None,
) -> InstrumentEndpoint:
    """
    Create an instrument endpoint from an implicit resource string.

    The resource string scheme is interpreted centrally here so ACB does not
    need to know whether the endpoint is simulated or physical.

    Args:
        resource_string:
            A simulator logical URI or a physical VISA resource string.

            Simulator form:
                sim://<profile_name>

            VISA examples:
                TCPIP0::192.168.1.50::inst0::INSTR
                USB0::0x0957::0x1507::MY12345678::INSTR
                GPIB0::1::INSTR
                ASRL1::INSTR

        visa_manager:
            Optional shared VisaManager. Used only when the resource string is
            interpreted as a physical VISA endpoint.

        command_policy:
            Optional CommandPolicy. Used only when the resource string is
            interpreted as a physical VISA endpoint. Simulator endpoints build
            their policy from the profile automatically.

        transport_config:
            Optional TransportConfig. Used only when the resource string is
            interpreted as a physical VISA endpoint.

    Returns:
        InstrumentEndpoint: Unopened endpoint instance.

    Raises:
        InstrumentEndpointError: If the resource string is empty, a simulator
            profile cannot be derived, or the profile cannot be loaded.
    """
    if not resource_string:
        raise InstrumentEndpointError(
            "Resource string is empty.",
            endpoint_type="unknown",
        )

    # The only simulator scheme at present is sim://
    if resource_string.startswith("sim://"):
        profile_name = resource_string[len("sim://") :].strip()

        if not profile_name:
            raise InstrumentEndpointError(
                "Simulator resource string is missing a profile name.",
                endpoint_type="simulator",
                resource_string=resource_string,
            )

        profile_path = f"config/instruments/{profile_name}.yaml"

        return create(
            {
                "type": "simulator",
                "profile_path": profile_path,
            }
        )

    # Every other supported string is treated as a physical VISA resource.
    return create(
        {
            "type": "visa",
            "visa_manager": visa_manager,
            "command_policy": command_policy,
            "transport_config": transport_config,
        }
    )


def _create_simulator_endpoint(config: Dict[str, Any]) -> SimulatorEndpoint:
    """
    Create a SimulatorEndpoint from configuration.

    The simulator instance may be supplied directly through:
        config["simulator_instance"]

    If no instance is supplied, a YAML instrument profile is loaded through:
        config["profile_path"]

    Profile-loaded simulator instances receive:

    - the factory-level shared SimulationContext
    - a CommandPolicy built from the same profile

    Args:
        config: Endpoint configuration.

    Returns:
        SimulatorEndpoint: Unopened simulator endpoint.

    Raises:
        InstrumentEndpointError: If no simulator instance or profile path is
            available, or if the simulator profile/policy cannot be loaded.
    """
    simulator = config.get("simulator_instance")
    command_policy = None

    if simulator is None:
        profile_path = config.get("profile_path")

        if not profile_path:
            raise InstrumentEndpointError(
                "Simulator endpoint requires simulator_instance or profile_path.",
                endpoint_type="simulator",
            )

        # Imported locally so the factory does not load YAML machinery unless a
        # profile-based simulator is actually requested.
        from src.core.yaml_instrument import load_instrument

        # Allow an explicit context override for tests. Otherwise use the
        # shared default context so separate source and DUT simulators created
        # by this factory see the same simulated signal path.
        simulation_context = config.get(
            "simulation_context",
            _default_simulation_context,
        )

        try:
            simulator = load_instrument(
                str(profile_path),
                simulation_context=simulation_context,
            )
        except Exception as exc:
            raise InstrumentEndpointError(
                f"Failed to load simulator profile: {profile_path!r}",
                endpoint_type="simulator",
                resource_string=str(profile_path),
                cause=exc,
            ) from exc

        # Build a command policy from the same profile. This enforces
        # allowlist-based command validation at the simulator endpoint boundary.
        try:
            command_policy = build_policy_from_source(str(profile_path))
        except Exception as exc:
            raise InstrumentEndpointError(
                f"Failed to build command policy from profile: {profile_path!r}",
                endpoint_type="simulator",
                resource_string=str(profile_path),
                cause=exc,
            ) from exc

    return SimulatorEndpoint(simulator, command_policy=command_policy)


def _create_visa_endpoint(config: Dict[str, Any]) -> PyVisaEndpoint:
    """
    Create a PyVisaEndpoint from configuration.

    An existing VisaManager may be supplied through:
        config["visa_manager"]

    An optional CommandPolicy may be supplied through:
        config["command_policy"]

    An optional TransportConfig may be supplied through:
        config["transport_config"]

    If no transport config is supplied, the endpoint uses default VISA
    termination and timeout behavior.

    Args:
        config: Endpoint configuration.

    Returns:
        PyVisaEndpoint: Unopened VISA endpoint.
    """
    visa_manager = config.get("visa_manager")
    command_policy = config.get("command_policy")
    transport_config = config.get("transport_config")

    return PyVisaEndpoint(
        visa_manager,
        command_policy=command_policy,
        transport_config=transport_config,
    )