"""msvcrt-based single-instance lock for Windows."""

from __future__ import annotations

import os
import sys
from io import TextIOWrapper

from ..base import InstanceLock


class MsvcrtLock(InstanceLock):
    """File-based lock using msvcrt.locking on Windows."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._fd: TextIOWrapper | None = None

    def acquire(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._fd = open(self._path, "w")
        try:
            import msvcrt  # type: ignore[import-not-found]
            msvcrt.locking(self._fd.fileno(), msvcrt.LK_NBLCK, 1)
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
                import msvcrt  # type: ignore[import-not-found]
                self._fd.seek(0)
                msvcrt.locking(self._fd.fileno(), msvcrt.LK_UNLCK, 1)
                self._fd.close()
                os.remove(self._path)
            except OSError:
                pass
            self._fd = None
