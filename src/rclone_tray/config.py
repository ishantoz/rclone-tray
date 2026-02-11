"""
Centralised configuration for rclone-tray.

Supports running from source and as a PyInstaller one-file binary.
"""

from __future__ import annotations

import os
import sys

APP_ID = "rclone-tray"
APP_NAME = "Rclone Mount Tray"
SERVICE_NAME = "rclone-mount.service"
BIN_NAME = "rclone-tray"
BIN_DIR = os.path.expanduser("~/.local/bin")
BIN_PATH = os.path.join(BIN_DIR, BIN_NAME)

if getattr(sys, "frozen", False):
    DATA_DIR = os.path.join(sys._MEIPASS, "data")  # type: ignore[attr-defined]
else:
    _PKG_DIR = os.path.dirname(os.path.abspath(__file__))
    _PROJECT_ROOT = os.path.normpath(os.path.join(_PKG_DIR, os.pardir, os.pardir))
    DATA_DIR = os.path.join(_PROJECT_ROOT, "data")

SERVICE_DST = os.path.expanduser(f"~/.config/systemd/user/{SERVICE_NAME}")

ICON_DIR = os.path.join(DATA_DIR, "icons")
ICON_RUNNING = os.path.join(ICON_DIR, "rclone-active.png")
ICON_STOPPED = os.path.join(ICON_DIR, "rclone-stop.png")

LOCK_FILE = os.path.expanduser("~/.cache/rclone-tray.lock")
POLL_INTERVAL_SEC = 5

DESKTOP_DIR = os.path.expanduser("~/.config/autostart")
DESKTOP_FILE = os.path.join(DESKTOP_DIR, f"{APP_ID}.desktop")
DESKTOP_SRC = os.path.join(DATA_DIR, f"{APP_ID}.desktop")
