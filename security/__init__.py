# File: security/__init__.py
# Path: /d/Projects/autocalbridge/security/__init__.py
# Purpose: Marks the AutoCalBridge security package.

"""
AutoCalBridge security package.

This package contains modular security components used at the instrument
endpoint boundary:

- command policy
- input validators
- secure configuration helpers
- audit logging helpers
- transport policy

Security components are intentionally separate from ACB business logic,
simulator logic, and instrument endpoint adapters.
"""