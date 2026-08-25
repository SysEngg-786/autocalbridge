# File: src/gui/log_terminal.py
# Path: /autocalbridge/src/gui/log_terminal.py
# Purpose: Log terminal widget for AutoCalBridge GUI.

import tkinter as tk
from tkinter import ttk
from datetime import datetime


class LogTerminal:
    """Log terminal widget for displaying system messages."""

    def __init__(self, parent, height=10):
        """Initialize the log terminal.

        Args:
            parent: Parent widget
            height: Height of the text widget in lines
        """
        self.parent = parent
        self.height = height
        self.messages = []

        self.create_widgets()

    def create_widgets(self):
        """Create the log terminal widgets."""
        # Frame with label
        self.frame = ttk.LabelFrame(self.parent, text="System Log", padding=5)
        self.frame.pack(fill="both", expand=True, pady=5)

        # Text widget with scrollbar
        self.text_frame = ttk.Frame(self.frame)
        self.text_frame.pack(fill="both", expand=True)

        self.text = tk.Text(
            self.text_frame,
            height=self.height,
            bg="#1e1e1e",
            fg="#4af626",
            font=("Consolas", 10),
            bd=0,
            wrap="word"
        )
        self.text.pack(side="left", fill="both", expand=True)

        # Scrollbar
        self.scrollbar = ttk.Scrollbar(
            self.text_frame,
            orient="vertical",
            command=self.text.yview
        )
        self.scrollbar.pack(side="right", fill="y")
        self.text.config(yscrollcommand=self.scrollbar.set)

        # Configure text tags for colors
        self.text.tag_config("INFO", foreground="#4af626")
        self.text.tag_config("WARNING", foreground="#ffaa00")
        self.text.tag_config("ERROR", foreground="#ff4444")
        self.text.tag_config("SUCCESS", foreground="#00ff88")
        self.text.tag_config("TIMESTAMP", foreground="#888888")

    def log(self, message, level="INFO"):
        """Add a message to the log.

        Args:
            message: Message text
            level: Log level (INFO, WARNING, ERROR, SUCCESS)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}\n"

        # Insert timestamp
        self.text.insert(tk.END, f"[{timestamp}] ", "TIMESTAMP")
        # Insert message with color
        self.text.insert(tk.END, f"{message}\n", level)

        self.text.see(tk.END)
        self.parent.update_idletasks()

        # Store for reference
        self.messages.append({"timestamp": timestamp, "message": message, "level": level})

    def info(self, message):
        """Log an info message."""
        self.log(message, "INFO")

    def warning(self, message):
        """Log a warning message."""
        self.log(message, "WARNING")

    def error(self, message):
        """Log an error message."""
        self.log(message, "ERROR")

    def success(self, message):
        """Log a success message."""
        self.log(message, "SUCCESS")

    def clear(self):
        """Clear the log terminal."""
        self.text.delete(1.0, tk.END)
        self.messages = []

    def get_messages(self):
        """Get all stored messages."""
        return self.messages

    def export_log(self, filepath):
        """Export the log to a file.

        Args:
            filepath: Path to save the log file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(filepath, "w") as f:
                for msg in self.messages:
                    f.write(f"[{msg['timestamp']}] [{msg['level']}] {msg['message']}\n")
            return True
        except Exception as e:
            self.error(f"Failed to export log: {e}")
            return False