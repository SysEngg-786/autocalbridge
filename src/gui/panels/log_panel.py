# File: src/gui/panels/log_panel.py
# Path: /d/Projects/autocalbridge/src/gui/panels/log_panel.py
# Purpose: Bottom log/audit panel using the existing LogTerminal widget.
#          Removed duplicate System Log title and Clear button from this
#          panel. Clear will live in CommandPanel next to Send to save
#          vertical space.

import tkinter as tk
from tkinter import ttk

from src.gui.log_terminal import LogTerminal


class LogPanel(ttk.Frame):
    """Bottom panel wrapping the reusable LogTerminal."""

    def __init__(self, parent, height=10):
        super().__init__(parent, padding=5)
        self.log_terminal = None

        self.create_widgets(height)
        self.bind_context_menu()

    def create_widgets(self, height):
        """Create only the LogTerminal. No duplicate header."""
        self.log_terminal = LogTerminal(self, height=height)
        self.log_terminal.frame.pack(fill="both", expand=True)

    def bind_context_menu(self):
        """Bind right-click context menu to the log text widget."""
        if self.log_terminal is None:
            return

        text_widget = self.log_terminal.text

        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self.copy_selection)
        self.context_menu.add_command(label="Select All", command=self.select_all)

        text_widget.bind(
            "<Button-3>",
            lambda event: self.show_context_menu(event),
        )

    def show_context_menu(self, event):
        """Show the right-click context menu at the pointer location."""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def copy_selection(self):
        """Copy selected text from the log terminal to clipboard."""
        if self.log_terminal is None:
            return

        text_widget = self.log_terminal.text

        try:
            selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            return

        self.clipboard_clear()
        self.clipboard_append(selected_text)

    def select_all(self):
        """Select all text in the log terminal."""
        if self.log_terminal is None:
            return

        text_widget = self.log_terminal.text
        text_widget.tag_add(tk.SEL, "1.0", tk.END)
        text_widget.mark_set(tk.INSERT, "1.0")
        text_widget.see(tk.INSERT)

    def clear_log(self):
        """Clear the visible log terminal content."""
        if self.log_terminal is not None:
            self.log_terminal.clear()