"""macOS service backend using launchd / launchctl."""

from __future__ import annotations

import logging
import os
import plistlib
import shutil
import subprocess
import time
from typing import Optional

from ...config import LAUNCH_AGENT_PLIST, LOG_FILE
from ...settings import get_mount_point, load as load_settings
from ..base import ServiceBackend

log = logging.getLogger(__name__)

_LABEL = "com.rclone-tray.mount"
_TIMEOUT = 30


def _fmt_duration(seconds: int) -> str:
    d, seconds = divmod(seconds, 86400)
    h, seconds = divmod(seconds, 3600)
    m, s = divmod(seconds, 60)
    parts: list[str] = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if not parts:
        parts.append(f"{s}s")
    return " ".join(parts)


def _fmt_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


class MacService(ServiceBackend):
    """Manage rclone mount via launchd on macOS."""

    @staticmethod
    def _generate_plist(settings: dict[str, str] | None = None) -> dict:
        if settings is None:
            settings = load_settings()
        remote = settings.get("remote", "gdrive:")
        mount = os.path.expanduser(settings.get("mount_point", "~/GoogleDrive"))
        cache_mode = settings.get("vfs_cache_mode", "full")
        cache_size = settings.get("vfs_cache_max_size", "10G")
        write_back = settings.get("vfs_write_back", "5s")
        dir_cache = settings.get("dir_cache_time", "2m")
        stats = settings.get("stats_interval", "30s")

        rclone_bin = shutil.which("rclone") or "/usr/local/bin/rclone"

        program_args = [
            rclone_bin, "mount", remote, mount,
            "--vfs-cache-mode", cache_mode,
            "--vfs-cache-max-size", cache_size,
            "--vfs-write-back", write_back,
            "--dir-cache-time", dir_cache,
            "-v",
            "--stats", stats,
            "--stats-one-line",
            "--log-file", LOG_FILE,
        ]

        return {
            "Label": _LABEL,
            "ProgramArguments": program_args,
            "RunAtLoad": False,
            "KeepAlive": True,
            "StandardOutPath": LOG_FILE,
            "StandardErrorPath": LOG_FILE,
        }

    def install(self, settings: dict[str, str] | None = None) -> None:
        os.makedirs(os.path.dirname(LAUNCH_AGENT_PLIST), exist_ok=True)
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        plist = self._generate_plist(settings)
        with open(LAUNCH_AGENT_PLIST, "wb") as f:
            plistlib.dump(plist, f)
        log.info("LaunchAgent installed -> %s", LAUNCH_AGENT_PLIST)

    def uninstall(self) -> None:
        self.stop()
        try:
            subprocess.run(
                ["launchctl", "unload", LAUNCH_AGENT_PLIST],
                capture_output=True, timeout=_TIMEOUT,
            )
        except Exception:
            pass
        try:
            os.remove(LAUNCH_AGENT_PLIST)
            log.info("Removed %s", LAUNCH_AGENT_PLIST)
        except OSError as e:
            log.warning("Could not remove plist: %s", e)

    def start(self) -> None:
        try:
            subprocess.run(
                ["launchctl", "load", LAUNCH_AGENT_PLIST],
                capture_output=True, timeout=_TIMEOUT,
            )
            subprocess.run(
                ["launchctl", "start", _LABEL],
                capture_output=True, timeout=_TIMEOUT,
            )
        except Exception as e:
            log.error("launchctl start failed: %s", e)

    def stop(self) -> None:
        try:
            subprocess.run(
                ["launchctl", "stop", _LABEL],
                capture_output=True, timeout=_TIMEOUT,
            )
        except Exception as e:
            log.error("launchctl stop failed: %s", e)
        mount = get_mount_point()
        if os.path.ismount(mount):
            try:
                subprocess.run(
                    ["umount", mount],
                    capture_output=True, timeout=_TIMEOUT,
                )
            except Exception:
                pass

    def restart(self) -> None:
        self.stop()
        time.sleep(1)
        self.start()

    def enable_and_start(self) -> None:
        try:
            subprocess.run(
                ["launchctl", "load", LAUNCH_AGENT_PLIST],
                capture_output=True, timeout=_TIMEOUT,
            )
            subprocess.run(
                ["launchctl", "start", _LABEL],
                capture_output=True, timeout=_TIMEOUT,
            )
        except Exception as e:
            log.error("launchctl enable+start failed: %s", e)

    def disable_and_stop(self) -> None:
        self.stop()
        try:
            subprocess.run(
                ["launchctl", "unload", LAUNCH_AGENT_PLIST],
                capture_output=True, timeout=_TIMEOUT,
            )
        except Exception:
            pass

    def is_running(self) -> bool:
        try:
            r = subprocess.run(
                ["launchctl", "list"],
                capture_output=True, text=True, timeout=10,
            )
            for line in r.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 3 and parts[2] == _LABEL:
                    pid = parts[0]
                    return pid != "-" and pid != "0"
        except Exception:
            pass
        return False

    def is_installed(self) -> bool:
        return os.path.isfile(LAUNCH_AGENT_PLIST)

    def get_uptime(self) -> Optional[str]:
        try:
            r = subprocess.run(
                ["launchctl", "list"],
                capture_output=True, text=True, timeout=10,
            )
            for line in r.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 3 and parts[2] == _LABEL:
                    pid = parts[0]
                    if pid != "-" and pid != "0":
                        ps = subprocess.run(
                            ["ps", "-p", pid, "-o", "etime="],
                            capture_output=True, text=True, timeout=5,
                        )
                        return ps.stdout.strip() or None
        except Exception:
            pass
        return None

    def get_mount_usage(self) -> tuple[Optional[str], Optional[str]]:
        try:
            mount = get_mount_point()
            if os.path.ismount(mount):
                st = os.statvfs(mount)
                total = st.f_blocks * st.f_frsize
                free = st.f_bfree * st.f_frsize
                used = total - free
                return _fmt_bytes(used), _fmt_bytes(total)
        except OSError:
            pass
        return None, None

    def get_logs(self, lines: int = 100) -> str:
        try:
            if os.path.isfile(LOG_FILE):
                r = subprocess.run(
                    ["tail", "-n", str(lines), LOG_FILE],
                    capture_output=True, text=True, timeout=5,
                )
                return r.stdout or "(no logs)"
        except Exception:
            pass
        return "(no log file found)"
