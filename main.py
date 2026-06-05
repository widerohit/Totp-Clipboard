"""Entry point for TOTP Clipboard."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from profile_manager import ProfileManager
from ui import TOTPClipboardApp


def main() -> None:
    root = tk.Tk()
    try:
        manager = ProfileManager()
    except ValueError as exc:
        messagebox.showerror("TOTP Clipboard", str(exc))
        root.destroy()
        return

    TOTPClipboardApp(root, manager)
    root.mainloop()


if __name__ == "__main__":
    main()
