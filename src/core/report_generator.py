# File: src/core/report_generator.py
# Path: /autocalbridge/src/core/report_generator.py
# Purpose: Generate CSV reports from test results.

import os
import csv
from datetime import datetime


class ReportGenerator:
    """Generates CSV reports from test results."""

    def __init__(self, report_directory="Reports"):
        """Initialize with the report directory."""
        self.report_directory = report_directory
        self._ensure_directory()

    def _ensure_directory(self):
        """Ensure the report directory exists."""
        os.makedirs(self.report_directory, exist_ok=True)

    def generate_report(self, results, prefix="Cal_Report"):
        """Generate a CSV report from test results.

        Args:
            results: List of TestResult objects or dictionaries
            prefix: Prefix for the filename

        Returns:
            str: Path to the generated report
        """
        if not results:
            raise ValueError("No results to generate report")

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.csv"
        filepath = os.path.join(self.report_directory, filename)

        # Convert results to dictionaries if they are TestResult objects
        data = []
        for result in results:
            if hasattr(result, 'to_dict'):
                data.append(result.to_dict())
            else:
                data.append(result)

        # Write CSV
        if data:
            fieldnames = data[0].keys()
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)

        return filepath

    def generate_summary(self, results):
        """Generate a summary of test results.

        Args:
            results: List of TestResult objects or dictionaries

        Returns:
            dict: Summary statistics
        """
        total = len(results)
        if total == 0:
            return {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0}

        # Convert to dicts if needed
        data = []
        for result in results:
            if hasattr(result, 'to_dict'):
                data.append(result.to_dict())
            else:
                data.append(result)

        passed = sum(1 for r in data if r.get("Status") == "PASS")
        failed = total - passed
        pass_rate = (passed / total) * 100 if total > 0 else 0

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(pass_rate, 2)
        }

    def generate_summary_report(self, results, prefix="Summary"):
        """Generate a summary report as CSV.

        Args:
            results: List of TestResult objects or dictionaries
            prefix: Prefix for the filename

        Returns:
            str: Path to the generated summary report
        """
        summary = self.generate_summary(results)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.csv"
        filepath = os.path.join(self.report_directory, filename)

        # Write summary as a single row
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=summary.keys())
            writer.writeheader()
            writer.writerow(summary)

        return filepath