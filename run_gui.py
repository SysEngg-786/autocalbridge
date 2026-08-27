# File: run_gui.py
# Path: /d/Projects/autocalbridge/run_gui.py
# Purpose: Launcher for the AutoCalBridge graphical user interface.

import tkinter as tk

from src.gui.main_window import MainWindow


def main():
    """Launch the AutoCalBridge GUI and keep it open."""
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()