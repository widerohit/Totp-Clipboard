# Tkinter UI for TOTP Clipboard (Premium Dark Theme)

"""Implementation of a modern, premium dark-theme UI for the TOTP Clipboard
application. The UI follows a refined design system and provides:
- Header with logo, title, subtitle, settings and tray buttons
- Left sidebar for profile management (search, list, add/edit/delete)
- Main content area with profile info card, live TOTP display (animated countdown
  ring), generated password field and quick-action buttons
- Footer with status indicators
- Keyboard shortcuts, toast notifications and optional recent-copy history.

All public method names, callbacks, and attribute names are unchanged from the
original implementation so this file is a drop-in replacement.
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from otp_service import OtpError, generate_value, seconds_remaining
from profile_manager import (
    DEFAULT_EXPORT_FILE,
    Profile,
    ProfileManager,
)
from tray import TrayApp


def resource_path(relative: str) -> Path:
    """Resolve a bundled resource path that works both running from source
    and from a PyInstaller --onefile exe (which extracts to sys._MEIPASS)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative

# ---------------------------------------------------------------------------
# Design System – colors (premium dark theme)
# ---------------------------------------------------------------------------
BG = "#0B0B0F"                 # App background (near-black, faint blue tint)
SURFACE = "#131318"            # Sidebar / panel surface
ELEVATED = "#1B1B22"           # Cards
ELEVATED_2 = "#22222B"         # Nested / inner elements on cards
BORDER = "#2A2A35"             # Hairline borders on cards
BORDER_SUBTLE = "#1F1F27"      # Very faint separators

ACCENT = "#5B8CFF"             # Primary accent (cooler, more premium blue)
ACCENT_HOVER = "#7CA3FF"
ACCENT_PRESS = "#4775E6"
ACCENT_SOFT = "#1B2540"        # Accent tint background (selected rows, etc.)

SUCCESS = "#34D399"
WARNING = "#F5A524"
ERROR = "#F87171"

TEXT_PRIMARY = "#F4F4F6"
TEXT_SECONDARY = "#8A8A98"
TEXT_TERTIARY = "#5C5C6A"

FONT_FAMILY = "Segoe UI"
MONO_FAMILY = "Cascadia Code"  # falls back gracefully if unavailable


# ---------------------------------------------------------------------------
# Helper – rounded card surface drawn on a Canvas (ttk has no border-radius)
# ---------------------------------------------------------------------------
class RoundedCard(tk.Frame):
    """A frame with a rounded-rectangle background + hairline border, drawn on
    a Canvas, with a normal tk.Frame placed on top to host child widgets."""

    def __init__(self, parent, bg=ELEVATED, border=BORDER, radius=14, **kwargs):
        super().__init__(parent, bg=parent["bg"] if "bg" in parent.keys() else BG)
        self._bg = bg
        self._border = border
        self._radius = radius

        self._canvas = tk.Canvas(self, bg=self["bg"], highlightthickness=0, bd=0)
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self.body = tk.Frame(self, bg=bg, **kwargs)
        self.body.place(x=0, y=0, relwidth=1, relheight=1)

        self.bind("<Configure>", self._redraw)

    def _redraw(self, event=None) -> None:
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 4 or h < 4:
            return
        self._canvas.delete("all")
        r = self._radius
        self._round_rect(2, 2, w - 2, h - 2, r, fill=self._bg, outline=self._border, width=1)

    def _round_rect(self, x1, y1, x2, y2, r, **kw) -> None:
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        self._canvas.create_polygon(points, smooth=True, **kw)


