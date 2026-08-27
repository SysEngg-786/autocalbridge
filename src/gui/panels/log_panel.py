# File: src/gui/panels/log_panel.py
# Path: /d/Projects/autocalbridge/src/gui/panels/log_panel.py
# Purpose: Bottom log/audit panel using the existing LogTerminal widget.

import tkinter as tk
from tkinter import ttk

from src.gui.log_terminal import LogTerminal


class LogPanel(ttk.Frame):
    """Bottom panel wrapping the reusable LogTerminal."""

    def __init__(self, parent, height=10):
        super().__init__(parent, padding=5)
        self.log_terminal = LogTerminal(self, height=height)
        self.log_terminal.frame.pack(fill="both", expand=True)