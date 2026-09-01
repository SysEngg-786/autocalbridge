# File: src/gui/panels/results_panel.py
# Path: /d/Projects/autocalbridge/src/gui/panels/results_panel.py
# Purpose: Results panel showing result table and summary.
#          Supports both full calibration session results and simpler
#          physical verification sweep results.
#          Uses larger fonts and wider columns for demo readability.

import tkinter as tk
from tkinter import ttk


class ResultsPanel(ttk.Frame):
    """Right panel for calibration results and report summary."""

    # Full session result columns.
    COLUMNS = [
        "Timestamp",
        "SessionID",
        "Operator",
        "Supervisor",
        "Procedure",
        "SourceID",
        "DUTID",
        "Target",
        "Measured",
        "Error",
        "Tolerance",
        "Status",
        "Metadata",
    ]

    # Simpler verification result columns.
    VERIFICATION_COLUMNS = [
        "Target (Hz)",
        "Measured (Hz)",
        "Error (Hz)",
        "Status",
    ]

    def __init__(self, parent, on_status=None):
        super().__init__(parent, padding=10)
        self.on_status = on_status

        # Larger font for demo readability.
        self.table_font = ("Segoe UI", 11)

        self.create_widgets()

    def create_widgets(self):
        """Create result table and summary widgets."""
        ttk.Label(self, text="Results", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 5))

        # Summary label
        self.summary_var = tk.StringVar(value="No run completed.")
        summary_label = ttk.Label(
            self,
            textvariable=self.summary_var,
            foreground="#003366",
            font=("Segoe UI", 10, "bold"),
        )
        summary_label.pack(anchor="w", pady=(0, 5))

        # Treeview for result rows
        columns = list(self.VERIFICATION_COLUMNS)
        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
            height=20,
            style="Results.Treeview",
        )

        # Define headings and widths
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="w", stretch=True)

        # Apply larger font to treeview rows and headings.
        style = ttk.Style()
        style.configure("Results.Treeview", font=self.table_font, rowheight=26)
        style.configure("Results.Treeview.Heading", font=("Segoe UI", 10, "bold"))

        # Vertical scrollbar
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    def _clear_tree(self):
        """Clear all rows from the tree."""
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _configure_columns(self, columns):
        """Configure tree columns dynamically."""
        self.tree["columns"] = list(columns)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="w", stretch=True)

    def set_results(self, results):
        """
        Display a list of canonical TestResult objects or dictionaries.

        Args:
            results: List of results. Each result may be a TestResult or dict.
        """
        self._clear_tree()
        self._configure_columns(self.COLUMNS)

        if not results:
            self.summary_var.set("No results.")
            return

        passed = 0
        failed = 0

        for result in results:
            if hasattr(result, "to_dict"):
                row = result.to_dict()
            elif isinstance(result, dict):
                row = result
            else:
                continue

            values = [str(row.get(col, "")) for col in self.COLUMNS]
            self.tree.insert("", "end", values=values)

            status = str(row.get("Status", "")).upper()
            if status == "PASS":
                passed += 1
            else:
                failed += 1

        total = passed + failed
        self.summary_var.set(
            f"Total: {total}   Passed: {passed}   Failed: {failed}"
        )

        if self.on_status is not None:
            self.on_status(f"Run complete: {passed}/{total} passed")

    def set_verification_results(self, results):
        """
        Display physical verification sweep results.

        Args:
            results: List of VerificationPointResult objects or dicts.
        """
        self._clear_tree()
        self._configure_columns(self.VERIFICATION_COLUMNS)

        if not results:
            self.summary_var.set("No verification results.")
            return

        passed = 0
        failed = 0

        for result in results:
            if isinstance(result, dict):
                target = result.get("target")
                measured = result.get("measured")
                error = result.get("error")
                status = result.get("status", "")
            else:
                target = result.target
                measured = result.measured
                error = result.error
                status = result.status

            values = [
                f"{target:.0f}" if target is not None else "",
                f"{measured:.6e}" if measured is not None else "ERROR",
                f"{error:.6e}" if error is not None else "",
                status,
            ]
            self.tree.insert("", "end", values=values)

            if status == "OK":
                passed += 1
            else:
                failed += 1

        total = passed + failed
        self.summary_var.set(
            f"Total: {total}   Passed: {passed}   Failed: {failed}"
        )

        if self.on_status is not None:
            self.on_status(f"Verification complete: {passed}/{total} passed")

    def clear(self):
        """Clear the result table and summary."""
        self._clear_tree()
        self.summary_var.set("No run completed.")