# ---------------------------------------------------------------------------
# Helper – flat, rounded, hover-aware button (replaces stock ttk button)
# ---------------------------------------------------------------------------
class FlatButton(tk.Canvas):
    def __init__(
        self,
        parent,
        text: str,
        command=None,
        kind: str = "secondary",   # "primary" | "secondary" | "ghost"
        width: int = 120,
        height: int = 36,
        font_size: int = 10,
        bold: bool = True,
        radius: int = 9,
        anchor_bg=None,
    ) -> None:
        bg_parent = anchor_bg if anchor_bg is not None else parent["bg"]
        super().__init__(parent, width=width, height=height, bg=bg_parent,
                          highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self.kind = kind
        self.radius = radius
        self.text = text
        self.font_size = font_size
        self.bold = bold
        self._enabled = True

        self._palette = {
            "primary": (ACCENT, ACCENT_HOVER, ACCENT_PRESS, "#FFFFFF"),
            "secondary": (ELEVATED_2, "#2C2C37", "#26262F", TEXT_PRIMARY),
            "ghost": (bg_parent, "#1E1E26", "#191920", TEXT_SECONDARY),
            "danger": ("#3A1F1F", "#4A2424", "#321A1A", ERROR),
        }
        self._state = "normal"
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._draw("normal")

    def _draw(self, state: str) -> None:
        self.delete("all")
        w = int(self["width"])
        h = int(self["height"])
        normal, hover, press, fg = self._palette.get(self.kind, self._palette["secondary"])
        fill = {"normal": normal, "hover": hover, "press": press}.get(state, normal)
        if not self._enabled:
            fill = ELEVATED if self.kind != "primary" else "#2E3A5C"
            fg = TEXT_TERTIARY
        r = self.radius
        points = [
            r, 0, w - r, 0, w, 0, w, r,
            w, h - r, w, h, w - r, h, r, h,
            0, h, 0, h - r, 0, r, 0, 0,
        ]
        self.create_polygon(points, smooth=True, fill=fill, outline=fill)
        weight = "bold" if self.bold else "normal"
        self.create_text(
            w / 2, h / 2, text=self.text, fill=fg,
            font=(FONT_FAMILY, self.font_size, weight),
        )

    def _on_enter(self, _e=None) -> None:
        if self._enabled:
            self._draw("hover")

    def _on_leave(self, _e=None) -> None:
        if self._enabled:
            self._draw("normal")

    def _on_press(self, _e=None) -> None:
        if self._enabled:
            self._draw("press")

    def _on_release(self, e=None) -> None:
        if not self._enabled:
            return
        self._draw("hover")
        w = int(self["width"])
        h = int(self["height"])
        if e is not None and 0 <= e.x <= w and 0 <= e.y <= h and self.command:
            self.command()

    def set_text(self, text: str) -> None:
        self.text = text
        self._draw("normal")

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw("normal")


# ---------------------------------------------------------------------------
# Helper – toast notification (premium pill-style, fade-in/out)
# ---------------------------------------------------------------------------
class Toast(tk.Toplevel):
    def __init__(self, master: tk.Tk, message: str, duration: int = 2000, kind: str = "success"):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", 0.0)
        except tk.TclError:
            pass

        color = {"success": SUCCESS, "error": ERROR, "info": ACCENT}.get(kind, SUCCESS)
        outer = tk.Frame(self, bg=color, bd=0)
        outer.pack()
        inner = tk.Frame(outer, bg=ELEVATED)
        inner.pack(padx=1, pady=1)

        row = tk.Frame(inner, bg=ELEVATED)
        row.pack(padx=14, pady=10)
        dot = tk.Canvas(row, width=8, height=8, bg=ELEVATED, highlightthickness=0)
        dot.create_oval(0, 0, 8, 8, fill=color, outline=color)
        dot.pack(side="left", padx=(0, 8))
        tk.Label(
            row, text=message, bg=ELEVATED, fg=TEXT_PRIMARY,
            font=(FONT_FAMILY, 10, "bold"),
        ).pack(side="left")

        self.update_idletasks()
        x = master.winfo_rootx() + master.winfo_width() - self.winfo_width() - 18
        y = master.winfo_rooty() + 54
        self.geometry(f"+{x}+{y}")
        self._fade(0.0)
        self.after(duration, lambda: self._fade(1.0, out=True))

    def _fade(self, value: float, out: bool = False, step: float = 0.12) -> None:
        try:
            target = 0.0 if out else 0.95
            value = value + (-step if out else step)
            value = max(0.0, min(0.95, value))
            self.attributes("-alpha", value)
            if out and value <= 0.0:
                self.destroy()
                return
            if not out and value >= 0.95:
                return
            self.after(16, lambda: self._fade(value, out=out, step=step))
        except tk.TclError:
            pass


# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------
class TOTPClipboardApp:
    def __init__(self, root: tk.Tk, manager: ProfileManager) -> None:
        self.root = root
        self.manager = manager
        self.current_value = ""
        self._allow_exit = False
        self._auto_copied = False
        self._refresh_job: str | None = None
        self._history: list[str] = []  # recent generated passwords (max 5)

        # Tk variables
        self.profile_var = tk.StringVar()
        self.generated_var = tk.StringVar(value="No profile selected")
        self.countdown_var = tk.StringVar(value="-- seconds")
        self.status_var = tk.StringVar(value="Secrets stay local. Offline only.")
        self.auto_copy_var = tk.BooleanVar(value=self.manager.auto_copy_on_launch)

        # System tray integration
        self.tray = TrayApp(
            on_open=lambda: self.root.after(0, self.show_window),
            on_copy=lambda: self.root.after(0, self.copy_current_value),
            on_exit=lambda: self.root.after(0, self.exit_app),
        )

        self._configure_window()
        self._configure_styles()
        self._build_ui()
        self._refresh_profile_options()
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
        self.tray.start()
        self.refresh_loop()

        # Keyboard shortcuts
        self.root.bind_all("<Control-Alt-c>", lambda e: self.copy_current_value())
        self.root.bind_all("<Control-Alt-t>", lambda e: self.copy_totp_only())
        self.root.bind_all("<F2>", lambda e: self.edit_profile())

    # -----------------------------------------------------------------------
    # Window & Styles
    # -----------------------------------------------------------------------
    def _configure_window(self) -> None:
        self.root.title("TOTP Clipboard")
        self.root.geometry("760x540")
        self.root.minsize(760, 540)
        self.root.configure(bg=BG)
        self._set_app_icon()
        self._enable_acrylic()

    def _set_app_icon(self) -> None:
        """Set the title-bar/taskbar icon. Looks for app.ico next to the
        script when run from source, or in the PyInstaller temp dir when
        run as a frozen --onefile exe. Fails silently if not found."""
        try:
            icon_path = resource_path("app.ico")
            if icon_path.exists():
                self.root.iconbitmap(default=str(icon_path))
        except Exception:
            pass  # Icon is cosmetic only; never block app startup over it

    # Enable acrylic blur (requires Windows 10/11)
    def _enable_acrylic(self) -> None:
        try:
            import ctypes
            class ACCENT_POLICY(ctypes.Structure):
                _fields_ = [
                    ("AccentState", ctypes.c_int),
                    ("AccentFlags", ctypes.c_int),
                    ("GradientColor", ctypes.c_uint),
                    ("AnimationId", ctypes.c_int),
                ]
            class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
                _fields_ = [
                    ("Attribute", ctypes.c_int),
                    ("Data", ctypes.c_void_p),
                    ("SizeOfData", ctypes.c_size_t),
                ]
            accent = ACCENT_POLICY()
            accent.AccentState = 3  # ACCENT_ENABLE_BLURBEHIND
            accent.AccentFlags = 0
            accent.GradientColor = 0x00FFFFFF
            accent.AnimationId = 0
            data = WINDOWCOMPOSITIONATTRIBDATA()
            data.Attribute = 19  # WCA_ACCENT_POLICY
            data.Data = ctypes.addressof(accent)
            data.SizeOfData = ctypes.sizeof(accent)
            ctypes.windll.user32.SetWindowCompositionAttribute(
                ctypes.windll.user32.GetParent(self.root.winfo_id()),
                ctypes.byref(data),
            )
        except Exception:
            pass  # Silently ignore if unable to apply premium look

    def _configure_styles(self) -> None:
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")

        self.style.configure("TFrame", background=BG)
        self.style.configure("Header.TFrame", background=BG)
        self.style.configure("Sidebar.TFrame", background=SURFACE)
        self.style.configure("Content.TFrame", background=BG)

        self.style.configure("TLabel", background=BG, foreground=TEXT_PRIMARY, font=(FONT_FAMILY, 10))
        self.style.configure("Muted.TLabel", background=BG, foreground=TEXT_SECONDARY, font=(FONT_FAMILY, 9))
        self.style.configure("Title.TLabel", background=BG, foreground=TEXT_PRIMARY, font=(FONT_FAMILY, 19, "bold"))
        self.style.configure("Subtitle.TLabel", background=BG, foreground=TEXT_SECONDARY, font=(FONT_FAMILY, 10))
        self.style.configure("SectionTitle.TLabel", background=ELEVATED, foreground=TEXT_PRIMARY, font=(FONT_FAMILY, 11, "bold"))
        self.style.configure("Status.TLabel", background=BG, foreground=SUCCESS, font=(FONT_FAMILY, 9))

        self.style.configure(
            "TCheckbutton", background=ELEVATED, foreground=TEXT_SECONDARY,
            font=(FONT_FAMILY, 9), focuscolor=ELEVATED,
        )
        self.style.map(
            "TCheckbutton",
            background=[("active", ELEVATED)],
            foreground=[("active", TEXT_PRIMARY)],
        )
        self.style.configure(
            "TEntry", fieldbackground=ELEVATED_2, background=ELEVATED_2,
            foreground=TEXT_PRIMARY, insertcolor=TEXT_PRIMARY,
            bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
            borderwidth=1, relief="flat", padding=8, font=(FONT_FAMILY, 10),
        )
        self.style.map("TEntry", bordercolor=[("focus", ACCENT)])

        # Scrollbar (used implicitly nowhere yet, but keep dark for consistency)
        self.style.configure(
            "Vertical.TScrollbar", background=ELEVATED_2, troughcolor=SURFACE,
            bordercolor=SURFACE, arrowcolor=TEXT_SECONDARY,
        )

    # -----------------------------------------------------------------------
    # UI Construction – Header, Sidebar, Content, Footer
    # -----------------------------------------------------------------------
    def _build_ui(self) -> None:
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=16)

        self._build_header(outer)

        main_area = tk.Frame(outer, bg=BG)
        main_area.pack(fill="both", expand=True, pady=(16, 0))
        main_area.columnconfigure(0, weight=0, minsize=210)
        main_area.columnconfigure(1, weight=1)
        main_area.rowconfigure(0, weight=1)

        self._build_sidebar(main_area)
        self._build_content(main_area)

        self._build_footer(outer)

    # -----------------------------------------------------------------------
    def _build_header(self, parent: tk.Frame) -> None:
        header = tk.Frame(parent, bg=BG)
        header.pack(fill="x")

        # Logo badge – soft accent circle behind a lock glyph
        badge = tk.Canvas(header, width=44, height=44, bg=BG, highlightthickness=0)
        badge.create_oval(0, 0, 44, 44, fill=ACCENT_SOFT, outline="")
        badge.create_text(22, 22, text="🔒", font=(FONT_FAMILY, 16))
        badge.pack(side="left", padx=(0, 12))

        title_frame = tk.Frame(header, bg=BG)
        title_frame.pack(side="left", fill="y")
        ttk.Label(title_frame, text="TOTP Clipboard", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_frame, text="Offline TOTP Password Generator", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 0))

        spacer = tk.Frame(header, bg=BG)
        spacer.pack(side="left", expand=True, fill="x")

    # -----------------------------------------------------------------------
    def _build_sidebar(self, parent: tk.Frame) -> None:
        sidebar_card = RoundedCard(parent, bg=SURFACE, border=BORDER, radius=14)
        sidebar_card.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        sidebar = tk.Frame(sidebar_card.body, bg=SURFACE)
        sidebar.pack(fill="both", expand=True, padx=14, pady=14)

        # Search field, with inline placeholder behavior
        search_wrap = tk.Frame(sidebar, bg=ELEVATED_2, highlightbackground=BORDER,
                                highlightthickness=1, bd=0)
        search_wrap.pack(fill="x", pady=(0, 12))
        search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_wrap, textvariable=search_var, bg=ELEVATED_2, fg=TEXT_SECONDARY,
            insertbackground=TEXT_PRIMARY, relief="flat", font=(FONT_FAMILY, 10),
            highlightthickness=0, bd=0,
        )
        search_entry.pack(fill="x", padx=10, pady=8)
        placeholder = "Search profiles…"
        search_entry.insert(0, placeholder)

        def on_focus_in(_e):
            if search_entry.get() == placeholder:
                search_entry.delete(0, "end")
                search_entry.config(fg=TEXT_PRIMARY)

        def on_focus_out(_e):
            if not search_entry.get():
                search_entry.insert(0, placeholder)
                search_entry.config(fg=TEXT_SECONDARY)

        search_entry.bind("<FocusIn>", on_focus_in)
        search_entry.bind("<FocusOut>", on_focus_out)
        search_entry.bind("<KeyRelease>", lambda e: self._filter_profiles(
            "" if search_entry.get() == placeholder else search_var.get()
        ))

        # Profile list
        list_wrap = tk.Frame(sidebar, bg=SURFACE)
        list_wrap.pack(fill="both", expand=True)
        self.profile_listbox = tk.Listbox(
            list_wrap,
            bg=SURFACE,
            fg=TEXT_SECONDARY,
            selectbackground=ACCENT_SOFT,
            selectforeground=ACCENT_HOVER,
            relief="flat",
            highlightthickness=0,
            activestyle="none",
            bd=0,
            font=(FONT_FAMILY, 10),
            selectborderwidth=0,
        )
        self.profile_listbox.pack(fill="both", expand=True)
        self.profile_listbox.bind("<<ListboxSelect>>", self._on_sidebar_select)

        btn_frame = tk.Frame(sidebar, bg=SURFACE)
        btn_frame.pack(fill="x", pady=(12, 0))
        FlatButton(btn_frame, "Add", command=self.add_profile, kind="primary",
                   width=58, height=34, font_size=9, anchor_bg=SURFACE).pack(side="left", expand=True, fill="x", padx=(0, 4))
        FlatButton(btn_frame, "Edit", command=self.edit_profile, kind="secondary",
                   width=58, height=34, font_size=9, anchor_bg=SURFACE).pack(side="left", expand=True, fill="x", padx=4)
        FlatButton(btn_frame, "🗑", command=self.delete_profile, kind="danger",
                   width=34, height=34, font_size=12, anchor_bg=SURFACE).pack(side="left", padx=(4, 0))

    # -----------------------------------------------------------------------
    def _build_content(self, parent: tk.Frame) -> None:
        content = tk.Frame(parent, bg=BG)
        content.grid(row=0, column=1, sticky="nsew")
        content.rowconfigure(2, weight=1)

        # ---- Profile Information card ----
        profile_card = RoundedCard(content, bg=ELEVATED, border=BORDER, radius=14)
        profile_card.pack(fill="x", pady=(0, 12))
        profile_body = tk.Frame(profile_card.body, bg=ELEVATED)
        profile_body.pack(fill="x", padx=16, pady=14)

        row_top = tk.Frame(profile_body, bg=ELEVATED)
        row_top.pack(fill="x")
        ttk.Label(row_top, text="PROFILE", background=ELEVATED, foreground=TEXT_TERTIARY,
                  font=(FONT_FAMILY, 8, "bold")).pack(anchor="w")

        row_mid = tk.Frame(profile_body, bg=ELEVATED)
        row_mid.pack(fill="x", pady=(4, 0))
        self.profile_name_lbl = ttk.Label(row_mid, text="—", background=ELEVATED,
                                           foreground=TEXT_PRIMARY, font=(FONT_FAMILY, 14, "bold"))
        self.profile_name_lbl.pack(side="left")

        sep_dot = tk.Label(row_mid, text="•", bg=ELEVATED, fg=TEXT_TERTIARY, font=(FONT_FAMILY, 11))
        sep_dot.pack(side="left", padx=8)

        ttk.Label(row_mid, text="Base:", background=ELEVATED, foreground=TEXT_SECONDARY,
                  font=(FONT_FAMILY, 9)).pack(side="left")
        self.base_text_lbl = ttk.Label(row_mid, text="••••••", background=ELEVATED,
                                        foreground=TEXT_SECONDARY, font=(MONO_FAMILY, 9))
        self.base_text_lbl.pack(side="left", padx=(5, 0))

        FlatButton(row_mid, "👁", command=self.reveal_base_text, kind="ghost",
                   width=30, height=26, font_size=10, anchor_bg=ELEVATED).pack(side="right")

        ttk.Checkbutton(
            profile_body,
            text="Auto-copy on launch",
            variable=self.auto_copy_var,
            command=self.toggle_auto_copy,
            style="TCheckbutton",
        ).pack(anchor="w", pady=(10, 0))

        # ---- TOTP + Password combined card ----
        totp_card = RoundedCard(content, bg=ELEVATED, border=BORDER, radius=16)
        totp_card.pack(fill="both", expand=True)
        totp_body = tk.Frame(totp_card.body, bg=ELEVATED)
        totp_body.pack(fill="both", expand=True, padx=20, pady=18)

        # Top row: TOTP value + countdown ring side-by-side
        totp_row = tk.Frame(totp_body, bg=ELEVATED)
        totp_row.pack(fill="x")

        totp_left = tk.Frame(totp_row, bg=ELEVATED)
        totp_left.pack(side="left", fill="x", expand=True)
        ttk.Label(totp_left, text="CURRENT TOTP", background=ELEVATED,
                  foreground=TEXT_TERTIARY, font=(FONT_FAMILY, 8, "bold")).pack(anchor="w")
        self.totp_display = tk.Label(
            totp_left, text="------", bg=ELEVATED, fg=ACCENT,
            font=(MONO_FAMILY, 30, "bold"),
        )
        self.totp_display.pack(anchor="w", pady=(4, 0))

        # Countdown ring on the right
        canvas_size = 76
        ring_frame = tk.Frame(totp_row, bg=ELEVATED)
        ring_frame.pack(side="right")
        self.countdown_canvas = tk.Canvas(
            ring_frame, width=canvas_size, height=canvas_size,
            bg=ELEVATED, highlightthickness=0,
        )
        self.countdown_canvas.pack()
        # Track (background) ring
        self.countdown_canvas.create_oval(
            5, 5, canvas_size - 5, canvas_size - 5,
            outline=ELEVATED_2, width=6,
        )
        self._countdown_arc = self.countdown_canvas.create_arc(
            5, 5, canvas_size - 5, canvas_size - 5,
            start=90, extent=0, style="arc", width=6, outline=ACCENT,
        )
        self._countdown_text = self.countdown_canvas.create_text(
            canvas_size / 2, canvas_size / 2, text="--",
            fill=TEXT_PRIMARY, font=(FONT_FAMILY, 14, "bold"),
        )
        self.expiry_label = ttk.Label(ring_frame, text="Expires in --s", background=ELEVATED,
                                       foreground=WARNING, font=(FONT_FAMILY, 9, "bold"))
        self.expiry_label.pack(pady=(6, 0))

        # Separator
        sep_line = tk.Frame(totp_body, height=1, bg=BORDER_SUBTLE)
        sep_line.pack(fill="x", pady=18)

        # Generated password field
        ttk.Label(totp_body, text="GENERATED PASSWORD", background=ELEVATED,
                  foreground=TEXT_TERTIARY, font=(FONT_FAMILY, 8, "bold")).pack(anchor="w")
        pw_wrap = tk.Frame(totp_body, bg=ELEVATED_2, highlightbackground=BORDER,
                            highlightthickness=1, bd=0)
        pw_wrap.pack(fill="x", pady=(6, 16))
        self.password_entry = tk.Entry(
            pw_wrap,
            textvariable=self.generated_var,
            font=(MONO_FAMILY, 14),
            state="readonly",
            readonlybackground=ELEVATED_2,
            fg=TEXT_PRIMARY,
            relief="flat",
            highlightthickness=0,
            bd=0,
            justify="left",
        )
        self.password_entry.pack(fill="x", padx=12, pady=10)

        # ===== ACTION BUTTONS =====
        btn_row = tk.Frame(totp_body, bg=ELEVATED)
        btn_row.pack(fill="x")
        copy_btn = FlatButton(btn_row, "📋  COPY PASSWORD", command=self.copy_current_value,
                               kind="primary", width=200, height=42, font_size=10, anchor_bg=ELEVATED)
        copy_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))
        FlatButton(btn_row, "🔑  TOTP Only", command=self.copy_totp_only, kind="secondary",
                   width=120, height=42, font_size=10, anchor_bg=ELEVATED).pack(side="left", expand=True, fill="x", padx=6)
        FlatButton(btn_row, "↻  Refresh", command=self.refresh_now, kind="secondary",
                   width=100, height=42, font_size=10, anchor_bg=ELEVATED).pack(side="left", expand=True, fill="x", padx=(6, 0))

        # ---- Bottom toolbar ----
        toolbar_card = RoundedCard(content, bg=ELEVATED, border=BORDER, radius=12)
        toolbar_card.pack(fill="x", pady=(12, 0))
        toolbar = tk.Frame(toolbar_card.body, bg=ELEVATED)
        toolbar.pack(fill="x", padx=10, pady=10)
        for txt, cmd in [
            ("📝  Edit Profile", self.edit_profile),
            ("⬆  Export", self.export_profiles),
            ("⬇  Import", self.import_profiles),
        ]:
            FlatButton(toolbar, txt, command=cmd, kind="ghost", width=130, height=36,
                       font_size=9, bold=False, anchor_bg=ELEVATED).pack(side="left", expand=True, fill="x", padx=4)

    # -----------------------------------------------------------------------
    def _build_footer(self, parent: tk.Frame) -> None:
        footer = tk.Frame(parent, bg=BG)
        footer.pack(fill="x", pady=(14, 0))

        status_dot = tk.Canvas(footer, width=8, height=8, bg=BG, highlightthickness=0)
        status_dot.create_oval(0, 0, 8, 8, fill=SUCCESS, outline=SUCCESS)
        status_dot.pack(side="left", padx=(0, 6))
        ttk.Label(footer, textvariable=self.status_var, style="Status.TLabel").pack(side="left")

        self.offline_lbl = ttk.Label(footer, text="Offline Mode", style="Muted.TLabel")
        self.offline_lbl.pack(side="right", padx=(10, 0))
        sep1 = tk.Label(footer, text="·", bg=BG, fg=TEXT_TERTIARY)
        sep1.pack(side="right")
        self.clipboard_lbl = ttk.Label(footer, text="Clipboard Ready", style="Muted.TLabel")
        self.clipboard_lbl.pack(side="right", padx=(10, 0))
        sep2 = tk.Label(footer, text="·", bg=BG, fg=TEXT_TERTIARY)
        sep2.pack(side="right")
        self.last_copy_lbl = ttk.Label(footer, text="Last copy: –", style="Muted.TLabel")
        self.last_copy_lbl.pack(side="right", padx=(0, 10))

    # -----------------------------------------------------------------------
    # Profile handling helpers
    # -----------------------------------------------------------------------
    def _refresh_profile_options(self) -> None:
        self.profile_listbox.delete(0, "end")
        for name in self.manager.names:
            self.profile_listbox.insert("end", f"  {name}")
        active = self.manager.active_profile_name
        if active and active in self.manager.names:
            idx = self.manager.names.index(active)
            self.profile_listbox.selection_set(idx)
            self.profile_listbox.see(idx)
            self._load_profile(active)

    def _filter_profiles(self, query: str) -> None:
        filtered = [n for n in self.manager.names if query.lower() in n.lower()]
        self.profile_listbox.delete(0, "end")
        for name in filtered:
            self.profile_listbox.insert("end", f"  {name}")

    def _on_sidebar_select(self, event: tk.Event) -> None:
        sel = self.profile_listbox.curselection()
        if sel:
            name = self.profile_listbox.get(sel[0]).strip()
            self.manager.set_active_profile(name)
            self._load_profile(name)

    def _load_profile(self, name: str) -> None:
        profile = self.manager.get_active_profile()
        if profile:
            self.profile_name_lbl.config(text=profile.name)
            masked = profile.baseText[:2] + "…" * max(0, len(profile.baseText) - 2)
            self.base_text_lbl.config(text=masked)
            self.status_var.set(f"Active profile: {profile.name}")
        else:
            self.profile_name_lbl.config(text="-")
            self.base_text_lbl.config(text="••••••")

    # -----------------------------------------------------------------------
    # Refresh loop – updates TOTP, countdown, generated password
    # -----------------------------------------------------------------------
    def refresh_loop(self) -> None:
        profile = self.manager.get_active_profile()
        if profile:
            try:
                totp = generate_value(profile.baseText, profile.secret)
                self.current_value = totp
                self.generated_var.set(totp)
                self.totp_display.config(text=totp[-6:])
                remaining = seconds_remaining()
                self.countdown_var.set(f"{remaining} second{'s' if remaining != 1 else ''}")
                extent = (remaining / 30) * 360
                self.countdown_canvas.itemconfigure(self._countdown_arc, extent=-extent)
                self.countdown_canvas.itemconfigure(self._countdown_text, text=str(remaining))
                ring_color = WARNING if remaining <= 5 else ACCENT
                self.countdown_canvas.itemconfigure(self._countdown_arc, outline=ring_color)
                self.expiry_label.config(text=f"Expires in {remaining}s",
                                          foreground=(WARNING if remaining <= 5 else TEXT_SECONDARY))
                if self.manager.auto_copy_on_launch and not self._auto_copied:
                    self.copy_current_value(show_dialog=False)
                    self._auto_copied = True
                if not self._history or self._history[-1] != totp:
                    self._history.append(totp)
                    if len(self._history) > 5:
                        self._history.pop(0)
                    self.last_copy_lbl.config(text=f"Last copy: {totp[-6:]}")
            except OtpError as exc:
                self.current_value = ""
                self.generated_var.set("Invalid secret")
                self.totp_display.config(text="------")
                self.countdown_var.set("-- seconds")
                self.status_var.set(str(exc))
        else:
            self.current_value = ""
            self.generated_var.set("Add a profile to begin")
            self.totp_display.config(text="------")
            self.countdown_var.set("-- seconds")
        self._refresh_job = self.root.after(1000, self.refresh_loop)

    def refresh_now(self) -> None:
        if self._refresh_job:
            self.root.after_cancel(self._refresh_job)
        self.refresh_loop()

    # -----------------------------------------------------------------------
    # Copy actions
    # -----------------------------------------------------------------------
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
        Toast(self.root, "Password copied!")
        self.last_copy_lbl.config(text=f"Last copy: {self.current_value[-6:]}")

    def copy_totp_only(self) -> None:
        if not self.current_value:
            self.status_var.set("No TOTP to copy.")
            Toast(self.root, "No TOTP to copy.", kind="error")
            return
        totp_part = self.current_value[-6:]
        self.root.clipboard_clear()
        self.root.clipboard_append(totp_part)
        self.root.update()
        self.status_var.set(f"Copied TOTP: {totp_part}")
        Toast(self.root, "TOTP copied!")
        self.last_copy_lbl.config(text=f"Last copy: {totp_part}")

    def reveal_base_text(self) -> None:
        profile = self.manager.get_active_profile()
        if profile:
            self.base_text_lbl.config(text=profile.baseText)
        else:
            messagebox.showinfo("TOTP Clipboard", "No profile selected.")

    # -----------------------------------------------------------------------
    def open_settings(self) -> None:
        messagebox.showinfo("Settings", "Settings dialog not implemented yet.")

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

    # -----------------------------------------------------------------------
    def toggle_auto_copy(self) -> None:
        enabled = self.auto_copy_var.get()
        self.manager.set_auto_copy_on_launch(enabled)
        self.status_var.set("Auto Copy on Launch enabled." if enabled else "Auto Copy on Launch disabled.")

    # -----------------------------------------------------------------------
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
        if not profile:
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
        if not profile:
            messagebox.showwarning("TOTP Clipboard", "Select a profile to delete.")
            return
        if not messagebox.askyesno("TOTP Clipboard", f"Delete profile '{profile.name}'?"):
            return
        self.manager.delete_profile(profile.name)
        self._refresh_profile_options()
        self.status_var.set(f"Deleted profile: {profile.name}")

    # -----------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Profile dialog – restyled to match the premium dark theme
