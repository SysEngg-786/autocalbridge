# File: src/core/endpoints/__init__.py
# Path: /d/Projects/autocalbridge/src/core/endpoints/__init__.py
# Purpose: Marks the AutoCalBridge endpoint subpackage.

"""
AutoCalBridge instrument endpoint package.

This package contains the neutral instrument endpoint contract, adapters, and
the endpoint factory. ACB code must depend only on the contract defined in
instrument_endpoint.py, never on a specific adapter or transport implementation.

The endpoint package is intentionally separate from existing core files such as
visa_manager.py and test_engine.py. This keeps the seam clean and lets physical,
simulated, and future transport-backed endpoints grow independently.
"""