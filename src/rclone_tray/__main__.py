"""Entry point for  python -m rclone_tray  and the console script."""

from __future__ import annotations

import logging
import os
import sys

from .config import PLATFORM

if PLATFORM == "linux":
    os.environ["GTK_MODULES"] = ""

from .app import RcloneTray


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [rclone-tray] %(levelname)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    app = RcloneTray()
    app.run()


if __name__ == "__main__":
    sys.exit(main())
