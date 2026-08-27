# File: src/transports/vxi11/acb_device_handler.py
# Path: /d/Projects/autocalbridge/src/transports/vxi11/acb_device_handler.py
# Purpose: ACB VXI-11 device handler backed by SimulatorEndpoint.

"""
ACB VXI-11 device handler.

This handler bridges the VXI-11 transport to the standard AutoCalBridge
instrument endpoint contract. It receives SCPI commands from the VXI-11
server, delegates them to a SimulatorEndpoint, and returns the response.

It must not import ACB test engine, know calibration sequence state, know
report generation, or access simulator profiles directly.
"""

from src.transports.vxi11.vxi11_server import vxi11
from src.transports.vxi11.vxi11_server.instrument_device import DefaultInstrumentDevice


class AcbDeviceHandler(DefaultInstrumentDevice):
    """
    VXI-11 device handler backed by a SimulatorEndpoint.

    The endpoint is supplied at construction time. This keeps the handler
    transport-only and free of simulator profile knowledge.
    """

    def __init__(self, device_name, device_lock, registry, endpoint):
        """
        Initialise the device handler.

        Args:
            device_name: VXI-11 device name, e.g. "inst0".
            device_lock: Lock object supplied by the VXI-11 server.
            registry: Device registry supplied by the server.
            endpoint: SimulatorEndpoint instance used for write and query.
        """
        super().__init__(device_name, device_lock, registry)

        # The endpoint is the only instrument-facing object this handler uses.
        # It already enforces CommandPolicy internally.
        self._endpoint = endpoint

        # Last query response, returned on the next device_read call.
        self._result = ""

    def device_init(self):
        """
        Called once when the VXI-11 server creates this device instance.

        No profile loading happens here. The endpoint was already created by
        EndpointFactory with the correct profile and policy.
        """
        return

    def device_write(self, opaque_data, flags, io_timeout):
        """
        Receive one SCPI command from the VXI-11 client.

        Commands that end with "?" are treated as queries and delegated to
        the endpoint query method. Other commands are delegated as writes.

        Args:
            opaque_data: Raw bytes received from the VXI-11 client.
            flags: VXI-11 operation flags.
            io_timeout: Timeout from the VXI-11 client.

        Returns:
            error: VXI-11 error code. ERR_NO_ERROR on success.
        """
        error = vxi11.ERR_NO_ERROR

        # Decode safely. Instrument commands are expected ASCII.
        cmd = opaque_data.decode("ascii", errors="replace").strip()

        if not cmd:
            self._result = ""
            return error

        try:
            if cmd.endswith("?"):
                # Query path. The endpoint returns the simulator response.
                self._result = self._endpoint.query(cmd)
            else:
                # Write path. The endpoint returns no result.
                self._endpoint.write(cmd)
                self._result = ""
        except Exception:
            # Convert every endpoint failure into a controlled VXI-11 error.
            # The original exception is deliberately not exposed.
            self._result = ""
            error = vxi11.ERR_IO_ERROR

        return error

    def device_read(self, request_size, term_char, flags, io_timeout):
        """
        Return the last query response to the VXI-11 client.

        Args:
            request_size: Maximum bytes the client expects.
            term_char: Termination character requested by the client.
            flags: VXI-11 operation flags.
            io_timeout: Timeout from the VXI-11 client.

        Returns:
            Tuple of error, reason, opaque_data.
        """
        error = vxi11.ERR_NO_ERROR
        reason = vxi11.RX_END

        # Encode the stored response and clear it after read, matching the
        # default VXI-11 device behavior.
        opaque_data = self._result.encode("ascii")
        self._result = ""

        return error, reason, opaque_data