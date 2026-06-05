"""System tray support for TOTP Clipboard."""

from __future__ import annotations

import threading
from typing import Callable

import pystray
from PIL import Image, ImageDraw


class TrayApp:
    def __init__(
        self,
        on_open: Callable[[], None],
        on_copy: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        self.on_open = on_open
        self.on_copy = on_copy
        self.on_exit = on_exit
        self.icon: pystray.Icon | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.icon is not None:
            return

        self.icon = pystray.Icon(
            "TOTP Clipboard",
            self._create_icon(),
            "TOTP Clipboard",
            pystray.Menu(
                pystray.MenuItem("Open", lambda: self.on_open(), default=True),
                pystray.MenuItem("Copy Current Value", lambda: self.on_copy()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", lambda: self.stop_and_exit()),
            ),
        )
        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.icon is not None:
            self.icon.stop()
            self.icon = None

    def stop_and_exit(self) -> None:
        self.on_exit()

    @staticmethod
    def _create_icon() -> Image.Image:
        image = Image.new("RGBA", (64, 64), (18, 22, 30, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, 56, 56), radius=12, fill=(35, 120, 210, 255))
        draw.ellipse((20, 16, 44, 40), fill=(245, 248, 252, 255))
        draw.rectangle((28, 32, 36, 48), fill=(245, 248, 252, 255))
        return image
