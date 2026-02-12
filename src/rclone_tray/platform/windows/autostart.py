"""Windows autostart backend using the HKCU Registry Run key."""

from __future__ import annotations

import logging
import os
import sys

from ..base import AutostartBackend

log = logging.getLogger(__name__)

_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "RcloneTray"


class RegistryAutostart(AutostartBackend):
    """Manage autostart via the Windows Registry Run key."""

    def is_enabled(self) -> bool:
        try:
            import winreg  # type: ignore[import-not-found]
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, _VALUE_NAME)
                return True
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False

    def enable(self) -> None:
        try:
            import winreg  # type: ignore[import-not-found]
            exe = sys.executable
            if getattr(sys, "frozen", False):
                exe = sys.executable
            else:
                exe = f'"{sys.executable}" -m rclone_tray'

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_WRITE
            )
            winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, exe)
            winreg.CloseKey(key)
            log.info("Autostart enabled via Registry")
        except Exception as e:
            log.error("Failed to enable autostart: %s", e)

    def disable(self) -> None:
        try:
            import winreg  # type: ignore[import-not-found]
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_WRITE
            )
            try:
                winreg.DeleteValue(key, _VALUE_NAME)
                log.info("Autostart disabled via Registry")
            except FileNotFoundError:
                pass
            finally:
                winreg.CloseKey(key)
        except Exception as e:
            log.error("Failed to disable autostart: %s", e)
