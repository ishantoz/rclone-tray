"""Systemd user-service manager for the rclone mount."""

from __future__ import annotations

import concurrent.futures
import logging
import os
import shutil
import subprocess
from typing import Optional

from .config import SERVICE_DST, SERVICE_NAME
from .settings import get_mount_point, load as load_settings
from .utils import fmt_bytes, fmt_duration

log = logging.getLogger(__name__)

_TIMEOUT = 30
_POLL_TIMEOUT = 5
_statvfs_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)


def shutdown_pool() -> None:
    """Shut down the module-level thread pool (call on app exit)."""
    _statvfs_pool.shutdown(wait=False)


class SystemdService:
    """Manage a single systemd --user service."""

    @staticmethod
    def _run(*args: str, timeout: int = _TIMEOUT) -> Optional[subprocess.CompletedProcess]:
        try:
            r = subprocess.run(
                ["systemctl", "--user", *args],
                capture_output=True, text=True, timeout=timeout,
            )
            if r.returncode != 0 and r.stderr.strip():
                log.warning("systemctl %s: %s", " ".join(args), r.stderr.strip())
            return r
        except subprocess.TimeoutExpired:
            log.error("systemctl %s timed out", " ".join(args))
        except Exception as e:
            log.error("systemctl %s failed: %s", " ".join(args), e)
        return None

    def _ctl(self, *actions: str) -> None:
        for a in actions:
            self._run(a, SERVICE_NAME)

    @staticmethod
    def _find_bin(names: list[str], fallback: str) -> str:
        """Return the absolute path of the first binary found, or fallback."""
        for name in names:
            path = shutil.which(name)
            if path:
                return path
        return fallback

    @staticmethod
    def generate_service(settings: dict[str, str] | None = None) -> str:
        """Render the systemd unit file content from settings."""
        if settings is None:
            settings = load_settings()
        remote = settings.get("remote", "gdrive:")
        mount = settings.get("mount_point", "~/GoogleDrive")
        cache_mode = settings.get("vfs_cache_mode", "full")
        cache_size = settings.get("vfs_cache_max_size", "10G")
        write_back = settings.get("vfs_write_back", "5s")
        dir_cache = settings.get("dir_cache_time", "2m")
        stats = settings.get("stats_interval", "30s")

        rclone_bin = SystemdService._find_bin(["rclone"], "/usr/bin/rclone")
        fuse_bin = SystemdService._find_bin(
            ["fusermount3", "fusermount"], "/usr/bin/fusermount"
        )

        if mount.startswith("~"):
            mount_escaped = "%h" + mount[1:]
        else:
            mount_escaped = mount

        return (
            "[Unit]\n"
            "Description=Rclone Cloud Storage Mount\n"
            "After=network-online.target\n"
            "Wants=network-online.target\n"
            "\n"
            "[Service]\n"
            "Type=simple\n"
            f"ExecStart={rclone_bin} mount {remote} {mount_escaped} \\\n"
            f"    --vfs-cache-mode {cache_mode} \\\n"
            f"    --vfs-cache-max-size {cache_size} \\\n"
            f"    --vfs-write-back {write_back} \\\n"
            f"    --dir-cache-time {dir_cache} \\\n"
            "    -v \\\n"
            f"    --stats {stats} \\\n"
            "    --stats-one-line \\\n"
            "    --log-systemd\n"
            f"ExecStop={fuse_bin} -uz {mount_escaped}\n"
            "Restart=always\n"
            "RestartSec=10\n"
            "\n"
            "[Install]\n"
            "WantedBy=default.target\n"
        )

    def install(self, settings: dict[str, str] | None = None) -> None:
        """Generate and install the .service file, then reload systemd."""
        os.makedirs(os.path.dirname(SERVICE_DST), exist_ok=True)
        content = self.generate_service(settings)
        with open(SERVICE_DST, "w") as f:
            f.write(content)
        self._run("daemon-reload")
        log.info("Service installed -> %s", SERVICE_DST)

    def uninstall(self) -> None:
        """Stop, disable, remove the service file, and reload."""
        self._ctl("stop", "disable")
        try:
            os.remove(SERVICE_DST)
            log.info("Removed %s", SERVICE_DST)
        except OSError as e:
            log.warning("Could not remove service file: %s", e)
        self._run("daemon-reload")
        self._run("reset-failed")

    def enable_and_start(self) -> None:
        self._ctl("enable", "start")

    def start(self) -> None:
        self._ctl("enable", "start")

    def stop(self) -> None:
        self._ctl("stop")

    def restart(self) -> None:
        self._ctl("restart")

    def disable_and_stop(self) -> None:
        self._ctl("stop", "disable")

    def is_running(self) -> bool:
        r = self._run("is-active", SERVICE_NAME, timeout=_POLL_TIMEOUT)
        return r is not None and r.stdout.strip() == "active"

    def get_uptime(self) -> Optional[str]:
        """Return a human-readable uptime string, or None."""
        try:
            r = subprocess.run(
                ["systemctl", "--user", "show", SERVICE_NAME,
                 "--property=ActiveEnterTimestampMonotonic"],
                capture_output=True, text=True, timeout=_POLL_TIMEOUT,
            )
            val = r.stdout.strip().split("=", 1)[-1]
            if val and val != "0":
                started_us = int(val)
                with open("/proc/uptime") as f:
                    boot_sec = float(f.read().split()[0])
                now_us = int(boot_sec * 1_000_000)
                delta_sec = max(0, (now_us - started_us) // 1_000_000)
                return fmt_duration(delta_sec)
        except Exception:
            pass
        return None

    @staticmethod
    def get_mount_usage() -> tuple[Optional[str], Optional[str]]:
        """Return (used, total) as formatted strings, or (None, None).

        Uses a thread with a timeout so a hung FUSE mount won't block.
        """
        def _statvfs() -> tuple[Optional[str], Optional[str]]:
            mount = get_mount_point()
            if os.path.ismount(mount):
                st = os.statvfs(mount)
                total = st.f_blocks * st.f_frsize
                free = st.f_bfree * st.f_frsize
                used = total - free
                return fmt_bytes(used), fmt_bytes(total)
            return None, None

        try:
            future = _statvfs_pool.submit(_statvfs)
            return future.result(timeout=3)
        except (concurrent.futures.TimeoutError, OSError, Exception):
            return None, None

    @staticmethod
    def get_recent_logs(lines: int = 100) -> str:
        """Return the last N lines from the service journal."""
        try:
            r = subprocess.run(
                ["journalctl", "--user", "-u", SERVICE_NAME,
                 "-n", str(lines), "--no-pager"],
                capture_output=True, text=True, timeout=10,
            )
            return r.stdout or "(no logs)"
        except Exception:
            return "(failed to read logs)"
