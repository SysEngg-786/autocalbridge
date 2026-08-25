#!/usr/bin/env python3
"""
File: temp_test_server.py
Path: /d/Projects/autocalbridge/src/transports/vxi11/temp_test_server.py
Purpose: Temporary verification server for the moved VXI-11 transport.

         This script is intentionally minimal. It imports the moved
         vxi11_server package from src/transports/vxi11/vxi11_server/
         and starts the same LocalInstrumentServer model used in the
         known-good external POC.

         No product logic is included here. This is only to prove the
         moved package imports and runs at its new location.
"""

import time
import logging

from src.transports.vxi11.vxi11_server import instrument_server as IS
from src.transports.vxi11.vxi11_server import vxi11
from src.transports.vxi11.vxi11_server.instrument_device import (
    InstrumentDevice,
    ReadRespReason,
    DefaultInstrumentDevice,
)


class TimeDevice(InstrumentDevice):
    """
    Simple VXI-11 device returning the current UTC time on read.

    Kept identical to the external POC so the moved package can be
    verified without introducing new behavior.
    """

    def device_init(self):
        pass

    def device_read(self, request_size, term_char, flags, io_timeout):
        error = vxi11.ERR_NO_ERROR
        reason = ReadRespReason.END

        data = time.strftime("%H:%M:%S +0000", time.gmtime())
        opaque_data = data.encode("ascii")

        return error, reason, opaque_data


class LocalAbortServer(IS.Vxi11AbortServer):
    """
    Bind the VXI-11 abort server to 127.0.0.1.

    On Windows, host '' can cause WinError 10049 during RPC
    registration. This mirrors the external POC behavior.
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


class LocalInstrumentServer(IS.InstrumentServer):
    """
    InstrumentServer equivalent using the local bindings.
    """

    def __init__(self, default_device_handler=None, default_device_name="inst0"):
        self.abortServer = LocalAbortServer()
        _, abort_port = self.abortServer.server_address

        self.coreServer = LocalCoreServer(abort_port)

        if default_device_handler is None:
            default_device_handler = DefaultInstrumentDevice

        self.add_device_handler(default_device_handler, default_device_name)

    def add_device_handler(self, device_handler, device_name=None):
        self.coreServer.device_register(device_name, device_handler)
        return True

    def close(self):
        logging.info("Closing...")
        for dev in list(self.coreServer.device_list()):
            self.coreServer.device_unregister(dev)

        self.coreServer.unregister()
        self.coreServer.shutdown()
        self.coreServer.server_close()

        vxi11.IntrServer.stopServer()

        self.abortServer.shutdown()
        self.abortServer.server_close()
        logging.info("Closed.")

    def listen(self, loglevel="INFO"):
        abort_thread = IS.threading.Thread(
            target=self.abortServer.serve_forever,
            daemon=True,
        )
        abort_thread.start()
        logging.info("abortServer started...")

        self.coreServer.register()

        core_thread = IS.threading.Thread(
            target=self.coreServer.serve_forever,
            daemon=True,
        )
        core_thread.start()
        logging.info("coreServer started...")

        return True


def main():
    """
    Entry point for the temporary verification server.
    """
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("Temporary VXI-11 verification server")
    print("Host: 127.0.0.1")
    print("Device: inst0 (DefaultInstrumentDevice)")
    print("Device: inst1 (TimeDevice)")
    print("=" * 60)

    server = LocalInstrumentServer(
        default_device_handler=DefaultInstrumentDevice,
        default_device_name="inst0",
    )

    server.add_device_handler(TimeDevice, "inst1")

    try:
        server.listen()
        print("[READY] VXI-11 server is running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
        server.close()
        print("[INFO] Server stopped.")


if __name__ == "__main__":
    main()