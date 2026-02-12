"""Cross-platform system tray icon using pystray + Pillow."""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

from PIL import Image
import pystray

from .config import APP_NAME, ICON_RUNNING, ICON_STOPPED

log = logging.getLogger(__name__)


def _load_icon(path: str) -> Image.Image:
    """Load an icon from disk, or create a fallback colored square."""
    try:
        return Image.open(path)
    except Exception:
        img = Image.new("RGBA", (64, 64), (128, 128, 128, 255))
        return img


class TrayIcon:
    """pystray-based system tray with dynamic menu and icon swapping."""

    def __init__(
        self,
        *,
        on_start: Callable,
        on_stop: Callable,
        on_restart: Callable,
        on_open_folder: Callable,
        on_view_logs: Callable,
        on_reconfigure: Callable,
        on_settings: Callable,
        on_toggle_autostart: Callable,
        on_quit: Callable,
        on_uninstall: Callable,
    ) -> None:
        self._icon_running = _load_icon(ICON_RUNNING)
        self._icon_stopped = _load_icon(ICON_STOPPED)
        self._running = False
        self._status_text = "Checking..."
        self._info_text = ""
        self._start_enabled = True
        self._stop_enabled = False
        self._restart_enabled = False
        self._autostart_label = "Enable Autostart"

        self._on_start = on_start
        self._on_stop = on_stop
        self._on_restart = on_restart
        self._on_open_folder = on_open_folder
        self._on_view_logs = on_view_logs
        self._on_reconfigure = on_reconfigure
        self._on_settings = on_settings
        self._on_toggle_autostart = on_toggle_autostart
        self._on_quit = on_quit
        self._on_uninstall = on_uninstall

        self._icon: Optional[pystray.Icon] = None

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(
                lambda _: self._status_text,
                action=None,
                enabled=False,
            ),
            pystray.MenuItem(
                lambda _: self._info_text,
                action=None,
                enabled=False,
                visible=lambda _: bool(self._info_text),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Start Mount",
                lambda: self._on_start(),
                enabled=lambda _: self._start_enabled,
            ),
            pystray.MenuItem(
                "Stop Mount",
                lambda: self._on_stop(),
                enabled=lambda _: self._stop_enabled,
            ),
            pystray.MenuItem(
                "Restart Mount",
                lambda: self._on_restart(),
                enabled=lambda _: self._restart_enabled,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Mount Folder", lambda: self._on_open_folder()),
            pystray.MenuItem("View Logs", lambda: self._on_view_logs()),
            pystray.MenuItem("Reconfigure Rclone", lambda: self._on_reconfigure()),
            pystray.MenuItem("Settings", lambda: self._on_settings()),
            pystray.MenuItem(
                lambda _: self._autostart_label,
                lambda: self._on_toggle_autostart(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Uninstall Service", lambda: self._on_uninstall()),
            pystray.MenuItem("Quit (Unmount && Disable)", lambda: self._on_quit()),
        )

    def update(
        self,
        *,
        running: bool,
        status_text: str,
        info_text: str,
        start_enabled: bool,
        stop_enabled: bool,
        restart_enabled: bool,
        autostart_label: str,
    ) -> None:
        """Update tray state — call from any thread, pystray will refresh."""
        self._running = running
        self._status_text = status_text
        self._info_text = info_text
        self._start_enabled = start_enabled
        self._stop_enabled = stop_enabled
        self._restart_enabled = restart_enabled
        self._autostart_label = autostart_label

        if self._icon:
            self._icon.icon = self._icon_running if running else self._icon_stopped
            self._icon.update_menu()

    def set_start_enabled(self, v: bool) -> None:
        self._start_enabled = v
        if self._icon:
            self._icon.update_menu()

    def set_stop_enabled(self, v: bool) -> None:
        self._stop_enabled = v
        if self._icon:
            self._icon.update_menu()

    def set_restart_enabled(self, v: bool) -> None:
        self._restart_enabled = v
        if self._icon:
            self._icon.update_menu()

    def notify(self, title: str, message: str) -> None:
        """Show a desktop notification if supported."""
        if self._icon:
            try:
                self._icon.notify(message, title=title)
            except Exception as e:
                log.debug("Notification failed: %s", e)

    def stop(self) -> None:
        """Stop the tray icon event loop."""
        if self._icon:
            self._icon.stop()

    def run(self) -> None:
        """Start the tray icon — blocks until stop() is called."""
        self._icon = pystray.Icon(
            name=APP_NAME,
            icon=self._icon_stopped,
            title=APP_NAME,
            menu=self._build_menu(),
        )
        self._icon.run()

    def run_detached(self) -> None:
        """Start the tray icon in a background thread (returns immediately)."""
        self._icon = pystray.Icon(
            name=APP_NAME,
            icon=self._icon_stopped,
            title=APP_NAME,
            menu=self._build_menu(),
        )
        self._icon.run_detached()
