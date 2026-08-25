# File: src/gui/main_window.py
# Path: /autocalbridge/src/gui/main_window.py
# Purpose: Main window for AutoCalBridge GUI.

import tkinter as tk
from tkinter import ttk


class MainWindow:
    """Main window for AutoCalBridge GUI."""

    def __init__(self, root):
        """Initialize the main window."""
        self.root = root
        self.root.title("AutoCalBridge (ACB)")
        self.root.geometry("950x650")
        self.root.configure(bg="#f4f6f9")

        # Configure styles
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(".", background="#f4f6f9", foreground="#333333")
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        self.style.configure("TLabel", font=("Segoe UI", 9), background="#f4f6f9")
        self.style.configure("TFrame", background="#f4f6f9")

        # Create main layout
        self.create_layout()

    def create_layout(self):
        """Create the main layout."""
        # Left panel (controls)
        self.control_frame = tk.Frame(self.root, bg="#ffffff", bd=1, relief="solid", width=320)
        self.control_frame.pack(side="left", fill="y", padx=15, pady=15)
        self.control_frame.pack_propagate(False)

        # Right panel (display)
        self.display_frame = tk.Frame(self.root, bg="#f4f6f9")
        self.display_frame.pack(side="right", fill="both", expand=True, padx=15, pady=15)

        # Populate control panel
        self.create_control_panel()

        # Populate display panel
        self.create_display_panel()

    def create_control_panel(self):
        """Create the control panel."""
        # Header
        header = tk.Label(
            self.control_frame,
            text="AUTOCALBRIDGE",
            font=("Segoe UI", 14, "bold"),
            bg="#ffffff",
            fg="#003366"
        )
        header.pack(anchor="w", padx=10, pady=15)

        # Connection section
        tk.Label(
            self.control_frame,
            text="Instrument Connection",
            font=("Segoe UI", 11, "bold"),
            bg="#ffffff",
            fg="#003366"
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # VISA address
        tk.Label(self.control_frame, text="VISA Address:", bg="#ffffff").pack(anchor="w", padx=10)
        self.entry_visa = ttk.Entry(self.control_frame)
        self.entry_visa.insert(0, "TCPIP0::localhost::hislip0::INSTR")
        self.entry_visa.pack(fill="x", padx=10, pady=3)

        # Connect button
        self.btn_connect = ttk.Button(
            self.control_frame,
            text="Connect",
            command=self.on_connect
        )
        self.btn_connect.pack(fill="x", padx=10, pady=5)

        # Status label
        self.status_label = tk.Label(
            self.control_frame,
            text="Disconnected",
            bg="#ffffff",
            fg="#888888"
        )
        self.status_label.pack(anchor="w", padx=10, pady=2)

        # Separator
        ttk.Separator(self.control_frame, orient="horizontal").pack(fill="x", padx=10, pady=10)

        # Test configuration section
        tk.Label(
            self.control_frame,
            text="Test Configuration",
            font=("Segoe UI", 11, "bold"),
            bg="#ffffff",
            fg="#003366"
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Vendor selection
        tk.Label(self.control_frame, text="Vendor:", bg="#ffffff").pack(anchor="w", padx=10)
        self.vendor_var = tk.StringVar(value="Keysight")
        self.vendor_combo = ttk.Combobox(
            self.control_frame,
            textvariable=self.vendor_var,
            values=["Keysight", "Tektronix", "Rohde & Schwarz", "Keithley"],
            state="readonly"
        )
        self.vendor_combo.pack(fill="x", padx=10, pady=3)

        # Instrument selection
        tk.Label(self.control_frame, text="Instrument:", bg="#ffffff").pack(anchor="w", padx=10)
        self.instrument_var = tk.StringVar(value="34461A")
        self.instrument_combo = ttk.Combobox(
            self.control_frame,
            textvariable=self.instrument_var,
            values=["34461A", "34970A", "N5171B"],
            state="readonly"
        )
        self.instrument_combo.pack(fill="x", padx=10, pady=3)

        # Test points
        tk.Label(self.control_frame, text="Test Points (V):", bg="#ffffff").pack(anchor="w", padx=10)
        self.entry_points = ttk.Entry(self.control_frame)
        self.entry_points.insert(0, "1.0, 2.5, 5.0, 10.0")
        self.entry_points.pack(fill="x", padx=10, pady=3)

        # Tolerance
        tk.Label(self.control_frame, text="Tolerance (V):", bg="#ffffff").pack(anchor="w", padx=10)
        self.entry_tolerance = ttk.Entry(self.control_frame)
        self.entry_tolerance.insert(0, "0.005")
        self.entry_tolerance.pack(fill="x", padx=10, pady=3)

        # Run button
        self.btn_run = ttk.Button(
            self.control_frame,
            text="Run Test",
            command=self.on_run_test,
            state="disabled"
        )
        self.btn_run.pack(fill="x", padx=10, pady=15)

    def create_display_panel(self):
        """Create the display panel."""
        # Log terminal
        tk.Label(
            self.display_frame,
            text="System Log",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=2)

        self.log_terminal = tk.Text(
            self.display_frame,
            height=10,
            bg="#1e1e1e",
            fg="#4af626",
            font=("Consolas", 10),
            bd=0
        )
        self.log_terminal.pack(fill="x", pady=5)

        # Results area
        tk.Label(
            self.display_frame,
            text="Results",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=2)

        self.results_frame = tk.Frame(self.display_frame, bg="#ffffff", bd=1, relief="solid")
        self.results_frame.pack(fill="both", expand=True, pady=5)

        # Placeholder
        placeholder = tk.Label(
            self.results_frame,
            text="Run a test to see results here.",
            bg="#ffffff",
            font=("Segoe UI", 10, "italic")
        )
        placeholder.pack(expand=True)

    def on_connect(self):
        """Handle connect button click."""
        address = self.entry_visa.get().strip()
        self.log("Connecting to: " + address)
        self.status_label.config(text="Connecting...", fg="#ff8800")
        # TODO: Implement connection logic
        self.status_label.config(text="Connected", fg="#00aa00")
        self.btn_run.config(state="normal")
        self.log("Connection successful")

    def on_run_test(self):
        """Handle run test button click."""
        self.log("Starting test sequence...")
        # TODO: Implement test execution
        self.log("Test sequence completed")

    def log(self, message):
        """Add a message to the log terminal."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_terminal.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_terminal.see(tk.END)
        self.root.update_idletasks()