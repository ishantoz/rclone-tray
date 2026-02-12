"""fcntl-based single-instance lock (Linux and macOS)."""

from __future__ import annotations

import fcntl
import os
import sys
from io import TextIOWrapper

from ..base import InstanceLock


class FcntlLock(InstanceLock):
    """File-based lock using fcntl.flock."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._fd: TextIOWrapper | None = None

    def acquire(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._fd = open(self._path, "w")
        try:
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._fd.write(str(os.getpid()))
            self._fd.flush()
        except OSError:
            print(
                f"{sys.argv[0]}: another instance is already running.",
                file=sys.stderr,
            )
            sys.exit(1)

    def release(self) -> None:
        if self._fd:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                self._fd.close()
                os.remove(self._path)
            except OSError:
                pass
            self._fd = None
