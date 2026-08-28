# File: src/gui/panels/setup_panel.py
# Path: /d/Projects/autocalbridge/src/gui/panels/setup_panel.py
# Purpose: Setup panel for instrument, session, and procedure selection.
#          Shows physical instruments by default; simulators are hidden
#          unless the operator explicitly enables "Show simulators".
#          Instrument dropdown and Refresh button share one row.
#          Test Connection button is below the dropdown row.
#          Network Setup button is a placeholder for future work.
#          Updates the top status bar with instrument and connection state.

import os
import tkinter as tk
from tkinter import ttk

from src.utils.instrument_registry import load_registry
from src.cli.common import open_endpoint_for_entry
from src.core.endpoints.instrument_endpoint import InstrumentEndpointError

# Directories used for session and procedure file discovery.
SESSIONS_DIR = "config/sessions"
PROCEDURES_DIR = "config/procedures"


class SetupPanel(ttk.Frame):
    """Left panel for instrument, session, and procedure setup."""

    def __init__(self, parent, on_status=None, log_panel=None):
        super().__init__(parent, padding=10)
        self.on_status = on_status
        self.log_panel = log_panel
        self.registry = None

        # Display-name to actual registry ID mapping.
        self._instrument_display_to_id = {}
        self._instrument_id_to_display = {}

        self.create_widgets()
        self.refresh_all()

    def create_widgets(self):
        """Create setup panel widgets."""
        # Header
        ttk.Label(self, text="Setup", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))

        # Instrument section
        ttk.Label(self, text="Instrument", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 3))

        # Row containing dropdown and Refresh button (same line).
        instrument_row = ttk.Frame(self)
        instrument_row.pack(fill="x", pady=(0, 3))

        self.instrument_var = tk.StringVar()
        self.instrument_combo = ttk.Combobox(
            instrument_row,
            textvariable=self.instrument_var,
            state="readonly",
            width=22
        )
        self.instrument_combo.pack(side="left", fill="x", expand=True, padx=(0, 3))
        self.instrument_combo.bind("<<ComboboxSelected>>", self.on_instrument_selected)

        self.refresh_button = ttk.Button(
            instrument_row,
            text="Refresh",
            command=self.refresh_instruments,
            width=8
        )
        self.refresh_button.pack(side="left")

        # Test Connection button below the row.
        self.test_button = ttk.Button(
            self,
            text="Test Connection",
            command=self.test_selected_instrument,
            state="disabled"
        )
        self.test_button.pack(fill="x", pady=(0, 3))

        # Show simulators toggle. Default is off.
        self.show_simulators_var = tk.BooleanVar(value=False)
        self.show_simulators_check = ttk.Checkbutton(
            self,
            text="Show simulators",
            variable=self.show_simulators_var,
            command=self.refresh_instruments
        )
        self.show_simulators_check.pack(anchor="w", pady=(0, 3))

        # Network Setup placeholder button.
        self.network_setup_button = ttk.Button(
            self,
            text="Network Setup...",
            command=self.network_setup,
        )
        self.network_setup_button.pack(fill="x", pady=(0, 8))

        # Instrument info label
        self.instrument_info_label = ttk.Label(
            self,
            text="No instrument selected.",
            foreground="#666666",
            wraplength=220,
            justify="left"
        )
        self.instrument_info_label.pack(anchor="w", pady=(0, 8))

        # Separator
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=8)

        # Session section
        ttk.Label(self, text="Session", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 3))

        self.session_var = tk.StringVar()
        self.session_combo = ttk.Combobox(
            self,
            textvariable=self.session_var,
            state="readonly",
            width=28
        )
        self.session_combo.pack(fill="x", pady=2)

        ttk.Button(
            self,
            text="Refresh Sessions",
            command=self.refresh_sessions
        ).pack(anchor="w", pady=(2, 8))

        # Separator
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=8)

        # Procedure section
        ttk.Label(self, text="Procedure", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 3))

        self.procedure_var = tk.StringVar()
        self.procedure_combo = ttk.Combobox(
            self,
            textvariable=self.procedure_var,
            state="readonly",
            width=28
        )
        self.procedure_combo.pack(fill="x", pady=2)

        ttk.Button(
            self,
            text="Refresh Procedures",
            command=self.refresh_procedures
        ).pack(anchor="w", pady=(2, 8))

    def log(self, message, level="INFO"):
        """Route a message to the log panel if available."""
        if self.log_panel is not None:
            self.log_panel.log_terminal.log(message, level)

    def set_status(self, message, level="INFO"):
        """Update the top status bar if callback exists."""
        if self.on_status is not None:
            self.on_status(message, level)

    def network_setup(self):
        """Placeholder for future network setup panel."""
        self.log("Network Setup is not implemented yet.", "WARNING")
        self.set_status("Network Setup not implemented", "WARNING")

    def refresh_all(self):
        """Refresh all dropdowns and current selection state."""
        self.refresh_instruments()
        self.refresh_sessions()
        self.refresh_procedures()

    def refresh_instruments(self):
        """Load registered instrument IDs into the combobox.

        By default only physical instruments are shown. Virtual instruments
        are included only when "Show simulators" is enabled.
        """
        try:
            self.registry = load_registry()
        except Exception as exc:
            self.log(f"Registry load failed: {exc}", "ERROR")
            self.set_status("Registry load failed", "ERROR")
            return

        show_simulators = self.show_simulators_var.get()

        display_items = []
        self._instrument_display_to_id = {}
        self._instrument_id_to_display = {}

        for entry in self.registry:
            if entry.kind == "virtual" and not show_simulators:
                continue

            if entry.kind == "virtual":
                display = f"{entry.id} [virtual]"
            else:
                display = entry.id

            display_items.append(display)
            self._instrument_display_to_id[display] = entry.id
            self._instrument_id_to_display[entry.id] = display

        self.instrument_combo["values"] = display_items

        if display_items:
            current = self.instrument_var.get()
            if current not in self._instrument_display_to_id:
                self.instrument_var.set(display_items[0])
                self.on_instrument_selected()
        else:
            self.instrument_var.set("")
            self.instrument_info_label.config(text="No instruments available.")
            self.test_button.config(state="disabled")

    def refresh_sessions(self):
        """Load available session file names into the combobox."""
        files = self._list_yaml_files(SESSIONS_DIR)
        self.session_combo["values"] = files
        if files and self.session_var.get() not in files:
            self.session_var.set(files[0])

    def refresh_procedures(self):
        """Load available procedure file names into the combobox."""
        files = self._list_yaml_files(PROCEDURES_DIR)
        self.procedure_combo["values"] = files
        if files and self.procedure_var.get() not in files:
            self.procedure_var.set(files[0])

    def _list_yaml_files(self, directory):
        """Return sorted .yaml filenames from a directory."""
        if not os.path.isdir(directory):
            return []
        return sorted(
            [f for f in os.listdir(directory) if f.endswith(".yaml")]
        )

    def get_selected_instrument_id(self):
        """Return the actual registry ID for the selected display name."""
        display = self.instrument_var.get()
        return self._instrument_display_to_id.get(display, "")

    def on_instrument_selected(self, event=None):
        """Update instrument info label, test button state, and top status."""
        entry_id = self.get_selected_instrument_id()
        if not entry_id or self.registry is None:
            self.test_button.config(state="disabled")
            return

        entry = self.registry.get(entry_id)
        if entry is None:
            self.instrument_info_label.config(text="Instrument not found.")
            self.test_button.config(state="disabled")
            return

        info = (
            f"ID: {entry.id}\n"
            f"Kind: {entry.kind}\n"
            f"Profile: {entry.profile}\n"
            f"Connection: {entry.connection}\n"
            f"Display: {entry.display_name}"
        )
        self.instrument_info_label.config(text=info)
        self.test_button.config(state="normal")
        self.set_status(f"Instrument: {entry_id} | Status: Not tested", "INFO")

    def test_selected_instrument(self):
        """Test connectivity to the selected instrument."""
        entry_id = self.get_selected_instrument_id()
        if not entry_id or self.registry is None:
            return

        entry = self.registry.get(entry_id)
        if entry is None:
            self.log(f"Instrument not found: {entry_id}", "ERROR")
            return

        self.set_status(f"Instrument: {entry_id} | Status: Testing...", "RUNNING")
        self.log(f"Testing {entry_id} ...")

        try:
            endpoint = open_endpoint_for_entry(entry)
            try:
                idn = endpoint.query("*IDN?")
                if idn and idn.strip():
                    self.log(f"{entry_id} IDN: {idn.strip()}", "SUCCESS")
                    self.set_status(f"Instrument: {entry_id} | Status: Connected", "SUCCESS")
                else:
                    self.log(f"{entry_id} returned empty IDN response.", "ERROR")
                    self.set_status(f"Instrument: {entry_id} | Status: Failed", "ERROR")
            except InstrumentEndpointError as exc:
                self.log(f"{entry_id} test failed: {exc.message}", "ERROR")
                self.set_status(f"Instrument: {entry_id} | Status: Failed", "ERROR")
            finally:
                endpoint.close()
        except InstrumentEndpointError as exc:
            self.log(f"{entry_id} open failed: {exc.message}", "ERROR")
            self.set_status(f"Instrument: {entry_id} | Status: Failed", "ERROR")

    def get_selected_session_file(self):
        """Return full path to the selected session file, or empty string."""
        filename = self.session_var.get().strip()
        if not filename:
            return ""
        return os.path.join(SESSIONS_DIR, filename)