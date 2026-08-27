# File: src/transports/vxi11/acb_server.py
# Path: /d/Projects/autocalbridge/src/transports/vxi11/acb_server.py
# Purpose: ACB VXI-11 server bound to 127.0.0.1, backed by simulator endpoints.

"""
ACB VXI-11 server.

This server wraps the moved vxi11_server package and registers one or more
AcbDeviceHandler instances. Each handler is backed by a SimulatorEndpoint
created through EndpointFactory.

The server is a dev/test scaffold only. It is not part of the shipped
product.
"""

import logging

from src.transports.vxi11.vxi11_server import instrument_server as IS
from src.transports.vxi11.vxi11_server import vxi11
from src.transports.vxi11.vxi11_server.instrument_device import DefaultInstrumentDevice

from src.transports.vxi11.acb_device_handler import AcbDeviceHandler


class LocalAbortServer(IS.Vxi11AbortServer):
    """
    Bind the VXI-11 abort server to 127.0.0.1.

    On Windows, binding to '' can cause WinError 10049 during RPC
    registration. This class mirrors the verified POC behavior.
    """

    def __init__(self):
        IS.Vxi11Server.__init__(
            self,
            "127.0.0.1",
            vxi11.DEVICE_ASYNC_PROG,
            vxi11.DEVICE_ASYNC_VERS,
            0,
            IS.Vxi11AbortHandler,
        )


class LocalCoreServer(IS.Vxi11CoreServer):
    """
    Bind the VXI-11 core server to 127.0.0.1.
    """

    def __init__(self, abort_port):
        IS.Vxi11Server.__init__(
            self,
            "127.0.0.1",
            vxi11.DEVICE_CORE_PROG,
            vxi11.DEVICE_CORE_VERS,
            0,
            IS.Vxi11CoreHandler,
        )

        self.abort_port = abort_port


class AcbVxi11Server:
    """
    AutoCalBridge VXI-11 server.

    Wraps the moved VXI-11 package with local-only bindings and registers
    ACB device handlers backed by simulator endpoints.
    """

    def __init__(self):
        """
        Initialise the server without starting it.

        Device handlers are registered separately through add_device().
        """
        self._abort_server = LocalAbortServer()
        _, abort_port = self._abort_server.server_address

        self._core_server = LocalCoreServer(abort_port)

    def add_device(self, device_name, endpoint):
        """
        Register one simulator endpoint as a VXI-11 device.

        Args:
            device_name: VXI-11 device name, e.g. "inst0".
            endpoint: SimulatorEndpoint instance backing this device.
        """
        # AcbDeviceHandler needs the registry in its constructor, matching
        # the upstream DefaultInstrumentDevice factory pattern.
        def handler_factory(name, lock, registry):
            return AcbDeviceHandler(name, lock, registry, endpoint)

        self._core_server.device_register(device_name, handler_factory)

    def listen(self):
        """
        Start the abort and core servers.

        The core server registers itself with rpcbind. Both servers run as
        daemon threads so the caller can keep the main thread alive.
        """
        abort_thread = IS.threading.Thread(
            target=self._abort_server.serve_forever,
            daemon=True,
        )
        abort_thread.start()
        logging.info("abortServer started...")

        self._core_server.register()

        core_thread = IS.threading.Thread(
            target=self._core_server.serve_forever,
            daemon=True,
        )
        core_thread.start()
        logging.info("coreServer started...")

    def close(self):
        """
        Stop both servers and unregister from rpcbind.
        """
        logging.info("Closing...")

        for dev in list(self._core_server.device_list()):
            self._core_server.device_unregister(dev)

        self._core_server.unregister()
        self._core_server.shutdown()
        self._core_server.server_close()

        vxi11.IntrServer.stopServer()

        self._abort_server.shutdown()
        self._abort_server.server_close()

        logging.info("Closed.")