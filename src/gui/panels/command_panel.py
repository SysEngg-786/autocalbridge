# File: src/gui/panels/command_panel.py
# Path: /d/Projects/autocalbridge/src/gui/panels/command_panel.py
# Purpose: Command panel for clean SCPI command/query input and built-in checks.
#          Uses run_single_command so the response is returned and displayed
#          in the GUI log panel instead of printing only to the console.

import tkinter as tk
from tkinter import ttk

from src.cli.instrument_commands import (
    test_instrument,
    basic_check_instrument,
    write_check_instrument,
    diagnostics_instrument,
    run_single_command,
)


class CommandPanel(ttk.Frame):
    """Panel for sending clean SCPI commands and running built-in checks."""

    def __init__(self, parent, get_selected_instrument_id=None, log_panel=None, on_status=None):
        super().__init__(parent, padding=10)
        self.get_selected_instrument_id = get_selected_instrument_id
        self.log_panel = log_panel
        self.on_status = on_status

        self.create_widgets()

    def create_widgets(self):
        """Create command panel widgets."""
        ttk.Label(self, text="Command", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 5))

        # Selected instrument display
        self.selected_var = tk.StringVar(value="No instrument selected")
        ttk.Label(self, textvariable=self.selected_var, foreground="#666666").pack(anchor="w", pady=(0, 5))

        # Clean SCPI command input
        self.command_var = tk.StringVar()
        self.command_entry = ttk.Entry(self, textvariable=self.command_var, width=40)
        self.command_entry.pack(fill="x", pady=3)
        self.command_entry.bind("<Return>", lambda event: self.send_command())

        self.send_button = ttk.Button(self, text="Send Command", command=self.send_command)
        self.send_button.pack(anchor="w", pady=(3, 8))

        # Built-in checks row
        checks_frame = ttk.Frame(self)
        checks_frame.pack(fill="x", pady=(0, 8))

        self.test_button = ttk.Button(checks_frame, text="Test", command=self.run_test)
        self.test_button.pack(side="left", padx=(0, 5))

        self.basic_check_button = ttk.Button(checks_frame, text="Basic Check", command=self.run_basic_check)
        self.basic_check_button.pack(side="left", padx=(0, 5))

        self.write_check_button = ttk.Button(checks_frame, text="Write Check", command=self.run_write_check)
        self.write_check_button.pack(side="left", padx=(0, 5))

        self.diagnostics_button = ttk.Button(checks_frame, text="Diagnostics", command=self.run_diagnostics)
        self.diagnostics_button.pack(side="left")

    def _current_instrument_id(self):
        """Return the currently selected instrument ID, or empty string."""
        if self.get_selected_instrument_id is None:
            return ""
        return self.get_selected_instrument_id().strip()

    def _set_selected_display(self):
        """Update the selected instrument label."""
        entry_id = self._current_instrument_id()
        if entry_id:
            self.selected_var.set(f"Instrument: {entry_id}")
        else:
            self.selected_var.set("No instrument selected")

    def _require_instrument(self):
        """Return instrument ID if available, else show error and return None."""
        entry_id = self._current_instrument_id()
        if not entry_id:
            self.log("No instrument selected.", "ERROR")
            if self.on_status:
                self.on_status("No instrument selected")
            return None
        return entry_id

    def log(self, message, level="INFO"):
        """Send a message to the shared log panel if available."""
        if self.log_panel is not None:
            self.log_panel.log_terminal.log(message, level)

    def send_command(self):
        """Send the clean SCPI command/query to the selected instrument.

        Uses run_single_command, which returns (success, response). The
        response is displayed directly in the GUI log panel.
        """
        self._set_selected_display()
        entry_id = self._require_instrument()
        if not entry_id:
            return

        command = self.command_var.get().strip()
        if not command:
            self.log("Command is empty.", "WARNING")
            return

        self.log(f"Sending to {entry_id}: {command}")

        success, response = run_single_command(entry_id, command)

        if success:
            if response:
                self.log(f"Response: {response}", "SUCCESS")
            else:
                self.log("Command sent.", "SUCCESS")
            if self.on_status:
                self.on_status("Command sent")
        else:
            self.log(f"Command failed: {response}", "ERROR")
            if self.on_status:
                self.on_status("Command failed")

    def run_test(self):
        """Run the built-in connectivity test and log the response."""
        self._set_selected_display()
        entry_id = self._require_instrument()
        if not entry_id:
            return
        self.log(f"Running test on {entry_id} ...")
        success, response = run_single_command(entry_id, "*IDN?")
        if success:
            self.log(f"Test passed. IDN: {response}", "SUCCESS")
            if self.on_status:
                self.on_status(f"Instrument: {entry_id} | Status: Connected", "SUCCESS")
        else:
            self.log(f"Test failed: {response}", "ERROR")
            if self.on_status:
                self.on_status(f"Instrument: {entry_id} | Status: Failed", "ERROR")

    def run_basic_check(self):
        """Run the built-in basic read-only check and log the response."""
        self._set_selected_display()
        entry_id = self._require_instrument()
        if not entry_id:
            return
        self.log(f"Running basic check on {entry_id} ...")

        commands = ["*IDN?", "*ESR?", "*STB?", "SYST:ERR?", "SYST:ERR:ALL?"]
        failed = False
        for cmd in commands:
            success, response = run_single_command(entry_id, cmd)
            if success:
                self.log(f"{cmd} -> {response}", "INFO")
            else:
                self.log(f"{cmd} -> ERROR: {response}", "ERROR")
                failed = True

        if failed:
            if self.on_status:
                self.on_status(f"Instrument: {entry_id} | Status: Basic check failed", "ERROR")
        else:
            if self.on_status:
                self.on_status(f"Instrument: {entry_id} | Status: Basic check passed", "SUCCESS")

    def run_write_check(self):
        """Run the built-in write path check and log the response."""
        self._set_selected_display()
        entry_id = self._require_instrument()
        if not entry_id:
            return
        self.log(f"Running write check on {entry_id} ...")

        write_commands = ["*CLS", "*WAI", "ACQ:STAT RUN", "CHAN1:STAT ON", "CHAN1:SCAL 0.01", "TIM:SCAL 0.001", "TIM:POS 0"]
        failed = False
        for cmd in write_commands:
            success, response = run_single_command(entry_id, cmd)
            if success:
                # Check error queue after write
                err_success, err_response = run_single_command(entry_id, "SYST:ERR?")
                if err_success and err_response.startswith("0,"):
                    self.log(f"WRITE {cmd} -> sent, no error", "INFO")
                else:
                    self.log(f"WRITE {cmd} -> sent, error: {err_response}", "ERROR")
                    failed = True
            else:
                self.log(f"WRITE {cmd} -> ERROR: {response}", "ERROR")
                failed = True

        if failed:
            if self.on_status:
                self.on_status(f"Instrument: {entry_id} | Status: Write check failed", "ERROR")
        else:
            if self.on_status:
                self.on_status(f"Instrument: {entry_id} | Status: Write check passed", "SUCCESS")

    def run_diagnostics(self):
        """Run the built-in diagnostics checks and log the response."""
        self._set_selected_display()
        entry_id = self._require_instrument()
        if not entry_id:
            return
        self.log(f"Running diagnostics on {entry_id} ...")

        diagnostic_commands = ["SYST:ERR:ALL?", "*ESR?", "*STB?", "STAT:OPER:EVEN?", "STAT:QUES:EVEN?", "*OPT?"]
        failed = False
        for cmd in diagnostic_commands:
            success, response = run_single_command(entry_id, cmd)
            if success:
                self.log(f"{cmd} -> {response}", "INFO")
            else:
                self.log(f"{cmd} -> ERROR: {response}", "ERROR")
                failed = True

        if failed:
            if self.on_status:
                self.on_status(f"Instrument: {entry_id} | Status: Diagnostics failed", "ERROR")
        else:
            if self.on_status:
                self.on_status(f"Instrument: {entry_id} | Status: Diagnostics passed", "SUCCESS")