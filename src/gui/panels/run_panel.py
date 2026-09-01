# File: src/gui/panels/run_panel.py
# Path: /d/Projects/autocalbridge/src/gui/panels/run_panel.py
# Purpose: Active run panel with run control and future manual entry area.
#          Includes both session run and physical verification actions.

import tkinter as tk
from tkinter import ttk


class RunPanel(ttk.Frame):
    """Center panel for live run status and run actions."""

    def __init__(
        self,
        parent,
        on_run_callback=None,
        on_status=None,
        on_verification_callback=None,
    ):
        super().__init__(parent, padding=10)
        self.on_run_callback = on_run_callback
        self.on_status = on_status
        self.on_verification_callback = on_verification_callback
        self.is_running = False
        self.is_verifying = False

        self.create_widgets()

    def create_widgets(self):
        """Create run controls and status area."""
        ttk.Label(self, text="Run", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 5))

        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(self, textvariable=self.status_var, foreground="#666666")
        status_label.pack(anchor="w", pady=(0, 8))

        # Session run button
        self.run_button = ttk.Button(
            self,
            text="Run Selected Session",
            command=self.do_run,
            style="Accent.TButton",
        )
        self.run_button.pack(anchor="w", pady=(0, 8))

        # Physical verification button
        self.verify_button = ttk.Button(
            self,
            text="Run Frequency Verification",
            command=self.do_verification,
            style="Accent.TButton",
        )
        self.verify_button.pack(anchor="w", pady=(0, 8))

        # Future manual entry area placeholder
        manual_frame = ttk.LabelFrame(self, text="Manual Entry", padding=8)
        manual_frame.pack(fill="both", expand=True, pady=(8, 0))

        ttk.Label(
            manual_frame,
            text="Assisted calibration prompts will appear here.",
            foreground="#888888",
        ).pack(anchor="w")

    def do_run(self):
        """Invoke the session run callback if not already running."""
        if self.is_running or self.is_verifying:
            return

        if self.on_run_callback is None:
            self.status_var.set("Run callback not configured.")
            return

        self.set_running(True)
        try:
            self.on_run_callback()
        finally:
            self.set_running(False)

    def do_verification(self):
        """Invoke the physical verification callback if not already busy."""
        if self.is_running or self.is_verifying:
            return

        if self.on_verification_callback is None:
            self.status_var.set("Verification callback not configured.")
            return

        self.set_verifying(True)
        try:
            self.on_verification_callback()
        finally:
            self.set_verifying(False)

    def set_running(self, running):
        """Update running state and button states."""
        self.is_running = running
        self._update_button_states()

        if running:
            self.status_var.set("Running session...")
        else:
            if not self.is_verifying:
                self.status_var.set("Ready")

    def set_verifying(self, verifying):
        """Update verifying state and button states."""
        self.is_verifying = verifying
        self._update_button_states()

        if verifying:
            self.status_var.set("Running verification...")
        else:
            if not self.is_running:
                self.status_var.set("Ready")

    def _update_button_states(self):
        """Enable/disable buttons based on current state."""
        if self.is_running or self.is_verifying:
            self.run_button.config(state="disabled")
            self.verify_button.config(state="disabled")
        else:
            self.run_button.config(state="normal")
            self.verify_button.config(state="normal")

    def set_status(self, message):
        """Update the run panel status message."""
        self.status_var.set(message)