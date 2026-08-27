# File: src/gui/panels/results_panel.py
# Path: /d/Projects/autocalbridge/src/gui/panels/results_panel.py
# Purpose: Results panel showing result table and summary.

import tkinter as tk
from tkinter import ttk


class ResultsPanel(ttk.Frame):
    """Right panel for calibration results and report summary."""

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

    def __init__(self, parent, on_status=None):
        super().__init__(parent, padding=10)
        self.on_status = on_status

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
            font=("Segoe UI", 9, "bold"),
        )
        summary_label.pack(anchor="w", pady=(0, 5))

        # Treeview for result rows
        columns = list(self.COLUMNS)
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=20)

        # Define headings and widths
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=90, anchor="w", stretch=True)

        # Vertical scrollbar
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    def set_results(self, results):
        """Display a list of canonical TestResult objects or dictionaries.

        Args:
            results: List of results. Each result may be a TestResult or dict.
        """
        # Clear existing rows
        for item in self.tree.get_children():
            self.tree.delete(item)

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

    def clear(self):
        """Clear the result table and summary."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.summary_var.set("No run completed.")