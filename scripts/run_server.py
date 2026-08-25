#!/usr/bin/env python3
"""
File: scripts/run_server.py
Path: /d/Projects/autocalbridge/scripts/run_server.py
Purpose: Start the VXI-11 server for AutoCalBridge.
"""

import sys
import os
import time
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.vxi11_server.instrument_server import InstrumentServer
from src.vxi11_server.instrument_device import DefaultInstrumentDevice


def main():
    # Set logging to see what's happening
    logging.basicConfig(level=logging.INFO)

    # ========================================================================
    # MONKEY-PATCH: Skip RPC portmapper registration on Windows
    # ========================================================================
    if sys.platform == 'win32':
        print("[PATCH] Skipping RPC portmapper registration (Windows)")
        from src.vxi11_server.rpc import TCPServer
        import logging as log

        def register_patch(self):
            log.info('Skipping RPC portmapper registration (Windows)')
            self.registered = True
            return

        TCPServer.register = register_patch

    print("=" * 60)
    print("AutoCalBridge VXI-11 Server — Simple Test")
    print("=" * 60)

    # Create server with default device (inst0)
    server = InstrumentServer(
        default_device_handler=DefaultInstrumentDevice,
        default_device_name='inst0'
    )

    print("\n[INFO] Server created.")
    print("[INFO] Device registered: inst0")
    print("[INFO] IDN response: python-vxi11-server,bbb,1234,567")
    print("\n[INFO] Starting VXI-11 server...")
    print("  - Core server: TCP port 1024")
    print("  - Abort server: TCP port 1025")
    print("\n[READY] Server is running. Press Ctrl+C to stop.\n")
    print("=" * 60)

    try:
        # Start the server (daemon threads)
        server.listen()

        # Keep main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
        server.close()
        print("[INFO] Server stopped.")


if __name__ == "__main__":
    main()