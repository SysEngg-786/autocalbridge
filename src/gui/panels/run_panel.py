# File: src/gui/panels/run_panel.py
# Path: /d/Projects/autocalbridge/src/gui/panels/run_panel.py
# Purpose: Active run panel with run control and future manual entry area.

import tkinter as tk
from tkinter import ttk


class RunPanel(ttk.Frame):
    """Center panel for live run status and manual entry area."""

    def __init__(self, parent, on_run_callback=None, on_status=None):
        super().__init__(parent, padding=10)
        self.on_run_callback = on_run_callback
        self.on_status = on_status
        self.is_running = False

        self.create_widgets()

    def create_widgets(self):
        """Create run controls and status area."""
        ttk.Label(self, text="Run", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 5))

        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(self, textvariable=self.status_var, foreground="#666666")
        status_label.pack(anchor="w", pady=(0, 8))

        self.run_button = ttk.Button(
            self,
            text="Run Selected Session",
            command=self.do_run,
            style="Accent.TButton",
        )
        self.run_button.pack(anchor="w", pady=(0, 8))

        # Future manual entry area placeholder
        manual_frame = ttk.LabelFrame(self, text="Manual Entry", padding=8)
        manual_frame.pack(fill="both", expand=True, pady=(8, 0))

        ttk.Label(
            manual_frame,
            text="Assisted calibration prompts will appear here.",
            foreground="#888888",
        ).pack(anchor="w")

    def do_run(self):
        """Invoke the run callback if not already running."""
        if self.is_running:
            return

        if self.on_run_callback is None:
            self.status_var.set("Run callback not configured.")
            return

        self.set_running(True)
        try:
            self.on_run_callback()
        finally:
            self.set_running(False)

    def set_running(self, running):
        """Update running state and button text."""
        self.is_running = running
        if running:
            self.run_button.config(state="disabled")
            self.status_var.set("Running...")
        else:
            self.run_button.config(state="normal")
            self.status_var.set("Ready")

    def set_status(self, message):
        """Update the run panel status message."""
        self.status_var.set(message)