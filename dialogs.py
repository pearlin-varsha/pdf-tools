"""
dialogs.py - the small window for 'Split / extract pages'.

Uses tkinter, the window toolkit that comes built into Python.
"""

import tkinter as tk
from tkinter import messagebox

from common import APP_NAME


def ask_split_options(filename, page_count):
    """Show the window. Returns ("extract", "1-3, 5"), ("split", None), or None if cancelled."""
    from pdfops import parse_page_ranges                 # reuse the same checker the real work uses

    result = {"choice": None}                            # a dict so the button functions can change it

    root = tk.Tk()
    root.title(APP_NAME)
    root.resizable(False, False)
    root.attributes("-topmost", True)                    # appear in front of Explorer

    frame = tk.Frame(root, padx=16, pady=14)
    frame.pack()

    tk.Label(frame, text=f"{filename}  ({page_count} pages)", font=("Segoe UI", 10, "bold")).pack(anchor="w")
    tk.Label(frame, text="Pages to extract, e.g.  1-3, 5, 8-10").pack(anchor="w", pady=(10, 2))

    entry = tk.Entry(frame, width=36, font=("Segoe UI", 10))
    entry.pack(fill="x")
    entry.focus_set()                                    # cursor ready in the box

    def on_extract(event=None):                          # event=None lets Enter key call it too
        text = entry.get().strip()
        try:
            parse_page_ranges(text, page_count)          # check now so the user can fix typos
        except ValueError as exc:
            messagebox.showerror(APP_NAME, str(exc), parent=root)
            return                                       # keep the window open
        result["choice"] = ("extract", text)
        root.destroy()

    def on_split():
        result["choice"] = ("split", None)
        root.destroy()

    buttons = tk.Frame(frame, pady=12)
    buttons.pack(fill="x")
    tk.Button(buttons, text="Extract pages", width=14, command=on_extract).pack(side="left")
    tk.Button(buttons, text="Split every page", width=14, command=on_split).pack(side="left", padx=6)
    tk.Button(buttons, text="Cancel", width=10, command=root.destroy).pack(side="right")

    root.bind("<Return>", on_extract)                    # Enter = Extract
    root.bind("<Escape>", lambda e: root.destroy())      # Esc = Cancel

    # Centre the window on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() - root.winfo_width()) // 2
    y = (root.winfo_screenheight() - root.winfo_height()) // 3
    root.geometry(f"+{x}+{y}")
    root.after(50, root.focus_force)                     # grab keyboard focus once it's visible

    root.mainloop()                                      # wait here until the window closes
    return result["choice"]
