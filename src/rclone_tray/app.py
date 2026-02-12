"""Main application class — platform-agnostic orchestrator."""

from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import threading
import time

from .config import (
    APP_NAME, ICON_RUNNING, ICON_STOPPED, LOCK_FILE,
    POLL_INTERVAL_SEC, PLATFORM, SERVICE_NAME,
)
from .settings import (
    exists as settings_exist,
    get_mount_point,
    save as save_settings,
)
from .platform import (
    get_autostart_backend,
    get_dialog_backend,
    get_instance_lock,
    get_service_backend,
)
from .tray import TrayIcon

log = logging.getLogger(__name__)


class RcloneTray:
    """System-tray application that manages an rclone mount."""

    def __init__(self) -> None:
        self._lock = get_instance_lock(LOCK_FILE)
        self._svc = get_service_backend()
        self._dlg = get_dialog_backend()
        self._autostart = get_autostart_backend()
        self._prev_running: bool | None = None
        self._stop_event = threading.Event()

        self._lock.acquire()

        if not settings_exist():
            log.info("First run — opening settings dialog")
            initial = self._dlg.show_settings()
            if initial is None:
                log.info("Setup cancelled, exiting.")
                self._lock.release()
                raise SystemExit(0)
            save_settings(initial)

        os.makedirs(get_mount_point(), exist_ok=True)

        if not self._svc.is_installed():
            self._svc.install()
        self._svc.enable_and_start()

        self._tray = TrayIcon(
            on_start=self._on_start,
            on_stop=self._on_stop,
            on_restart=self._on_restart,
            on_open_folder=self._on_open_folder,
            on_view_logs=self._on_view_logs,
            on_reconfigure=self._on_reconfigure,
            on_settings=self._on_settings,
            on_toggle_autostart=self._on_toggle_autostart,
            on_quit=self._on_quit,
            on_uninstall=self._on_uninstall,
        )

        signal.signal(signal.SIGINT, self._signal_quit)
        signal.signal(signal.SIGTERM, self._signal_quit)

        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _signal_quit(self, _sig: int, _frame: object) -> None:
        self._quit()

    def _poll_loop(self) -> None:
        """Periodically poll service state and update the tray."""
        while not self._stop_event.is_set():
            self._refresh()
            self._stop_event.wait(POLL_INTERVAL_SEC)

    def _refresh(self) -> None:
        """Poll service state and update the tray UI."""
        running = self._svc.is_running()

        status_text = "Mounted  -  Running" if running else "Unmounted  -  Stopped"
        info_text = ""

        if running:
            parts: list[str] = []
            uptime = self._svc.get_uptime()
            if uptime:
                parts.append(f"Uptime: {uptime}")
            used, total = self._svc.get_mount_usage()
            if used and total:
                parts.append(f"{used} / {total}")
            if parts:
                info_text = "  ".join(parts)

        autostart_label = (
            "Disable Autostart"
            if self._autostart.is_enabled()
            else "Enable Autostart"
        )

        self._tray.update(
            running=running,
            status_text=status_text,
            info_text=info_text,
            start_enabled=not running,
            stop_enabled=running,
            restart_enabled=running,
            autostart_label=autostart_label,
        )

        if self._prev_running is not None and self._prev_running != running:
            if running:
                self._tray.notify("Rclone Mount", "Remote mounted.")
            else:
                self._tray.notify("Rclone Mount", "Remote unmounted.")
            log.info("State changed -> %s", "running" if running else "stopped")
        self._prev_running = running

    def _run_async(self, fn: callable, *args: object) -> None:
        """Run a function in a background thread, then refresh."""
        def _worker() -> None:
            fn(*args)
            self._refresh()
        threading.Thread(target=_worker, daemon=True).start()

    def _on_start(self) -> None:
        log.info("Starting mount...")
        self._tray.set_start_enabled(False)
        self._run_async(self._svc.start)

    def _on_stop(self) -> None:
        log.info("Stopping mount...")
        self._tray.set_stop_enabled(False)
        self._run_async(self._svc.stop)

    def _on_restart(self) -> None:
        log.info("Restarting mount...")
        self._tray.set_restart_enabled(False)
        self._run_async(self._svc.restart)

    def _on_open_folder(self) -> None:
        self._dlg.open_folder(get_mount_point())

    def _on_view_logs(self) -> None:
        if PLATFORM == "linux":
            cmd = [
                "journalctl", "--user", "-u", SERVICE_NAME, "-f", "--no-pager",
            ]
            if self._dlg.open_terminal_with(cmd):
                return
        text = self._svc.get_logs(100)
        self._dlg.show_logs(text)

    def _on_settings(self) -> None:
        new_settings = self._dlg.show_settings()
        if new_settings is None:
            return
        log.info("Applying new settings...")
        save_settings(new_settings)

        def _worker() -> None:
            self._svc.stop()
            os.makedirs(
                os.path.expanduser(new_settings["mount_point"]), exist_ok=True
            )
            self._svc.install(new_settings)
            self._svc.enable_and_start()
            log.info("Settings applied, service restarted.")
            self._refresh()

        threading.Thread(target=_worker, daemon=True).start()

    def _on_toggle_autostart(self) -> None:
        if self._autostart.is_enabled():
            self._autostart.disable()
            self._tray.notify("Rclone Mount", "Autostart disabled.")
        else:
            self._autostart.enable()
            self._tray.notify("Rclone Mount", "Autostart enabled.")
        self._refresh()

    def _on_reconfigure(self) -> None:
        log.info("Reconfiguring rclone...")

        def _worker() -> None:
            self._svc.uninstall()
            mount = get_mount_point()
            shutil.rmtree(mount, ignore_errors=True)
            log.info("Removed mount folder %s", mount)
            self._refresh()

            cmd = ["rclone", "config"]
            if not self._dlg.open_terminal_with(cmd):
                try:
                    subprocess.run(cmd, check=False)
                except Exception as e:
                    log.error("rclone config failed: %s", e)

            os.makedirs(get_mount_point(), exist_ok=True)
            self._svc.install()
            self._svc.enable_and_start()
            log.info("Reconfiguration complete, service restarted.")
            self._refresh()

        threading.Thread(target=_worker, daemon=True).start()

    def _on_quit(self) -> None:
        self._quit()

    def _on_uninstall(self) -> None:
        log.info("Uninstalling service...")
        self._svc.uninstall()
        self._autostart.disable()
        self._tray.notify("Rclone Mount", "Service uninstalled.")
        log.info("Removed service, autostart disabled.")
        self._shutdown()

    def _quit(self) -> None:
        log.info("Quitting...")
        self._svc.disable_and_stop()
        self._shutdown()

    def _shutdown(self) -> None:
        self._stop_event.set()
        self._lock.release()
        self._tray.stop()

    def run(self) -> None:
        """Start the application — blocks until quit."""
        self._tray.run()
