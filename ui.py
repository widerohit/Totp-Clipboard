"""Tkinter UI for TOTP Clipboard."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from otp_service import OtpError, generate_value, seconds_remaining
from profile_manager import DEFAULT_EXPORT_FILE, Profile, ProfileManager
from tray import TrayApp


BG = "#111827"
PANEL = "#1f2937"
PANEL_LIGHT = "#263244"
TEXT = "#f9fafb"
MUTED = "#9ca3af"
ACCENT = "#38bdf8"
SUCCESS = "#34d399"
WARNING = "#fbbf24"
ERROR = "#f87171"


class TOTPClipboardApp:
    def __init__(self, root: tk.Tk, manager: ProfileManager) -> None:
        self.root = root
        self.manager = manager
        self.current_value = ""
        self._allow_exit = False
        self._auto_copied = False
        self._refresh_job: str | None = None

        self.profile_var = tk.StringVar(value=self.manager.active_profile_name)
        self.generated_var = tk.StringVar(value="No profile selected")
        self.countdown_var = tk.StringVar(value="-- seconds")
        self.status_var = tk.StringVar(value="Secrets stay local. Offline only.")
        self.auto_copy_var = tk.BooleanVar(value=self.manager.auto_copy_on_launch)

        self.tray = TrayApp(
            on_open=lambda: self.root.after(0, self.show_window),
            on_copy=lambda: self.root.after(0, self.copy_current_value),
            on_exit=lambda: self.root.after(0, self.exit_app),
        )

        self._configure_window()
        self._configure_styles()
        self._build_ui()
        self._refresh_profile_options()
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.tray.start()
        self.refresh_loop()

    def _configure_window(self) -> None:
        self.root.title("TOTP Clipboard")
        self.root.geometry("520x480")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

    def _configure_styles(self) -> None:
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background=BG)
        self.style.configure("Panel.TFrame", background=PANEL)
        self.style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        self.style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        self.style.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI Semibold", 18))
        self.style.configure("Value.TLabel", background=PANEL, foreground=ACCENT, font=("Consolas", 24, "bold"))
        self.style.configure("Countdown.TLabel", background=PANEL, foreground=WARNING, font=("Segoe UI Semibold", 16))
        self.style.configure("Status.TLabel", background=BG, foreground=SUCCESS, font=("Segoe UI", 9))
        self.style.configure("TButton", font=("Segoe UI Semibold", 10), padding=(12, 8))
        self.style.configure("Accent.TButton", background=ACCENT, foreground="#07111f")
        self.style.map("Accent.TButton", background=[("active", "#7dd3fc")])
        self.style.configure("TCheckbutton", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        self.style.map("TCheckbutton", background=[("active", BG)], foreground=[("active", TEXT)])
        self.style.configure("TCombobox", fieldbackground=PANEL_LIGHT, background=PANEL_LIGHT, foreground=TEXT)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="TOTP Clipboard", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="Generate <BaseText><CurrentTOTP> and copy it in one click.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 18))

        selector_row = ttk.Frame(outer)
        selector_row.pack(fill="x")
        ttk.Label(selector_row, text="Profile").pack(side="left")
        self.profile_combo = ttk.Combobox(
            selector_row,
            textvariable=self.profile_var,
            state="readonly",
            width=24,
        )
        self.profile_combo.pack(side="left", padx=(10, 8), fill="x", expand=True)
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_profile_selected)

        ttk.Button(selector_row, text="Add", command=self.add_profile).pack(side="left", padx=2)
        ttk.Button(selector_row, text="Edit", command=self.edit_profile).pack(side="left", padx=2)
        ttk.Button(selector_row, text="Delete", command=self.delete_profile).pack(side="left", padx=2)

        panel = ttk.Frame(outer, style="Panel.TFrame", padding=18)
        panel.pack(fill="x", pady=18)
        ttk.Label(panel, text="Generated Value", style="Panel.TLabel").pack(anchor="w")
        ttk.Label(panel, textvariable=self.generated_var, style="Value.TLabel", wraplength=450).pack(
            anchor="w", pady=(8, 18)
        )
        ttk.Label(panel, text="Expires In", style="Panel.TLabel").pack(anchor="w")
        ttk.Label(panel, textvariable=self.countdown_var, style="Countdown.TLabel").pack(anchor="w", pady=(6, 0))

        action_row = ttk.Frame(outer)
        action_row.pack(fill="x")
        ttk.Button(action_row, text="Copy", style="Accent.TButton", command=self.copy_current_value).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(action_row, text="Import", command=self.import_profiles).pack(side="left", padx=(10, 0))
        ttk.Button(action_row, text="Export", command=self.export_profiles).pack(side="left", padx=(6, 0))

        ttk.Checkbutton(
            outer,
            text="Auto Copy on Launch",
            variable=self.auto_copy_var,
            command=self.toggle_auto_copy,
        ).pack(anchor="w", pady=(18, 8))

        ttk.Label(outer, textvariable=self.status_var, style="Status.TLabel", wraplength=470).pack(
            anchor="w", side="bottom"
        )

    def _refresh_profile_options(self) -> None:
        names = self.manager.names
        self.profile_combo.configure(values=names)
        active = self.manager.active_profile_name
        if active:
            self.profile_var.set(active)
        elif names:
            self.profile_var.set(names[0])
            self.manager.set_active_profile(names[0])
        else:
            self.profile_var.set("")

    def refresh_loop(self) -> None:
        profile = self.manager.get_active_profile()
        if profile is None:
            self.current_value = ""
            self.generated_var.set("Add a profile to begin")
            self.countdown_var.set("-- seconds")
        else:
            try:
                self.current_value = generate_value(profile.baseText, profile.secret)
                self.generated_var.set(self.current_value)
                remaining = seconds_remaining()
                self.countdown_var.set(f"{remaining} second{'s' if remaining != 1 else ''}")
                if self.manager.auto_copy_on_launch and not self._auto_copied:
                    self.copy_current_value(show_dialog=False)
                    self.status_var.set(f"Copied on launch: {self.current_value}")
                    self._auto_copied = True
            except OtpError as exc:
                self.current_value = ""
                self.generated_var.set("Invalid secret")
                self.countdown_var.set("-- seconds")
                self.status_var.set(str(exc))

        self._refresh_job = self.root.after(1000, self.refresh_loop)

    def on_profile_selected(self, _event: tk.Event | None = None) -> None:
        self.manager.set_active_profile(self.profile_var.get())
        self.status_var.set(f"Active profile: {self.profile_var.get()}")

    def copy_current_value(self, show_dialog: bool = True) -> None:
        if not self.current_value:
            self.status_var.set("Nothing to copy. Add or select a valid profile.")
            if show_dialog:
                messagebox.showwarning("TOTP Clipboard", "Nothing to copy. Add or select a valid profile.")
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(self.current_value)
        self.root.update()
        self.status_var.set(f"Copied: {self.current_value}")
        if show_dialog:
            messagebox.showinfo("TOTP Clipboard", f"Copied:\n{self.current_value}")

    def toggle_auto_copy(self) -> None:
        enabled = self.auto_copy_var.get()
        self.manager.set_auto_copy_on_launch(enabled)
        self.status_var.set("Auto Copy on Launch enabled." if enabled else "Auto Copy on Launch disabled.")

    def add_profile(self) -> None:
        dialog = ProfileDialog(self.root, "Add Profile")
        if dialog.result:
            try:
                self.manager.add_profile(dialog.result)
                self._refresh_profile_options()
                self.status_var.set(f"Added profile: {dialog.result.name}")
            except ValueError as exc:
                messagebox.showerror("TOTP Clipboard", str(exc))

    def edit_profile(self) -> None:
        profile = self.manager.get_active_profile()
        if profile is None:
            messagebox.showwarning("TOTP Clipboard", "Select a profile to edit.")
            return

        dialog = ProfileDialog(self.root, "Edit Profile", profile)
        if dialog.result:
            try:
                self.manager.update_profile(profile.name, dialog.result)
                self._refresh_profile_options()
                self.status_var.set(f"Updated profile: {dialog.result.name}")
            except ValueError as exc:
                messagebox.showerror("TOTP Clipboard", str(exc))

    def delete_profile(self) -> None:
        profile = self.manager.get_active_profile()
        if profile is None:
            messagebox.showwarning("TOTP Clipboard", "Select a profile to delete.")
            return
        if not messagebox.askyesno("TOTP Clipboard", f"Delete profile '{profile.name}'?"):
            return
        self.manager.delete_profile(profile.name)
        self._refresh_profile_options()
        self.status_var.set(f"Deleted profile: {profile.name}")

    def export_profiles(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export Profiles",
            initialfile=DEFAULT_EXPORT_FILE.name,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        try:
            exported = self.manager.export_profiles(Path(path))
            self.status_var.set(f"Exported profiles to {exported}")
            messagebox.showinfo("TOTP Clipboard", f"Profiles exported to:\n{exported}")
        except OSError as exc:
            messagebox.showerror("TOTP Clipboard", str(exc))

    def import_profiles(self) -> None:
        path = filedialog.askopenfilename(
            title="Import Profiles",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        try:
            count = self.manager.import_profiles(Path(path))
            self._refresh_profile_options()
            self.status_var.set(f"Imported {count} profile(s).")
            messagebox.showinfo("TOTP Clipboard", f"Imported {count} profile(s).")
        except (OSError, ValueError) as exc:
            messagebox.showerror("TOTP Clipboard", str(exc))

    def hide_to_tray(self) -> None:
        if self._allow_exit:
            self.exit_app()
            return
        self.root.withdraw()
        self.status_var.set("TOTP Clipboard is running in the system tray.")

    def show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def exit_app(self) -> None:
        self._allow_exit = True
        if self._refresh_job is not None:
            self.root.after_cancel(self._refresh_job)
            self._refresh_job = None
        self.tray.stop()
        self.root.destroy()


class ProfileDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, title: str, profile: Profile | None = None) -> None:
        super().__init__(parent)
        self.result: Profile | None = None
        self.configure(bg=BG)
        self.title(title)
        self.geometry("420x285")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.name_var = tk.StringVar(value=profile.name if profile else "")
        self.base_var = tk.StringVar(value=profile.baseText if profile else "")
        self.secret_var = tk.StringVar(value=profile.secret if profile else "")

        frame = ttk.Frame(self, padding=18)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=title, style="Title.TLabel").pack(anchor="w", pady=(0, 14))
        self._entry(frame, "Name", self.name_var)
        self._entry(frame, "Base Text", self.base_var)
        self._entry(frame, "Base32 Secret", self.secret_var, show="")

        button_row = ttk.Frame(frame)
        button_row.pack(fill="x", pady=(18, 0))
        ttk.Button(button_row, text="Save", style="Accent.TButton", command=self.save).pack(side="right")
        ttk.Button(button_row, text="Cancel", command=self.destroy).pack(side="right", padx=(0, 8))

        self.bind("<Return>", lambda _event: self.save())
        self.bind("<Escape>", lambda _event: self.destroy())
        self.wait_window()

    def _entry(self, parent: ttk.Frame, label: str, variable: tk.StringVar, show: str | None = None) -> None:
        ttk.Label(parent, text=label).pack(anchor="w", pady=(4, 2))
        entry = ttk.Entry(parent, textvariable=variable, show=show if show is not None else "")
        entry.pack(fill="x")

    def save(self) -> None:
        try:
            profile = Profile(
                name=self.name_var.get().strip(),
                baseText=self.base_var.get(),
                secret=self.secret_var.get().strip(),
            )
            profile.validate()
        except ValueError as exc:
            messagebox.showerror("TOTP Clipboard", str(exc), parent=self)
            return
        self.result = profile
        self.destroy()