# ---------------------------------------------------------------------------
class ProfileDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, title: str, profile: Profile | None = None) -> None:
        super().__init__(parent)
        self.result: Profile | None = None
        self.configure(bg=BG)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.name_var = tk.StringVar(value=profile.name if profile else "")
        self.base_var = tk.StringVar(value=profile.baseText if profile else "")
        self.secret_var = tk.StringVar(value=profile.secret if profile else "")

        card = RoundedCard(self, bg=ELEVATED, border=BORDER, radius=14)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        frame = tk.Frame(card.body, bg=ELEVATED)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ttk.Label(frame, text=title, background=ELEVATED, foreground=TEXT_PRIMARY,
                  font=(FONT_FAMILY, 15, "bold")).pack(anchor="w", pady=(0, 16))
        self._entry(frame, "Name", self.name_var)
        self._entry(frame, "Base Text", self.base_var)
        self._entry(frame, "Base32 Secret", self.secret_var, show="")

        button_row = tk.Frame(frame, bg=ELEVATED)
        button_row.pack(fill="x", pady=(20, 0))
        FlatButton(button_row, "Save", command=self.save, kind="primary",
                   width=100, height=38, font_size=10, anchor_bg=ELEVATED).pack(side="right")
        FlatButton(button_row, "Cancel", command=self.destroy, kind="secondary",
                   width=100, height=38, font_size=10, anchor_bg=ELEVATED).pack(side="right", padx=(0, 8))

        self.bind("<Return>", lambda _event: self.save())
        self.bind("<Escape>", lambda _event: self.destroy())

        # Size the window to fit its actual content rather than a hardcoded
        # guess, so the Save/Cancel row is never clipped off the bottom.
        self.update_idletasks()
        width = max(440, frame.winfo_reqwidth() + 72)
        height = frame.winfo_reqheight() + 72
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")

        self.wait_window()

    def _entry(self, parent: tk.Frame, label: str, variable: tk.StringVar, show: str | None = None) -> None:
        ttk.Label(parent, text=label.upper(), background=ELEVATED, foreground=TEXT_TERTIARY,
                  font=(FONT_FAMILY, 8, "bold")).pack(anchor="w", pady=(8, 4))
        wrap = tk.Frame(parent, bg=ELEVATED_2, highlightbackground=BORDER, highlightthickness=1, bd=0)
        wrap.pack(fill="x")
        entry = tk.Entry(
            wrap, textvariable=variable, show=show if show is not None else "",
            bg=ELEVATED_2, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY,
            relief="flat", highlightthickness=0, bd=0, font=(FONT_FAMILY, 10),
        )
        entry.pack(fill="x", padx=10, pady=8)

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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    manager = ProfileManager(Path("profiles.json"))
    app = TOTPClipboardApp(root, manager)
    root.mainloop()
