"""Abstract interfaces for platform-specific backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class ServiceBackend(ABC):
    """Manage the rclone mount process/service."""

    @abstractmethod
    def install(self, settings: dict[str, str] | None = None) -> None: ...

    @abstractmethod
    def uninstall(self) -> None: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def restart(self) -> None: ...

    @abstractmethod
    def enable_and_start(self) -> None: ...

    @abstractmethod
    def disable_and_stop(self) -> None: ...

    @abstractmethod
    def is_running(self) -> bool: ...

    @abstractmethod
    def is_installed(self) -> bool: ...

    @abstractmethod
    def get_uptime(self) -> Optional[str]: ...

    @abstractmethod
    def get_mount_usage(self) -> tuple[Optional[str], Optional[str]]: ...

    @abstractmethod
    def get_logs(self, lines: int = 100) -> str: ...


class DialogBackend(ABC):
    """Show native dialogs for settings and logs."""

    @abstractmethod
    def show_settings(self) -> Optional[dict[str, str]]: ...

    @abstractmethod
    def show_logs(self, text: str) -> None: ...

    @abstractmethod
    def open_folder(self, path: str) -> None: ...

    @abstractmethod
    def open_terminal_with(self, cmd: list[str]) -> bool: ...


class AutostartBackend(ABC):
    """Manage login-time autostart."""

    @abstractmethod
    def is_enabled(self) -> bool: ...

    @abstractmethod
    def enable(self) -> None: ...

    @abstractmethod
    def disable(self) -> None: ...


class InstanceLock(ABC):
    """Single-instance guard."""

    @abstractmethod
    def acquire(self) -> None: ...

    @abstractmethod
    def release(self) -> None: ...
