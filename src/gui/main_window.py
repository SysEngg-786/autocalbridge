# File: src/gui/main_window.py
# Path: /d/Projects/autocalbridge/src/gui/main_window.py
# Purpose: Main window shell using resizable paned windows.
#          Top status ribbon, prominent instrument display, Exit button.
#          Left notebook contains Instrument and Session tabs.
#          Right results panel, bottom command+log area remain unchanged.
#          Includes physical frequency verification and waveform spot check.
#          Results panel has higher weight for demo emphasis.

import os
import tkinter as tk
from tkinter import ttk

from src.gui.panels.setup_panel import SetupPanel
from src.gui.panels.session_panel import SessionPanel
from src.gui.panels.run_panel import RunPanel
from src.gui.panels.results_panel import ResultsPanel
from src.gui.panels.command_panel import CommandPanel
from src.gui.panels.log_panel import LogPanel

from src.core.session_runner import run_session, SessionRunnerError
from src.core.report_generator import ReportGenerator
from src.core.physical_verification import (
    run_physical_freq_sweep,
    run_waveform_spot_check,
    PhysicalVerificationError,
)
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

        # Default session panel mode. Later can be toggled from UI or launch.
        self.session_panel_mode = "operator"

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

        # Top horizontal paned window: left notebook | center | results
        self.horizontal_paned = ttk.PanedWindow(self.vertical_paned, orient="horizontal")
        self.vertical_paned.add(self.horizontal_paned, weight=4)

        # Left notebook with Instrument and Session tabs
        self.left_notebook = ttk.Notebook(self.horizontal_paned)
        self.left_notebook.pack(side="left", fill="y", padx=5, pady=5)

        # Instrument tab: existing SetupPanel
        self.setup_panel = SetupPanel(
            self.left_notebook,
            on_status=self.set_status,
            log_panel=None,
        )
        self.setup_panel.pack(fill="both", expand=True, padx=5, pady=5)
        self.left_notebook.add(self.setup_panel, text="Instrument")

        # Session tab: new SessionPanel
        self.session_panel = SessionPanel(
            self.left_notebook,
            mode=self.session_panel_mode,
            on_status=self.set_status,
            log_panel=None,
            on_session_created=self.on_session_created,
        )
        self.session_panel.pack(fill="both", expand=True, padx=5, pady=5)
        self.left_notebook.add(self.session_panel, text="Session")

        self.horizontal_paned.add(self.left_notebook, weight=0)

        # Center run panel
        self.run_panel = RunPanel(
            self.horizontal_paned,
            on_run_callback=self.run_selected_session,
            on_status=self.set_status,
            on_verification_callback=self.run_frequency_verification,
            on_spot_check_callback=self.run_spot_check,
        )
        self.run_panel.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.horizontal_paned.add(self.run_panel, weight=1)

        # Right results panel with emphasis
        self.results_panel = ResultsPanel(
            self.horizontal_paned,
            on_status=self.set_status,
        )
        self.results_panel.pack(side="right", fill="y", padx=5, pady=5)
        self.horizontal_paned.add(self.results_panel, weight=2)

        # Bottom container: command panel above log panel with border
        bottom_container = ttk.Frame(self.vertical_paned)
        self.vertical_paned.add(bottom_container, weight=1)

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
            log_panel=None,
            on_status=self.set_status,
        )
        self.command_panel.pack(fill="x", padx=2, pady=2)

        self.log_panel = LogPanel(bottom_container, height=8)
        self.log_panel.pack(fill="both", expand=True, padx=5, pady=5)

        self.setup_panel.log_panel = self.log_panel
        self.session_panel.log_panel = self.log_panel
        self.command_panel.log_panel = self.log_panel

    def set_status(self, message, level="INFO"):
        colors = {
            "INFO": "#333333",
            "SUCCESS": "#008000",
            "WARNING": "#b36b00",
            "ERROR": "#b00000",
            "RUNNING": "#b36b00",
        }
        fg = colors.get(level.upper(), "#333333")
        self.status_display.config(text=message, fg=fg)

    def log(self, message, level="INFO"):
        if hasattr(self.log_panel, "log_terminal"):
            self.log_panel.log_terminal.log(message, level)

    def get_selected_instrument_id(self):
        return self.setup_panel.get_selected_instrument_id()

    def on_session_created(self, session_file):
        if hasattr(self.setup_panel, "refresh_sessions"):
            self.setup_panel.refresh_sessions()
        self.log(f"Session file created: {session_file}", "SUCCESS")

    def run_selected_session(self):
        session_file = self.setup_panel.get_selected_session_file()

        if not session_file:
            self.log("No session file selected.", "ERROR")
            self.set_status("No session selected")
            return

        if not os.path.isfile(session_file):
            self.log(f"Session file not found: {session_file}", "ERROR")
            self.set_status("Session file not found")
            return

        self.set_status("Running session ...", "RUNNING")
        self.log(f"Running session: {session_file}")

        try:
            results, errors = run_session(session_file)
        except SessionRunnerError as exc:
            self.log(f"Session run failed: {exc}", "ERROR")
            self.set_status("Session run failed", "ERROR")
            return

        self.results_panel.set_results(results)

        if errors:
            self.log(f"Errors encountered: {len(errors)}", "WARNING")
            for err in errors:
                self.log(
                    f"{err.get('instrument', 'Unknown')}: {err.get('message', '')}",
                    "ERROR",
                )

        try:
            report_generator = ReportGenerator()
            report_path = report_generator.generate_report(results, prefix="GUI")
            self.log(f"Report saved to: {report_path}", "SUCCESS")
        except Exception as exc:
            self.log(f"Report generation failed: {exc}", "WARNING")

    def run_frequency_verification(self):
        source_id = "rigol_dg2102_usb"
        dut_id = "rtc1002-lab1"

        self.set_status("Running frequency verification ...", "RUNNING")
        self.log(f"Running physical verification: {source_id} -> {dut_id}")

        try:
            results = run_physical_freq_sweep(
                source_id=source_id,
                dut_id=dut_id,
            )
        except PhysicalVerificationError as exc:
            self.log(f"Verification failed: {exc}", "ERROR")
            self.set_status("Verification failed", "ERROR")
            return

        self.results_panel.set_verification_results(results)

        try:
            data = [
                {
                    "Target": r.target,
                    "Measured": r.measured,
                    "Error": r.error,
                    "Status": r.status,
                }
                for r in results
            ]
            report_generator = ReportGenerator()
            report_path = report_generator.generate_report(
                data,
                prefix="Verification",
            )
            self.log(f"Verification report saved to: {report_path}", "SUCCESS")
        except Exception as exc:
            self.log(f"Verification report generation failed: {exc}", "WARNING")

        self.set_status("Verification complete", "SUCCESS")

    def run_spot_check(self):
        source_id = "rigol_dg2102_usb"
        dut_id = "rtc1002-lab1"

        waveform = self.run_panel.waveform_var.get().strip().upper()
        freq_text = self.run_panel.spot_freq_var.get().strip()
        ampl_text = self.run_panel.spot_ampl_var.get().strip()
        offset_text = self.run_panel.spot_offset_var.get().strip()

        frequency = None
        if waveform != "NOIS":
            if not freq_text:
                self.log("Frequency is required for this waveform.", "ERROR")
                self.set_status("Spot check failed", "ERROR")
                return
            try:
                frequency = float(freq_text)
            except ValueError:
                self.log("Invalid frequency value.", "ERROR")
                self.set_status("Spot check failed", "ERROR")
                return
        try:
            amplitude = float(ampl_text)
        except ValueError:
            self.log("Invalid amplitude value.", "ERROR")
            self.set_status("Spot check failed", "ERROR")
            return
        try:
            offset = float(offset_text)
        except ValueError:
            self.log("Invalid offset value.", "ERROR")
            self.set_status("Spot check failed", "ERROR")
            return

        self.set_status("Running waveform spot check ...", "RUNNING")
        self.log(f"Running spot check: {waveform} freq={frequency} ampl={amplitude} offset={offset}")

        try:
            result = run_waveform_spot_check(
                source_id=source_id,
                dut_id=dut_id,
                waveform=waveform,
                frequency=frequency,
                amplitude=amplitude,
                offset=offset,
            )
        except PhysicalVerificationError as exc:
            self.log(f"Spot check failed: {exc}", "ERROR")
            self.set_status("Spot check failed", "ERROR")
            return

        # Display single result in results panel as verification row.
        self.results_panel.set_verification_results([result])

        self.log(f"Spot check result: {result}", "SUCCESS")
        self.set_status("Spot check complete", "SUCCESS")