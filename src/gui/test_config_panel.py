# File: src/gui/test_config_panel.py
# Path: /autocalbridge/src/gui/test_config_panel.py
# Purpose: Test configuration panel for AutoCalBridge GUI.

import tkinter as tk
from tkinter import ttk


class TestConfigPanel:
    """Test configuration panel."""

    def __init__(self, parent, on_run_callback=None, on_stop_callback=None):
        """Initialize the test configuration panel.

        Args:
            parent: Parent widget
            on_run_callback: Function to call when Run is clicked
            on_stop_callback: Function to call when Stop is clicked
        """
        self.parent = parent
        self.on_run_callback = on_run_callback
        self.on_stop_callback = on_stop_callback
        self.is_running = False

        self.create_widgets()

    def create_widgets(self):
        """Create the test configuration widgets."""
        # Frame
        self.frame = ttk.LabelFrame(self.parent, text="Test Configuration", padding=10)
        self.frame.pack(fill="x", pady=5)

        # Test points
        ttk.Label(self.frame, text="Test Points (V):").grid(row=0, column=0, sticky="w", pady=2)
        self.points_entry = ttk.Entry(self.frame, width=30)
        self.points_entry.insert(0, "1.0, 2.5, 5.0, 10.0")
        self.points_entry.grid(row=0, column=1, sticky="ew", pady=2, padx=(5, 0))

        # Tolerance
        ttk.Label(self.frame, text="Tolerance (V):").grid(row=1, column=0, sticky="w", pady=2)
        self.tolerance_entry = ttk.Entry(self.frame, width=10)
        self.tolerance_entry.insert(0, "0.005")
        self.tolerance_entry.grid(row=1, column=1, sticky="w", pady=2, padx=(5, 0))

        # Duration
        ttk.Label(self.frame, text="Duration (s):").grid(row=2, column=0, sticky="w", pady=2)
        self.duration_entry = ttk.Entry(self.frame, width=10)
        self.duration_entry.insert(0, "5.0")
        self.duration_entry.grid(row=2, column=1, sticky="w", pady=2, padx=(5, 0))

        # Interval
        ttk.Label(self.frame, text="Interval (s):").grid(row=3, column=0, sticky="w", pady=2)
        self.interval_entry = ttk.Entry(self.frame, width=10)
        self.interval_entry.insert(0, "0.1")
        self.interval_entry.grid(row=3, column=1, sticky="w", pady=2, padx=(5, 0))

        # Operator name
        ttk.Label(self.frame, text="Operator:").grid(row=4, column=0, sticky="w", pady=2)
        self.operator_entry = ttk.Entry(self.frame, width=20)
        self.operator_entry.insert(0, "Default_Operator")
        self.operator_entry.grid(row=4, column=1, sticky="w", pady=2, padx=(5, 0))

        # Control buttons
        self.button_frame = ttk.Frame(self.frame)
        self.button_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky="ew")

        self.run_btn = ttk.Button(
            self.button_frame,
            text="Run Test",
            command=self.do_run,
            state="normal"
        )
        self.run_btn.pack(side="left", padx=(0, 5))

        self.stop_btn = ttk.Button(
            self.button_frame,
            text="Stop",
            command=self.do_stop,
            state="disabled"
        )
        self.stop_btn.pack(side="left")

        # Progress
        self.progress_var = tk.StringVar(value="Ready")
        self.progress_label = ttk.Label(self.frame, textvariable=self.progress_var)
        self.progress_label.grid(row=6, column=0, columnspan=2, sticky="w", pady=2)

        # Make grid columns expand
        self.frame.columnconfigure(1, weight=1)

    def do_run(self):
        """Handle Run button click."""
        if self.is_running:
            return

        # Validate inputs
        try:
            points_text = self.points_entry.get().strip()
            points = [float(x.strip()) for x in points_text.split(",")]
            tolerance = float(self.tolerance_entry.get().strip())
            duration = float(self.duration_entry.get().strip())
            interval = float(self.interval_entry.get().strip())
            operator = self.operator_entry.get().strip()

            if not points:
                raise ValueError("At least one test point required")
            if tolerance <= 0:
                raise ValueError("Tolerance must be positive")
            if duration <= 0:
                raise ValueError("Duration must be positive")
            if interval <= 0:
                raise ValueError("Interval must be positive")

        except ValueError as e:
            self.progress_var.set(f"Error: {e}")
            return

        self.is_running = True
        self.run_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress_var.set("Running...")

        # Notify parent
        if self.on_run_callback:
            self.on_run_callback({
                "points": points,
                "tolerance": tolerance,
                "duration": duration,
                "interval": interval,
                "operator": operator
            })

    def do_stop(self):
        """Handle Stop button click."""
        self.is_running = False
        self.run_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.progress_var.set("Stopped")

        # Notify parent
        if self.on_stop_callback:
            self.on_stop_callback()

    def on_complete(self):
        """Called when test completes."""
        self.is_running = False
        self.run_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.progress_var.set("Complete")

    def on_progress(self, message):
        """Update progress message."""
        self.progress_var.set(message)

    def get_config(self):
        """Get the current test configuration."""
        points_text = self.points_entry.get().strip()
        points = [float(x.strip()) for x in points_text.split(",")]
        return {
            "points": points,
            "tolerance": float(self.tolerance_entry.get().strip()),
            "duration": float(self.duration_entry.get().strip()),
            "interval": float(self.interval_entry.get().strip()),
            "operator": self.operator_entry.get().strip()
        }