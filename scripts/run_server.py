#!/usr/bin/env python3
"""
File: scripts/run_server.py
Path: /d/Projects/autocalbridge/scripts/run_server.py
Purpose: Start the ACB VXI-11 server with simulator endpoints.

         Step 2: Uses EndpointFactory to create simulator endpoints from
         YAML profiles and registers them as VXI-11 devices.

         Debug logging is enabled for the VXI-11 server so we can observe
         exactly what RSCommander sends during discovery and connection.
"""

import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.endpoints.endpoint_factory import create_from_resource_string
from src.transports.vxi11.acb_server import AcbVxi11Server
from src.transports.vxi11.acb_device_handler import AcbDeviceHandler


def main():
    """
    Start the ACB VXI-11 server with simulator endpoint devices.
    """
    logging.basicConfig(level=logging.INFO)

    # Enable debug logging for the VXI-11 server internals so we can see
    # every RPC request and link-create attempt from RSCommander.
    logging.getLogger("src.transports.vxi11.vxi11_server").setLevel(logging.DEBUG)
    logging.getLogger("src.transports.vxi11.vxi11_server.rpc").setLevel(logging.DEBUG)
    logging.getLogger("src.transports.vxi11.vxi11_server.instrument_server").setLevel(logging.DEBUG)

    print("=" * 60)
    print("AutoCalBridge VXI-11 Server — Step 2 with debug logging")
    print("Host: 127.0.0.1")
    print("Device: inst0 (sim://keysight_source)")
    print("Device: inst1 (sim://keysight_34461a)")
    print("=" * 60)

    # Create simulator endpoints through the standard factory.
    # Each endpoint carries its own CommandPolicy from the YAML profile.
    source_endpoint = create_from_resource_string("sim://keysight_source")
    dut_endpoint = create_from_resource_string("sim://keysight_34461a")

    # Open both endpoints with their logical resource strings.
    source_endpoint.open("sim://keysight_source")
    dut_endpoint.open("sim://keysight_34461a")

    # The VXI-11 registry instantiates device classes with three arguments:
    # (device_name, device_lock, registry). Therefore we define subclasses
    # with the endpoint already bound at construction time.
    class SourceDevice(AcbDeviceHandler):
        def __init__(self, device_name, device_lock, registry):
            super().__init__(device_name, device_lock, registry, source_endpoint)

    class DutDevice(AcbDeviceHandler):
        def __init__(self, device_name, device_lock, registry):
            super().__init__(device_name, device_lock, registry, dut_endpoint)

    server = AcbVxi11Server()

    # Register the device classes, not factory functions.
    server._core_server.device_register("inst0", SourceDevice)
    server._core_server.device_register("inst1", DutDevice)

    try:
        server.listen()
        print("[READY] VXI-11 server is running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
        server.close()
        source_endpoint.close()
        dut_endpoint.close()
        print("[INFO] Server stopped.")


if __name__ == "__main__":
    main()