# File: src/gui/threading_utils.py
# Path: /d/Projects/autocalbridge/src/gui/threading_utils.py
# Purpose: Reusable non-blocking background execution helper for Tkinter GUI.
#          Runs a function in a worker thread and marshals results/errors
#          back to the Tk main thread safely.

import threading
import tkinter as tk
from typing import Any, Callable, Optional


def run_in_background(
    parent: tk.Misc,
    func: Callable[[], Any],
    on_success: Optional[Callable[[Any], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
) -> None:
    """
    Run a function in a background thread and return result to Tk main thread.

    The GUI remains responsive while the function executes.

    Args:
        parent: Tk widget used to schedule callbacks on the main thread.
        func: Callable that performs the long-running work.
        on_success: Optional callback receiving func() result on main thread.
        on_error: Optional callback receiving Exception on main thread.
    """
    def worker():
        try:
            result = func()
        except Exception as exc:
            if on_error is not None:
                parent.after(0, lambda: on_error(exc))
        else:
            if on_success is not None:
                parent.after(0, lambda: on_success(result))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()