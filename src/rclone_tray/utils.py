"""Utility helpers: formatting, terminal detection, autostart, single-instance lock."""

from __future__ import annotations

import fcntl
import logging
import os
import shutil
import sys

from .config import BIN_PATH, DATA_DIR, DESKTOP_DIR, DESKTOP_FILE

log = logging.getLogger(__name__)

_TERMINALS = (
    "kitty", "alacritty", "foot", "wezterm", "ghostty",
    "gnome-terminal", "konsole", "xfce4-terminal", "xterm",
)


def fmt_duration(seconds: int) -> str:
    """Convert seconds into a compact string like '2h 15m'."""
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


def fmt_bytes(n: float) -> str:
    """Format byte count like '4.2 GB'."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def find_terminal() -> str | None:
    """Return the binary name of the first available terminal emulator."""
    env = os.environ.get("TERMINAL")
    if env and shutil.which(env):
        return env
    for t in _TERMINALS:
        if shutil.which(t):
            return t
    return None


def is_autostart_enabled() -> bool:
    return os.path.isfile(DESKTOP_FILE)


def enable_autostart() -> None:
    """Install the autostart desktop entry with the correct Exec path."""
    os.makedirs(DESKTOP_DIR, exist_ok=True)

    if os.path.isfile(BIN_PATH):
        exec_cmd = BIN_PATH
    else:
        project_root = os.path.normpath(os.path.join(DATA_DIR, os.pardir))
        uv_bin = shutil.which("uv")
        if uv_bin:
            exec_cmd = f"{uv_bin} run --project {project_root} rclone-tray"
        else:
            exec_cmd = f"{project_root}/.venv/bin/python -m rclone_tray"

    with open(DESKTOP_FILE, "w") as f:
        f.write(f"""\
[Desktop Entry]
Type=Application
Name=Rclone Mount Tray
Comment=System tray controller for rclone cloud storage mounts
Exec={exec_cmd}
Icon=drive-harddisk
Terminal=false
Categories=Utility;System;
StartupNotify=false
X-GNOME-Autostart-enabled=true
""")
    log.info("Autostart enabled -> %s", DESKTOP_FILE)


def disable_autostart() -> None:
    try:
        os.remove(DESKTOP_FILE)
        log.info("Autostart disabled (removed %s)", DESKTOP_FILE)
    except OSError:
        pass


class InstanceLock:
    """flock-based single-instance guard."""

    def __init__(self, path: str) -> None:
        self._path = path
        from io import TextIOWrapper
        self._fd: TextIOWrapper | None = None

    def acquire(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._fd = open(self._path, "w")
        try:
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._fd.write(str(os.getpid()))
            self._fd.flush()
        except OSError:
            print(f"{sys.argv[0]}: another instance is already running.",
                  file=sys.stderr)
            sys.exit(1)

    def release(self) -> None:
        fd, self._fd = self._fd, None
        if fd is None:
            return
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            fd.close()
        except OSError:
            pass
        try:
            os.remove(self._path)
        except OSError:
            pass
