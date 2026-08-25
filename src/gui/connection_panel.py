# File: src/gui/connection_panel.py
# Path: /autocalbridge/src/gui/connection_panel.py
# Purpose: Connection panel for AutoCalBridge GUI.

import tkinter as tk
from tkinter import ttk
from src.drivers import DRIVER_REGISTRY, get_driver


class ConnectionPanel:
    """Connection panel for instrument control."""

    def __init__(self, parent, on_connect_callback=None):
        """Initialize the connection panel.

        Args:
            parent: Parent widget
            on_connect_callback: Function to call when connected
        """
        self.parent = parent
        self.on_connect_callback = on_connect_callback
        self.connected = False
        self.instrument = None
        self.visa_manager = None

        self.create_widgets()

    def create_widgets(self):
        """Create the connection panel widgets."""
        # Frame
        self.frame = ttk.LabelFrame(self.parent, text="Instrument Connection", padding=10)
        self.frame.pack(fill="x", pady=5)

        # VISA Address
        ttk.Label(self.frame, text="VISA Address:").grid(row=0, column=0, sticky="w", pady=2)
        self.visa_entry = ttk.Entry(self.frame, width=40)
        self.visa_entry.insert(0, "TCPIP0::localhost::hislip0::INSTR")
        self.visa_entry.grid(row=0, column=1, sticky="ew", pady=2, padx=(5, 0))

        # Vendor selection
        ttk.Label(self.frame, text="Vendor:").grid(row=1, column=0, sticky="w", pady=2)
        self.vendor_var = tk.StringVar(value="Keysight")
        self.vendor_combo = ttk.Combobox(
            self.frame,
            textvariable=self.vendor_var,
            values=list(DRIVER_REGISTRY.keys()),
            state="readonly",
            width=20
        )
        self.vendor_combo.grid(row=1, column=1, sticky="w", pady=2, padx=(5, 0))
        self.vendor_combo.bind("<<ComboboxSelected>>", self.on_vendor_change)

        # Instrument selection
        ttk.Label(self.frame, text="Instrument:").grid(row=2, column=0, sticky="w", pady=2)
        self.instrument_var = tk.StringVar(value="34461A")
        self.instrument_combo = ttk.Combobox(
            self.frame,
            textvariable=self.instrument_var,
            values=["34461A"],
            state="readonly",
            width=20
        )
        self.instrument_combo.grid(row=2, column=1, sticky="w", pady=2, padx=(5, 0))

        # Connection mode
        ttk.Label(self.frame, text="Mode:").grid(row=3, column=0, sticky="w", pady=2)
        self.mode_var = tk.StringVar(value="network")
        self.mode_combo = ttk.Combobox(
            self.frame,
            textvariable=self.mode_var,
            values=["local", "network"],
            state="readonly",
            width=10
        )
        self.mode_combo.grid(row=3, column=1, sticky="w", pady=2, padx=(5, 0))

        # Buttons
        self.connect_btn = ttk.Button(self.frame, text="Connect", command=self.do_connect)
        self.connect_btn.grid(row=4, column=0, pady=10, sticky="e", padx=(0, 5))

        self.disconnect_btn = ttk.Button(
            self.frame,
            text="Disconnect",
            command=self.do_disconnect,
            state="disabled"
        )
        self.disconnect_btn.grid(row=4, column=1, pady=10, sticky="w", padx=(5, 0))

        # Status
        self.status_var = tk.StringVar(value="Disconnected")
        self.status_label = ttk.Label(self.frame, textvariable=self.status_var, foreground="red")
        self.status_label.grid(row=5, column=0, columnspan=2, sticky="w", pady=2)

        # Make grid columns expand
        self.frame.columnconfigure(1, weight=1)

    def on_vendor_change(self, event=None):
        """Update instrument list when vendor changes."""
        vendor = self.vendor_var.get()
        driver_class = get_driver(vendor)
        if driver_class:
            instruments = driver_class().get_instruments()
            self.instrument_combo["values"] = instruments
            if instruments:
                self.instrument_combo.set(instruments[0])

    def do_connect(self):
        """Connect to the instrument."""
        if self.connected:
            return

        address = self.visa_entry.get().strip()
        vendor = self.vendor_var.get()
        instrument_model = self.instrument_var.get()
        mode = self.mode_var.get()

        self.status_var.set("Connecting...")
        self.status_label.config(foreground="orange")
        self.parent.update_idletasks()

        # TODO: Implement actual VISA connection
        # For now, simulate connection
        import time
        time.sleep(0.5)

        self.connected = True
        self.status_var.set(f"Connected to {vendor} {instrument_model}")
        self.status_label.config(foreground="green")
        self.connect_btn.config(state="disabled")
        self.disconnect_btn.config(state="normal")

        # Notify parent
        if self.on_connect_callback:
            self.on_connect_callback(vendor, instrument_model)

    def do_disconnect(self):
        """Disconnect from the instrument."""
        self.connected = False
        self.status_var.set("Disconnected")
        self.status_label.config(foreground="red")
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self.instrument = None
        self.visa_manager = None

    def get_connection_info(self):
        """Get the current connection information."""
        return {
            "address": self.visa_entry.get().strip(),
            "vendor": self.vendor_var.get(),
            "instrument": self.instrument_var.get(),
            "mode": self.mode_var.get(),
            "connected": self.connected
        }

    def update(self):
        """Update UI state (call periodically)."""
        pass