"""macOS autostart backend using a LaunchAgent plist for the tray app itself."""

from __future__ import annotations

import logging
import os
import plistlib
import shutil
import subprocess
import sys

from ...config import AUTOSTART_PLIST, BIN_PATH
from ..base import AutostartBackend

log = logging.getLogger(__name__)

_LABEL = "com.rclone-tray"


class LaunchAgentAutostart(AutostartBackend):
    """Manage login-time autostart via ~/Library/LaunchAgents/."""

    def is_enabled(self) -> bool:
        return os.path.isfile(AUTOSTART_PLIST)

    def enable(self) -> None:
        os.makedirs(os.path.dirname(AUTOSTART_PLIST), exist_ok=True)

        if os.path.isfile(BIN_PATH):
            exec_args = [BIN_PATH]
        else:
            exec_args = [sys.executable, "-m", "rclone_tray"]

        plist = {
            "Label": _LABEL,
            "ProgramArguments": exec_args,
            "RunAtLoad": True,
            "KeepAlive": False,
        }

        with open(AUTOSTART_PLIST, "wb") as f:
            plistlib.dump(plist, f)

        subprocess.run(
            ["launchctl", "load", AUTOSTART_PLIST],
            capture_output=True,
        )
        log.info("Autostart enabled -> %s", AUTOSTART_PLIST)

    def disable(self) -> None:
        try:
            subprocess.run(
                ["launchctl", "unload", AUTOSTART_PLIST],
                capture_output=True,
            )
        except Exception:
            pass
        try:
            os.remove(AUTOSTART_PLIST)
            log.info("Autostart disabled (removed %s)", AUTOSTART_PLIST)
        except OSError:
            pass
