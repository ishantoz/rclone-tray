"""
Centralised configuration for rclone-tray.

Platform-aware paths for Linux, macOS, and Windows.
Supports running from source and as a PyInstaller one-file binary.
"""

from __future__ import annotations

import os
import sys

APP_ID = "rclone-tray"
APP_NAME = "Rclone Mount Tray"
SERVICE_NAME = "rclone-mount.service"
BIN_NAME = "rclone-tray"
POLL_INTERVAL_SEC = 5

# --- Platform detection ---

if sys.platform.startswith("linux"):
    PLATFORM = "linux"
elif sys.platform == "darwin":
    PLATFORM = "macos"
elif sys.platform == "win32":
    PLATFORM = "windows"
else:
    PLATFORM = "linux"

# --- Data directory (icons, templates) ---

if getattr(sys, "frozen", False):
    DATA_DIR = os.path.join(sys._MEIPASS, "data")  # type: ignore[attr-defined]
else:
    _PKG_DIR = os.path.dirname(os.path.abspath(__file__))
    _PROJECT_ROOT = os.path.normpath(os.path.join(_PKG_DIR, os.pardir, os.pardir))
    DATA_DIR = os.path.join(_PROJECT_ROOT, "data")

ICON_DIR = os.path.join(DATA_DIR, "icons")
ICON_RUNNING = os.path.join(ICON_DIR, "rclone-active.png")
ICON_STOPPED = os.path.join(ICON_DIR, "rclone-stop.png")

# --- Platform-specific paths ---

if PLATFORM == "linux":
    CONFIG_DIR = os.path.expanduser("~/.config/rclone-tray")
    CACHE_DIR = os.path.expanduser("~/.cache")
    SERVICE_DST = os.path.expanduser(f"~/.config/systemd/user/{SERVICE_NAME}")
    LOCK_FILE = os.path.join(CACHE_DIR, "rclone-tray.lock")
    BIN_DIR = os.path.expanduser("~/.local/bin")
    BIN_PATH = os.path.join(BIN_DIR, BIN_NAME)
    DESKTOP_DIR = os.path.expanduser("~/.config/autostart")
    DESKTOP_FILE = os.path.join(DESKTOP_DIR, f"{APP_ID}.desktop")
    DESKTOP_SRC = os.path.join(DATA_DIR, f"{APP_ID}.desktop")
    LOG_FILE = ""  # Linux uses journalctl

elif PLATFORM == "macos":
    CONFIG_DIR = os.path.expanduser("~/Library/Application Support/rclone-tray")
    CACHE_DIR = os.path.expanduser("~/Library/Caches/rclone-tray")
    LOCK_FILE = os.path.join(CACHE_DIR, "rclone-tray.lock")
    LOG_FILE = os.path.join(CACHE_DIR, "rclone.log")
    BIN_DIR = "/usr/local/bin"
    BIN_PATH = os.path.join(BIN_DIR, BIN_NAME)
    LAUNCH_AGENT_DIR = os.path.expanduser("~/Library/LaunchAgents")
    LAUNCH_AGENT_PLIST = os.path.join(LAUNCH_AGENT_DIR, "com.rclone-tray.mount.plist")
    AUTOSTART_PLIST = os.path.join(LAUNCH_AGENT_DIR, "com.rclone-tray.plist")
    SERVICE_DST = LAUNCH_AGENT_PLIST
    DESKTOP_DIR = ""
    DESKTOP_FILE = ""
    DESKTOP_SRC = ""

elif PLATFORM == "windows":
    _APPDATA = os.environ.get("APPDATA", os.path.expanduser("~/AppData/Roaming"))
    CONFIG_DIR = os.path.join(_APPDATA, "rclone-tray")
    CACHE_DIR = CONFIG_DIR
    LOCK_FILE = os.path.join(CONFIG_DIR, "rclone-tray.lock")
    LOG_FILE = os.path.join(CONFIG_DIR, "rclone.log")
    BIN_DIR = ""
    BIN_PATH = ""
    SERVICE_DST = ""
    DESKTOP_DIR = ""
    DESKTOP_FILE = ""
    DESKTOP_SRC = ""

else:
    CONFIG_DIR = os.path.expanduser("~/.config/rclone-tray")
    CACHE_DIR = os.path.expanduser("~/.cache")
    LOCK_FILE = os.path.join(CACHE_DIR, "rclone-tray.lock")
    LOG_FILE = ""
    BIN_DIR = os.path.expanduser("~/.local/bin")
    BIN_PATH = os.path.join(BIN_DIR, BIN_NAME)
    SERVICE_DST = ""
    DESKTOP_DIR = ""
    DESKTOP_FILE = ""
    DESKTOP_SRC = ""
