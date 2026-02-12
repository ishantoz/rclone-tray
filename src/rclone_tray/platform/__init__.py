"""Platform detection and backend factory."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import AutostartBackend, DialogBackend, InstanceLock, ServiceBackend


def detect_platform() -> str:
    """Return 'linux', 'macos', or 'windows'."""
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    raise RuntimeError(f"Unsupported platform: {sys.platform}")


PLATFORM = detect_platform()


def get_service_backend() -> ServiceBackend:
    if PLATFORM == "linux":
        from .linux.service import LinuxService
        return LinuxService()
    if PLATFORM == "macos":
        from .macos.service import MacService
        return MacService()
    if PLATFORM == "windows":
        from .windows.service import WindowsService
        return WindowsService()
    raise RuntimeError(f"No service backend for {PLATFORM}")


def get_dialog_backend() -> DialogBackend:
    if PLATFORM == "linux":
        from .linux.dialogs import GtkDialogs
        return GtkDialogs()
    if PLATFORM == "macos":
        from .macos.dialogs import TkDialogs
        return TkDialogs()
    if PLATFORM == "windows":
        from .windows.dialogs import TkDialogs
        return TkDialogs()
    raise RuntimeError(f"No dialog backend for {PLATFORM}")


def get_autostart_backend() -> AutostartBackend:
    if PLATFORM == "linux":
        from .linux.autostart import DesktopAutostart
        return DesktopAutostart()
    if PLATFORM == "macos":
        from .macos.autostart import LaunchAgentAutostart
        return LaunchAgentAutostart()
    if PLATFORM == "windows":
        from .windows.autostart import RegistryAutostart
        return RegistryAutostart()
    raise RuntimeError(f"No autostart backend for {PLATFORM}")


def get_instance_lock(path: str) -> InstanceLock:
    if PLATFORM == "windows":
        from .windows.lock import MsvcrtLock
        return MsvcrtLock(path)
    else:
        from .linux.lock import FcntlLock
        return FcntlLock(path)
