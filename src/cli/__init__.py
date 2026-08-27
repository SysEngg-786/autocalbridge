# File: src/cli/__init__.py
# Path: /d/Projects/autocalbridge/src/cli/__init__.py
# Purpose: Command-line interface package for AutoCalBridge.
#          Contains modular command implementations separated from thin
#          runnable scripts, so CICD and GUI layers can import and reuse
#          command logic without subprocess calls.