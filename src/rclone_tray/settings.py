"""Persistent user settings backed by a JSON file."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from .config import CONFIG_DIR

log = logging.getLogger(__name__)

SETTINGS_DIR = CONFIG_DIR
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")

DEFAULTS: dict[str, str] = {
    "remote": "gdrive:",
    "mount_point": "~/GoogleDrive",
    "vfs_cache_mode": "full",
    "vfs_cache_max_size": "10G",
    "vfs_write_back": "5s",
    "dir_cache_time": "2m",
    "stats_interval": "30s",
}


def load() -> dict[str, str]:
    """Load settings from disk, falling back to DEFAULTS for missing keys."""
    data: dict[str, Any] = {}
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Failed to read settings, using defaults: %s", e)
    merged = {**DEFAULTS, **data}
    return merged


def save(data: dict[str, str]) -> None:
    """Write settings to disk."""
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    log.info("Settings saved -> %s", SETTINGS_FILE)


def exists() -> bool:
    """Return True if a settings file has been saved before."""
    return os.path.isfile(SETTINGS_FILE)


def get_mount_point() -> str:
    """Return the expanded, absolute mount-point path."""
    val = load()["mount_point"].strip()
    if not val:
        val = DEFAULTS["mount_point"]
    return os.path.expanduser(val)
