"""Main application class — glues service management, UI, and lifecycle together."""

from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # type: ignore[attr-defined]  # noqa: E402

try:
    gi.require_version("Notify", "0.7")
    from gi.repository import Notify  # type: ignore[attr-defined]
    HAS_NOTIFY = True
except (ValueError, ImportError):
    HAS_NOTIFY = False

from .config import (
    APP_NAME, ICON_RUNNING, ICON_STOPPED,
    LOCK_FILE, POLL_INTERVAL_SEC, SERVICE_DST,
)
from .settings import exists as settings_exist, get_mount_point, save as save_settings
from .service import SystemdService, shutdown_pool
from .ui import (
    TrayMenu, create_indicator, open_live_logs, open_mount_folder,
    show_settings_dialog, _find_term_cmd,
)
from .utils import InstanceLock, is_autostart_enabled, enable_autostart, disable_autostart

log = logging.getLogger(__name__)


class RcloneTray:
    """System-tray application that manages an rclone systemd user service."""

    def __init__(self) -> None:
        self._lock = InstanceLock(LOCK_FILE)
        self._svc = SystemdService()
        self._prev_running: bool | None = None
        self._poll_lock = threading.Lock()
        self._poll_busy = False
        self._poll_gen = 0
        self._poll_source_id: int | None = None
        self._shutting_down = False

        self._lock.acquire()
        try:
            self._init_notifications()

            if not settings_exist():
                log.info("First run — opening settings dialog")
                initial = show_settings_dialog()
                if initial is None:
                    log.info("Setup cancelled, exiting.")
                    raise SystemExit(0)
                save_settings(initial)

            os.makedirs(get_mount_point(), exist_ok=True)

            if not os.path.isfile(SERVICE_DST):
                self._svc.install()
            self._svc.enable_and_start()

            self._indicator = create_indicator()
            self._menu = TrayMenu(
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
            self._indicator.set_menu(self._menu.gtk_menu)

            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self._quit)
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self._quit)

            self._update_autostart_label()
            self._refresh()
            self._poll_source_id = GLib.timeout_add_seconds(
                POLL_INTERVAL_SEC, self._refresh,
            )
        except SystemExit:
            self._lock.release()
            raise
        except Exception:
            self._lock.release()
            raise

    @staticmethod
    def _init_notifications() -> None:
        if HAS_NOTIFY:
            Notify.init(APP_NAME)  # type: ignore[possibly-unbound]

    @staticmethod
    def _notify(title: str, body: str, icon: str) -> None:
        if not HAS_NOTIFY:
            return
        try:
            n = Notify.Notification.new(title, body, icon)  # type: ignore[possibly-unbound]
            n.set_urgency(Notify.Urgency.NORMAL)  # type: ignore[possibly-unbound]
            n.show()
        except Exception as e:
            log.debug("Notification failed: %s", e)

    def _refresh(self) -> bool:
        """Kick off a background poll; skip if one is already running."""
        with self._poll_lock:
            if self._poll_busy:
                return True
            self._poll_busy = True
            self._poll_gen += 1
            gen = self._poll_gen
        threading.Thread(target=self._poll_worker, args=(gen,), daemon=True).start()
        return True

    def _poll_worker(self, gen: int) -> None:
        """Collect service state off-thread, then push UI update to GTK."""
        try:
            running = self._svc.is_running()
            uptime = self._svc.get_uptime() if running else None
            used, total = self._svc.get_mount_usage() if running else (None, None)
            GLib.idle_add(self._apply_state, gen, running, uptime, used, total)
        except Exception as e:
            log.debug("Poll failed: %s", e)
            with self._poll_lock:
                self._poll_busy = False

    def _apply_state(
        self,
        gen: int,
        running: bool,
        uptime: str | None,
        used: str | None,
        total: str | None,
    ) -> bool:
        """Update the UI from poll results (runs on GTK main thread)."""
        with self._poll_lock:
            self._poll_busy = False
            # Discard stale results from an older poll cycle
            if gen < self._poll_gen:
                return False

        m = self._menu

        self._indicator.set_icon_full(
            ICON_RUNNING if running else ICON_STOPPED,
            "Running" if running else "Stopped",
        )

        m.status_item.set_label(
            "Mounted  -  Running" if running else "Unmounted  -  Stopped"
        )

        if running:
            parts: list[str] = []
            if uptime:
                parts.append(f"Uptime: {uptime}")
            if used and total:
                parts.append(f"{used} / {total}")
            if parts:
                m.info_item.set_label("  ".join(parts))
                m.info_item.show()
            else:
                m.info_item.hide()
        else:
            m.info_item.hide()

        m.start_item.set_sensitive(not running)
        m.stop_item.set_sensitive(running)
        m.restart_item.set_sensitive(running)

        if self._prev_running is not None and self._prev_running != running:
            if running:
                self._notify("Rclone Mount", "Remote mounted.", ICON_RUNNING)
            else:
                self._notify("Rclone Mount", "Remote unmounted.", ICON_STOPPED)
            log.info("State changed -> %s", "running" if running else "stopped")
        self._prev_running = running

        return False  # run once, not repeating

    def _run_async(self, *actions: str) -> None:
        """Run service actions off the GTK main thread, then refresh UI."""
        def _worker() -> None:
            for a in actions:
                getattr(self._svc, a)()
            GLib.idle_add(self._refresh)
        threading.Thread(target=_worker, daemon=True).start()

    def _on_start(self, _: object) -> None:
        log.info("Starting mount...")
        self._menu.start_item.set_sensitive(False)
        self._run_async("start")

    def _on_stop(self, _: object) -> None:
        log.info("Stopping mount...")
        self._menu.stop_item.set_sensitive(False)
        self._run_async("stop")

    def _on_restart(self, _: object) -> None:
        log.info("Restarting mount...")
        self._menu.restart_item.set_sensitive(False)
        self._run_async("restart")

    def _on_open_folder(self, _: object) -> None:
        open_mount_folder()

    def _on_view_logs(self, _: object) -> None:
        open_live_logs()

    def _on_settings(self, _: object) -> None:
        """Open settings dialog; on save, apply new settings and restart service."""
        new_settings = show_settings_dialog()
        if new_settings is None:
            return
        log.info("Applying new settings...")
        save_settings(new_settings)

        def _worker() -> None:
            self._svc.stop()
            os.makedirs(os.path.expanduser(new_settings["mount_point"]), exist_ok=True)
            self._svc.install(new_settings)
            self._svc.enable_and_start()
            log.info("Settings applied, service restarted.")
            GLib.idle_add(self._refresh)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_toggle_autostart(self, _: object) -> None:
        if is_autostart_enabled():
            disable_autostart()
            self._notify("Rclone Mount", "Autostart disabled.", ICON_STOPPED)
        else:
            enable_autostart()
            self._notify("Rclone Mount", "Autostart enabled.", ICON_RUNNING)
        self._update_autostart_label()

    def _update_autostart_label(self) -> None:
        label = "Disable Autostart" if is_autostart_enabled() else "Enable Autostart"
        self._menu.autostart_item.set_label(label)

    def _on_reconfigure(self, _: object) -> None:
        """Tear down mount, run rclone config, then re-bootstrap."""
        log.info("Reconfiguring rclone...")

        def _worker() -> None:
            self._svc.uninstall()
            mount = get_mount_point()
            shutil.rmtree(mount, ignore_errors=True)
            log.info("Removed mount folder %s", mount)

            term_cmd = _find_term_cmd()
            if term_cmd:
                try:
                    with subprocess.Popen(term_cmd + ["rclone", "config"]) as proc:
                        proc.wait()
                except Exception as e:
                    log.error("rclone config failed: %s", e)

            os.makedirs(get_mount_point(), exist_ok=True)
            self._svc.install()
            self._svc.enable_and_start()
            log.info("Reconfiguration complete, service restarted.")
            GLib.idle_add(self._refresh)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_quit(self, _: object) -> None:
        self._quit()

    def _on_uninstall(self, _: object) -> None:
        """Uninstall service off the main thread to avoid UI freeze."""
        log.info("Uninstalling service...")
        self._menu.autostart_item.set_sensitive(False)

        def _worker() -> None:
            self._svc.uninstall()
            disable_autostart()
            GLib.idle_add(self._finish_uninstall)

        threading.Thread(target=_worker, daemon=True).start()

    def _finish_uninstall(self) -> bool:
        self._notify("Rclone Mount", "Service uninstalled.", ICON_STOPPED)
        log.info("Removed service, autostart disabled.")
        self._shutdown()
        return False

    def _quit(self) -> bool:
        """Stop service off the main thread, then shut down."""
        log.info("Quitting...")

        def _worker() -> None:
            self._svc.disable_and_stop()
            GLib.idle_add(self._shutdown)

        threading.Thread(target=_worker, daemon=True).start()
        return False

    def _shutdown(self) -> bool:
        if self._shutting_down:
            return False
        self._shutting_down = True

        if self._poll_source_id is not None:
            GLib.source_remove(self._poll_source_id)
            self._poll_source_id = None

        shutdown_pool()

        if HAS_NOTIFY:
            Notify.uninit()  # type: ignore[possibly-unbound]
        self._lock.release()
        Gtk.main_quit()
        return False

    def run(self) -> None:
        Gtk.main()
