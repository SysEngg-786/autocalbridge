# File: src/gui/panels/run_panel.py
# Path: /d/Projects/autocalbridge/src/gui/panels/run_panel.py
# Purpose: Active run panel with run control and future manual entry area.
#          Includes session run, physical frequency verification, and
#          waveform spot check actions.
#          Actions run in background threads so animation stays responsive.

import time
import tkinter as tk
from tkinter import ttk

from src.gui.threading_utils import run_in_background


class RunPanel(ttk.Frame):
    """Center panel for live run status and run actions."""

    MIN_PROGRESS_VISIBLE_SECONDS = 0.8
    BANNER_DURATION_MS = 6000
    ANIMATION_INTERVAL_MS = 350

    def __init__(
        self,
        parent,
        on_run_callback=None,
        on_status=None,
        on_verification_callback=None,
        on_spot_check_callback=None,
    ):
        super().__init__(parent, padding=10)
        self.on_run_callback = on_run_callback
        self.on_status = on_status
        self.on_verification_callback = on_verification_callback
        self.on_spot_check_callback = on_spot_check_callback
        self.is_running = False
        self.is_verifying = False
        self.is_spot_checking = False
        self._banner_after_id = None
        self._animation_after_id = None
        self._animation_dots = 0

        self.create_widgets()

    def _create_action_button(self, parent, text, command):
        """Create a raised 3D-style action button."""
        return tk.Button(
            parent,
            text=text,
            command=command,
            relief="raised",
            bd=3,
            bg="#d9d9d9",
            activebackground="#b3b3b3",
            activeforeground="#000000",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=4,
        )

    def create_widgets(self):
        """Create run controls and status area."""
        ttk.Label(self, text="Run", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 5))

        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(self, textvariable=self.status_var, foreground="#666666")
        status_label.pack(anchor="w", pady=(0, 5))

        # Indeterminate progress bar, hidden until a run action starts.
        self.progress = ttk.Progressbar(self, mode="indeterminate", length=280)

        # Animated running-dot label, hidden by default.
        self.animation_label = tk.Label(
            self,
            text="",
            fg="#003366",
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        )

        # Session run button
        self.run_button = self._create_action_button(
            self,
            text="Run Selected Session",
            command=self.do_run,
        )
        self.run_button.pack(anchor="w", pady=(0, 8))

        # Physical verification button
        self.verify_button = self._create_action_button(
            self,
            text="Run Frequency Verification",
            command=self.do_verification,
        )
        self.verify_button.pack(anchor="w", pady=(0, 8))

        # Waveform spot check section
        spot_frame = ttk.LabelFrame(self, text="Waveform Spot Check", padding=8)
        spot_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(spot_frame, text="Waveform:").grid(row=0, column=0, sticky="w", pady=2)
        self.waveform_var = tk.StringVar(value="SIN")
        self.waveform_combo = ttk.Combobox(
            spot_frame,
            textvariable=self.waveform_var,
            values=["SIN", "SQU", "RAMP", "PULS", "NOIS"],
            state="readonly",
            width=10,
        )
        self.waveform_combo.grid(row=0, column=1, sticky="w", pady=2, padx=(5, 0))

        ttk.Label(spot_frame, text="Frequency (Hz):").grid(row=1, column=0, sticky="w", pady=2)
        self.spot_freq_var = tk.StringVar(value="10000")
        ttk.Entry(spot_frame, textvariable=self.spot_freq_var, width=15).grid(
            row=1, column=1, sticky="w", pady=2, padx=(5, 0)
        )

        ttk.Label(spot_frame, text="Amplitude (Vpp):").grid(row=2, column=0, sticky="w", pady=2)
        self.spot_ampl_var = tk.StringVar(value="1.0")
        ttk.Entry(spot_frame, textvariable=self.spot_ampl_var, width=15).grid(
            row=2, column=1, sticky="w", pady=2, padx=(5, 0)
        )

        self.spot_check_button = self._create_action_button(
            spot_frame,
            text="Run Spot Check",
            command=self.do_spot_check,
        )
        self.spot_check_button.grid(row=2, column=2, sticky="w", pady=2, padx=(15, 0))

        ttk.Label(spot_frame, text="Offset (V):").grid(row=3, column=0, sticky="w", pady=2)
        self.spot_offset_var = tk.StringVar(value="0.0")
        ttk.Entry(spot_frame, textvariable=self.spot_offset_var, width=15).grid(
            row=3, column=1, sticky="w", pady=2, padx=(5, 0)
        )

        # Inline completion banner below all action controls.
        self.banner_label = tk.Label(
            self,
            text="",
            bg="#ffffff",
            fg="#000000",
            anchor="center",
            padx=8,
            pady=6,
            font=("Segoe UI", 11, "bold"),
            bd=2,
            relief="solid",
        )

        # Future manual entry area placeholder
        manual_frame = ttk.LabelFrame(self, text="Manual Entry", padding=8)
        manual_frame.pack(fill="both", expand=True, pady=(8, 0))

        ttk.Label(
            manual_frame,
            text="Assisted calibration prompts will appear here.",
            foreground="#888888",
        ).pack(anchor="w")

    def start_progress(self):
        """Show and start progress bar plus animated running dots."""
        if not self.progress.winfo_manager():
            self.progress.pack(fill="x", pady=(0, 5))
        self.progress.start(12)

        self._animation_dots = 0
        if not self.animation_label.winfo_manager():
            self.animation_label.pack(anchor="w", pady=(0, 5))
        self._animate_dots()

    def _animate_dots(self):
        """Animate a running dots indicator."""
        self._animation_dots = (self._animation_dots % 3) + 1
        dots = "." * self._animation_dots
        self.animation_label.config(text=f"Running{dots}")
        self._animation_after_id = self.after(
            self.ANIMATION_INTERVAL_MS,
            self._animate_dots,
        )

    def stop_progress(self):
        """Stop and hide progress bar and animation."""
        self.progress.stop()

        if self._animation_after_id is not None:
            try:
                self.after_cancel(self._animation_after_id)
            except Exception:
                pass
            self._animation_after_id = None

        if self.animation_label.winfo_manager():
            self.animation_label.pack_forget()

        elapsed = 0.0
        step = 0.02
        while elapsed < self.MIN_PROGRESS_VISIBLE_SECONDS:
            self.update_idletasks()
            time.sleep(step)
            elapsed += step

        if self.progress.winfo_manager():
            self.progress.pack_forget()

    def show_banner(self, message, level="SUCCESS"):
        """Show an inline banner below the action buttons."""
        colors = {
            "SUCCESS": "#d9f2d9",
            "ERROR": "#f2d9d9",
        }
        fg = {
            "SUCCESS": "#006600",
            "ERROR": "#990000",
        }.get(level, "#000000")

        bg = colors.get(level, "#ffffff")

        if self._banner_after_id is not None:
            try:
                self.after_cancel(self._banner_after_id)
            except Exception:
                pass
            self._banner_after_id = None

        self.banner_label.config(
            text=message,
            bg=bg,
            fg=fg,
        )
        self.banner_label.pack(fill="x", pady=(0, 5))

        self._banner_after_id = self.after(
            self.BANNER_DURATION_MS,
            self.hide_banner,
        )

    def hide_banner(self):
        """Hide the inline completion banner."""
        self.banner_label.pack_forget()
        self._banner_after_id = None

    def do_run(self):
        """Invoke the session run callback in background."""
        if self.is_running or self.is_verifying or self.is_spot_checking:
            return

        if self.on_run_callback is None:
            self.status_var.set("Run callback not configured.")
            return

        self.set_running(True)
        self.start_progress()

        def done(_result):
            self.stop_progress()
            self.set_running(False)

        def error(exc):
            self.stop_progress()
            self.set_running(False)
            self.show_banner(f"Run failed: {exc}", "ERROR")

        run_in_background(
            self,
            self.on_run_callback,
            on_success=done,
            on_error=error,
        )

    def do_verification(self):
        """Invoke physical verification callback in background."""
        if self.is_running or self.is_verifying or self.is_spot_checking:
            return

        if self.on_verification_callback is None:
            self.status_var.set("Verification callback not configured.")
            return

        self.set_verifying(True)
        self.start_progress()

        def done(_result):
            self.stop_progress()
            self.set_verifying(False)

        def error(exc):
            self.stop_progress()
            self.set_verifying(False)
            self.show_banner(f"Verification failed: {exc}", "ERROR")

        run_in_background(
            self,
            self.on_verification_callback,
            on_success=done,
            on_error=error,
        )

    def do_spot_check(self):
        """Invoke waveform spot check callback in background."""
        if self.is_running or self.is_verifying or self.is_spot_checking:
            return

        if self.on_spot_check_callback is None:
            self.status_var.set("Spot check callback not configured.")
            return

        self.set_spot_checking(True)
        self.start_progress()

        def done(_result):
            self.stop_progress()
            self.set_spot_checking(False)

        def error(exc):
            self.stop_progress()
            self.set_spot_checking(False)
            self.show_banner(f"Spot check failed: {exc}", "ERROR")

        run_in_background(
            self,
            self.on_spot_check_callback,
            on_success=done,
            on_error=error,
        )

    def set_running(self, running):
        self.is_running = running
        self._update_button_states()
        if running:
            self.status_var.set("Running session...")
        elif not self.is_verifying and not self.is_spot_checking:
            self.status_var.set("Ready")

    def set_verifying(self, verifying):
        self.is_verifying = verifying
        self._update_button_states()
        if verifying:
            self.status_var.set("Running verification...")
        elif not self.is_running and not self.is_spot_checking:
            self.status_var.set("Ready")

    def set_spot_checking(self, checking):
        self.is_spot_checking = checking
        self._update_button_states()
        if checking:
            self.status_var.set("Running spot check...")
        elif not self.is_running and not self.is_verifying:
            self.status_var.set("Ready")

    def _update_button_states(self):
        busy = self.is_running or self.is_verifying or self.is_spot_checking
        state = "disabled" if busy else "normal"
        self.run_button.config(state=state)
        self.verify_button.config(state=state)
        self.spot_check_button.config(state=state)

    def set_status(self, message):
        self.status_var.set(message)