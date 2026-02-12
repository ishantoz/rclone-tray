"""Windows service backend — manages rclone as a direct subprocess."""

from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import subprocess
import time
from typing import Optional

from ...config import CONFIG_DIR, LOG_FILE
from ...settings import get_mount_point, load as load_settings
from ..base import ServiceBackend

log = logging.getLogger(__name__)

_PID_FILE = os.path.join(CONFIG_DIR, "rclone.pid")


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


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is alive (Windows-compatible)."""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
    except Exception:
        pass
    return False


def _read_pid() -> Optional[int]:
    try:
        with open(_PID_FILE) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _write_pid(pid: int) -> None:
    os.makedirs(os.path.dirname(_PID_FILE), exist_ok=True)
    with open(_PID_FILE, "w") as f:
        f.write(str(pid))


def _clear_pid() -> None:
    try:
        os.remove(_PID_FILE)
    except OSError:
        pass


class WindowsService(ServiceBackend):
    """Manage rclone as a direct subprocess on Windows."""

    def _build_cmd(self, settings: dict[str, str] | None = None) -> list[str]:
        if settings is None:
            settings = load_settings()
        remote = settings.get("remote", "gdrive:")
        mount = os.path.expanduser(settings.get("mount_point", "~/GoogleDrive"))
        cache_mode = settings.get("vfs_cache_mode", "full")
        cache_size = settings.get("vfs_cache_max_size", "10G")
        write_back = settings.get("vfs_write_back", "5s")
        dir_cache = settings.get("dir_cache_time", "2m")
        stats = settings.get("stats_interval", "30s")

        rclone_bin = shutil.which("rclone") or "rclone"

        return [
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

    def install(self, settings: dict[str, str] | None = None) -> None:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        cmd = self._build_cmd(settings)
        cmd_file = os.path.join(CONFIG_DIR, "rclone_cmd.json")
        with open(cmd_file, "w") as f:
            json.dump(cmd, f)
        log.info("Service config saved -> %s", cmd_file)

    def uninstall(self) -> None:
        self.stop()
        cmd_file = os.path.join(CONFIG_DIR, "rclone_cmd.json")
        try:
            os.remove(cmd_file)
        except OSError:
            pass
        _clear_pid()

    def start(self) -> None:
        if self.is_running():
            return
        cmd_file = os.path.join(CONFIG_DIR, "rclone_cmd.json")
        try:
            with open(cmd_file) as f:
                cmd = json.load(f)
        except (OSError, json.JSONDecodeError):
            cmd = self._build_cmd()

        try:
            # CREATE_NO_WINDOW on Windows
            CREATE_NO_WINDOW = 0x08000000
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
            )
            _write_pid(proc.pid)
            log.info("rclone started (PID %d)", proc.pid)
        except Exception as e:
            log.error("Failed to start rclone: %s", e)

    def stop(self) -> None:
        pid = _read_pid()
        if pid and _is_pid_alive(pid):
            try:
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True, timeout=10,
                )
                log.info("Killed rclone (PID %d)", pid)
            except Exception as e:
                log.error("Failed to kill PID %d: %s", pid, e)
        _clear_pid()

    def restart(self) -> None:
        self.stop()
        time.sleep(1)
        self.start()

    def enable_and_start(self) -> None:
        self.start()

    def disable_and_stop(self) -> None:
        self.stop()

    def is_running(self) -> bool:
        pid = _read_pid()
        return pid is not None and _is_pid_alive(pid)

    def is_installed(self) -> bool:
        cmd_file = os.path.join(CONFIG_DIR, "rclone_cmd.json")
        return os.path.isfile(cmd_file)

    def get_uptime(self) -> Optional[str]:
        pid = _read_pid()
        if not pid:
            return None
        try:
            r = subprocess.run(
                [
                    "powershell", "-Command",
                    f"(Get-Process -Id {pid}).StartTime",
                ],
                capture_output=True, text=True, timeout=5,
            )
            if r.stdout.strip():
                from datetime import datetime
                start_str = r.stdout.strip()
                start_time = datetime.strptime(start_str, "%m/%d/%Y %I:%M:%S %p")
                delta = datetime.now() - start_time
                return _fmt_duration(int(delta.total_seconds()))
        except Exception:
            pass
        return None

    def get_mount_usage(self) -> tuple[Optional[str], Optional[str]]:
        try:
            mount = get_mount_point()
            if os.path.isdir(mount):
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(  # type: ignore[attr-defined]
                    mount, None, ctypes.pointer(total_bytes), ctypes.pointer(free_bytes)
                )
                total = total_bytes.value
                free = free_bytes.value
                used = total - free
                if total > 0:
                    return _fmt_bytes(used), _fmt_bytes(total)
        except Exception:
            pass
        return None, None

    def get_logs(self, lines: int = 100) -> str:
        try:
            if os.path.isfile(LOG_FILE):
                with open(LOG_FILE) as f:
                    all_lines = f.readlines()
                return "".join(all_lines[-lines:]) or "(no logs)"
        except Exception:
            pass
        return "(no log file found)"
