"""Linux autostart backend using .desktop files in ~/.config/autostart/."""

from __future__ import annotations

import logging
import os
import shutil

from ...config import BIN_PATH, DATA_DIR, DESKTOP_DIR, DESKTOP_FILE
from ..base import AutostartBackend

log = logging.getLogger(__name__)


class DesktopAutostart(AutostartBackend):
    """Manage autostart via XDG .desktop file."""

    def is_enabled(self) -> bool:
        return os.path.isfile(DESKTOP_FILE)

    def enable(self) -> None:
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
            f.write(
                f"""\
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
"""
            )
        log.info("Autostart enabled -> %s", DESKTOP_FILE)

    def disable(self) -> None:
        try:
            os.remove(DESKTOP_FILE)
            log.info("Autostart disabled (removed %s)", DESKTOP_FILE)
        except OSError:
            pass
