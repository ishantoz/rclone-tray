"""fcntl-based single-instance lock for macOS (same as Linux)."""

from ..linux.lock import FcntlLock  # noqa: F401 — re-export
