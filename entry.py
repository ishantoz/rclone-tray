"""PyInstaller entry point (uses absolute imports)."""

import logging
import os
import sys

if sys.platform.startswith("linux"):
    os.environ["GTK_MODULES"] = ""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [rclone-tray] %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)

from rclone_tray.app import RcloneTray

app = RcloneTray()
app.run()
