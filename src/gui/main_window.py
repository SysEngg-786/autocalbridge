# File: src/gui/main_window.py
# Path: /d/Projects/autocalbridge/src/gui/main_window.py
# Purpose: Main window shell using resizable paned windows.
#          Top status ribbon, prominent instrument display, Exit button.
#          Horizontal paned window for Setup | Run | Results.
#          Vertical paned window for main area | bottom command+log area.
#          Command panel sits directly above the log window with a border.

import os
import tkinter as tk
from tkinter import ttk

from src.gui.panels.setup_panel import SetupPanel
from src.gui.panels.run_panel import RunPanel
from src.gui.panels.results_panel import ResultsPanel
from src.gui.panels.command_panel import CommandPanel
from src.gui.panels.log_panel import LogPanel

from src.core.session_runner import run_session, SessionRunnerError
from src.core.report_generator import ReportGenerator
from src.utils.structured_logger import setup_logging


class MainWindow:
    """Main window for AutoCalBridge GUI."""

    def __init__(self, root):
        self.root = root
        self.root.title("AutoCalBridge (ACB)")
        self.root.geometry("1200x720")
        self.root.configure(bg="#f4f6f9")

        # Initialize structured logging once for the application.
        setup_logging()

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(".", background="#f4f6f9", foreground="#333333")
        self.style.configure("TFrame", background="#f4f6f9")
        self.style.configure("TLabel", background="#f4f6f9", font=("Segoe UI", 9))
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        self.style.configure(
            "Accent.TButton",
            background="#003366",
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padding=8,
        )

        self.create_layout()

    def create_layout(self):
        """Create the panel-based resizable layout."""
        # Top blue ribbon
        self.top_ribbon = tk.Frame(self.root, bg="#003366", height=32)
        self.top_ribbon.pack(side="top", fill="x")

        ribbon_title = tk.Label(
            self.top_ribbon,
            text="AUTOCALBRIDGE",
            bg="#003366",
            fg="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=4,
        )
        ribbon_title.pack(side="left")

        # Exit button on top right
        self.exit_button = tk.Button(
            self.top_ribbon,
            text="Exit",
            command=self.root.destroy,
            bg="#003366",
            fg="#ffffff",
            activebackground="#002244",
            activeforeground="#ffffff",
            bd=0,
            font=("Segoe UI", 9, "bold"),
            padx=10,
        )
        self.exit_button.pack(side="right")

        # Prominent status display below top ribbon
        self.status_display = tk.Label(
            self.root,
            text="Instrument: --    |    Status: --",
            bg="#eef2f7",
            fg="#333333",
            anchor="w",
            padx=10,
            pady=4,
            font=("Segoe UI", 10, "bold"),
        )
        self.status_display.pack(side="top", fill="x")

        # Main vertical paned window: main work area vs bottom log area
        self.vertical_paned = ttk.PanedWindow(self.root, orient="vertical")
        self.vertical_paned.pack(fill="both", expand=True)

        # Top horizontal paned window: Setup | Run | Results
        self.horizontal_paned = ttk.PanedWindow(self.vertical_paned, orient="horizontal")
        self.vertical_paned.add(self.horizontal_paned, weight=4)

        # Left setup panel
        self.setup_panel = SetupPanel(
            self.horizontal_paned,
            on_status=self.set_status,
            log_panel=None,  # temporarily no log panel; will update later
        )
        self.setup_panel.pack(side="left", fill="y", padx=5, pady=5)
        self.horizontal_paned.add(self.setup_panel, weight=0)

        # Center run panel
        self.run_panel = RunPanel(
            self.horizontal_paned,
            on_run_callback=self.run_selected_session,
            on_status=self.set_status,
        )
        self.run_panel.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.horizontal_paned.add(self.run_panel, weight=1)

        # Right results panel
        self.results_panel = ResultsPanel(
            self.horizontal_paned,
            on_status=self.set_status,
        )
        self.results_panel.pack(side="right", fill="y", padx=5, pady=5)
        self.horizontal_paned.add(self.results_panel, weight=0)

        # Bottom container: command panel above log panel with border
        bottom_container = ttk.Frame(self.vertical_paned)
        self.vertical_paned.add(bottom_container, weight=1)

        # Command panel wrapped in a bordered frame
        command_border_frame = tk.Frame(
            bottom_container,
            bg="#003366",
            bd=2,
            relief="groove",
        )
        command_border_frame.pack(fill="x", padx=5, pady=(5, 0))

        self.command_panel = CommandPanel(
            command_border_frame,
            get_selected_instrument_id=self.get_selected_instrument_id,
            log_panel=None,  # will be wired after log panel creation
            on_status=self.set_status,
        )
        self.command_panel.pack(fill="x", padx=2, pady=2)

        # Log panel
        self.log_panel = LogPanel(bottom_container, height=8)
        self.log_panel.pack(fill="both", expand=True, padx=5, pady=5)

        # Wire log panel to setup and command panels
        self.setup_panel.log_panel = self.log_panel
        self.command_panel.log_panel = self.log_panel

    def set_status(self, message, level="INFO"):
        """Update the top status bar text."""
        self.status_display.config(text=message)

    def log(self, message, level="INFO"):
        """Route a message to the log panel."""
        if hasattr(self.log_panel, "log_terminal"):
            self.log_panel.log_terminal.log(message, level)

    def get_selected_instrument_id(self):
        """Return the currently selected instrument ID from SetupPanel."""
        return self.setup_panel.get_selected_instrument_id()

    def run_selected_session(self):
        """Run the session selected in the setup panel."""
        session_file = self.setup_panel.get_selected_session_file()

        if not session_file:
            self.log("No session file selected.", "ERROR")
            self.set_status("No session selected")
            return

        if not os.path.isfile(session_file):
            self.log(f"Session file not found: {session_file}", "ERROR")
            self.set_status("Session file not found")
            return

        self.set_status("Running session ...")
        self.log(f"Running session: {session_file}")

        try:
            results, errors = run_session(session_file)
        except SessionRunnerError as exc:
            self.log(f"Session run failed: {exc}", "ERROR")
            self.set_status("Session run failed")
            return

        # Show results in results panel.
        self.results_panel.set_results(results)

        if errors:
            self.log(f"Errors encountered: {len(errors)}", "WARNING")
            for err in errors:
                self.log(
                    f"{err.get('instrument', 'Unknown')}: {err.get('message', '')}",
                    "ERROR",
                )

        # Generate a CSV report and show its path.
        try:
            report_generator = ReportGenerator()
            report_path = report_generator.generate_report(results, prefix="GUI")
            self.log(f"Report saved to: {report_path}", "SUCCESS")
        except Exception as exc:
            self.log(f"Report generation failed: {exc}", "WARNING")