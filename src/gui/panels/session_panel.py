# File: src/gui/panels/session_panel.py
# Path: /d/Projects/autocalbridge/src/gui/panels/session_panel.py
# Purpose: Session creation panel with operator and CICD modes.
#          Contains only session configuration controls.
#          Operator mode shows physical instruments only.
#          CICD mode includes virtual instruments.

import os
import tkinter as tk
from tkinter import ttk

from src.utils.instrument_registry import load_registry
from src.core.session_creator import create_session, SessionCreationError

# Directory used for procedure file discovery.
PROCEDURES_DIR = "config/procedures"


class SessionPanel(ttk.Frame):
    """Panel for creating calibration sessions."""

    def __init__(
        self,
        parent,
        mode="operator",
        on_status=None,
        log_panel=None,
        on_session_created=None,
    ):
        super().__init__(parent, padding=10)
        self.mode = mode
        self.on_status = on_status
        self.log_panel = log_panel
        self.on_session_created = on_session_created

        self.registry = None
        self._instrument_display_to_id = {}
        self._instrument_id_to_display = {}

        self.create_widgets()
        self.refresh_all()

    def create_widgets(self):
        """Create session configuration widgets."""
        ttk.Label(self, text="Session", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 5))

        # Operator
        ttk.Label(self, text="Operator:").pack(anchor="w", pady=(0, 2))
        self.operator_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.operator_var, width=30).pack(fill="x", pady=(0, 5))

        # Supervisor
        ttk.Label(self, text="Supervisor (optional):").pack(anchor="w", pady=(0, 2))
        self.supervisor_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.supervisor_var, width=30).pack(fill="x", pady=(0, 5))

        # Source instrument
        ttk.Label(self, text="Source instrument:").pack(anchor="w", pady=(0, 2))
        self.source_var = tk.StringVar()
        self.source_combo = ttk.Combobox(
            self,
            textvariable=self.source_var,
            state="readonly",
            width=30,
        )
        self.source_combo.pack(fill="x", pady=(0, 5))

        # DUT instrument
        ttk.Label(self, text="DUT instrument:").pack(anchor="w", pady=(0, 2))
        self.dut_var = tk.StringVar()
        self.dut_combo = ttk.Combobox(
            self,
            textvariable=self.dut_var,
            state="readonly",
            width=30,
        )
        self.dut_combo.pack(fill="x", pady=(0, 5))

        # Procedure
        ttk.Label(self, text="Procedure:").pack(anchor="w", pady=(0, 2))
        self.procedure_var = tk.StringVar()
        self.procedure_combo = ttk.Combobox(
            self,
            textvariable=self.procedure_var,
            state="readonly",
            width=30,
        )
        self.procedure_combo.pack(fill="x", pady=(0, 5))

        # Session label
        ttk.Label(self, text="Label (optional):").pack(anchor="w", pady=(0, 2))
        self.label_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.label_var, width=30).pack(fill="x", pady=(0, 5))

        # Purpose / metadata
        ttk.Label(self, text="Purpose (optional):").pack(anchor="w", pady=(0, 2))
        self.purpose_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.purpose_var, width=30).pack(fill="x", pady=(0, 8))

        refresh_frame = ttk.Frame(self)
        refresh_frame.pack(fill="x", pady=(0, 8))

        ttk.Button(
            refresh_frame,
            text="Refresh Instruments",
            command=self.refresh_instruments,
        ).pack(side="left", padx=(0, 5))

        ttk.Button(
            refresh_frame,
            text="Refresh Procedures",
            command=self.refresh_procedures,
        ).pack(side="left")

        self.create_button = ttk.Button(
            self,
            text="Create Session",
            command=self.create_session_action,
        )
        self.create_button.pack(fill="x", pady=(0, 8))

    def set_mode(self, mode):
        """Set panel mode and refresh instrument list."""
        self.mode = mode
        self.refresh_instruments()

    def log(self, message, level="INFO"):
        if self.log_panel is not None:
            self.log_panel.log_terminal.log(message, level)

    def set_status(self, message, level="INFO"):
        if self.on_status is not None:
            self.on_status(message, level)

    def refresh_all(self):
        self.refresh_instruments()
        self.refresh_procedures()

    def refresh_instruments(self):
        """Load registered instrument IDs into source and DUT combos."""
        try:
            self.registry = load_registry()
        except Exception as exc:
            self.log(f"Registry load failed: {exc}", "ERROR")
            self.set_status("Registry load failed", "ERROR")
            return

        include_virtual = self.mode == "cicd"

        display_items = []
        self._instrument_display_to_id = {}
        self._instrument_id_to_display = {}

        for entry in self.registry:
            if entry.kind == "virtual" and not include_virtual:
                continue

            if entry.kind == "virtual":
                display = f"{entry.id} [virtual]"
            else:
                display = entry.id

            display_items.append(display)
            self._instrument_display_to_id[display] = entry.id
            self._instrument_id_to_display[entry.id] = display

        self.source_combo["values"] = display_items
        self.dut_combo["values"] = display_items

        if display_items:
            if self.source_var.get() not in self._instrument_display_to_id:
                self.source_var.set(display_items[0])
            if self.dut_var.get() not in self._instrument_display_to_id:
                self.dut_var.set(display_items[0] if len(display_items) > 1 else "")
        else:
            self.source_var.set("")
            self.dut_var.set("")

    def refresh_procedures(self):
        """Load available procedure IDs from config/procedures/."""
        if not os.path.isdir(PROCEDURES_DIR):
            self.procedure_combo["values"] = []
            return

        files = sorted(
            [f[:-5] for f in os.listdir(PROCEDURES_DIR) if f.endswith(".yaml")]
        )
        self.procedure_combo["values"] = files
        if files and self.procedure_var.get() not in files:
            self.procedure_var.set(files[0])

    def _selected_source_id(self):
        display = self.source_var.get()
        return self._instrument_display_to_id.get(display, "")

    def _selected_dut_id(self):
        display = self.dut_var.get()
        return self._instrument_display_to_id.get(display, "")

    def create_session_action(self):
        """Gather inputs and create a session file."""
        operator = self.operator_var.get().strip()
        supervisor = self.supervisor_var.get().strip()
        source_id = self._selected_source_id()
        dut_id = self._selected_dut_id()
        procedure = self.procedure_var.get().strip()
        label = self.label_var.get().strip()
        purpose = self.purpose_var.get().strip()

        metadata = {}
        if purpose:
            metadata["purpose"] = purpose

        try:
            session_file = create_session(
                operator=operator,
                supervisor=supervisor or None,
                source_id=source_id,
                dut_id=dut_id,
                procedure=procedure,
                label=label or None,
                metadata=metadata or None,
            )
        except SessionCreationError as exc:
            self.log(f"Session creation failed: {exc}", "ERROR")
            self.set_status("Session creation failed", "ERROR")
            return

        self.log(f"Session created: {session_file}", "SUCCESS")
        self.set_status("Session created", "SUCCESS")

        if self.on_session_created is not None:
            self.on_session_created(session_file)