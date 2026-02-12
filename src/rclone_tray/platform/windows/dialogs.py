"""Windows dialog backend using tkinter."""

from __future__ import annotations

import os
import subprocess
from typing import Optional

from ...settings import DEFAULTS, load as load_settings
from ..base import DialogBackend

_VFS_CACHE_MODES = ["off", "minimal", "writes", "full"]


def _get_rclone_remotes() -> list[str]:
    try:
        r = subprocess.run(
            ["rclone", "listremotes"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            return [line.strip() for line in r.stdout.splitlines() if line.strip()]
    except Exception:
        pass
    return []


class TkDialogs(DialogBackend):
    """tkinter-based dialogs for Windows."""

    def show_settings(self) -> Optional[dict[str, str]]:
        import tkinter as tk
        from tkinter import ttk, filedialog

        settings = load_settings()
        result: dict[str, str] | None = None

        root = tk.Tk()
        root.title("Rclone Mount - Settings")
        root.resizable(False, False)

        frame = ttk.Frame(root, padding=16)
        frame.grid(sticky="nsew")

        row = 0

        ttk.Label(frame, text="Remote:").grid(row=row, column=0, sticky="e", padx=(0, 8))
        remotes = _get_rclone_remotes()
        remote_var = tk.StringVar(value=settings.get("remote", DEFAULTS["remote"]))
        if remotes:
            remote_cb = ttk.Combobox(frame, textvariable=remote_var, values=remotes, state="readonly", width=30)
        else:
            remote_cb = ttk.Combobox(frame, textvariable=remote_var, values=[], width=30)
        remote_cb.grid(row=row, column=1, columnspan=2, sticky="ew")
        row += 1

        ttk.Label(frame, text="Mount Folder:").grid(row=row, column=0, sticky="e", padx=(0, 8))
        mount_var = tk.StringVar(value=settings.get("mount_point", DEFAULTS["mount_point"]))
        ttk.Entry(frame, textvariable=mount_var, width=30).grid(row=row, column=1, sticky="ew")

        def _browse() -> None:
            d = filedialog.askdirectory(
                initialdir=os.path.expanduser(mount_var.get()),
                title="Select Mount Folder",
            )
            if d:
                mount_var.set(d)

        ttk.Button(frame, text="Browse", command=_browse).grid(row=row, column=2, padx=(4, 0))
        row += 1

        ttk.Label(frame, text="VFS Cache Mode:").grid(row=row, column=0, sticky="e", padx=(0, 8))
        cache_mode_var = tk.StringVar(value=settings.get("vfs_cache_mode", DEFAULTS["vfs_cache_mode"]))
        ttk.Combobox(frame, textvariable=cache_mode_var, values=_VFS_CACHE_MODES, state="readonly", width=30).grid(
            row=row, column=1, columnspan=2, sticky="ew"
        )
        row += 1

        ttk.Label(frame, text="VFS Cache Max Size:").grid(row=row, column=0, sticky="e", padx=(0, 8))
        cache_size_var = tk.StringVar(value=settings.get("vfs_cache_max_size", DEFAULTS["vfs_cache_max_size"]))
        ttk.Entry(frame, textvariable=cache_size_var, width=30).grid(row=row, column=1, columnspan=2, sticky="ew")
        row += 1

        ttk.Label(frame, text="VFS Write-Back:").grid(row=row, column=0, sticky="e", padx=(0, 8))
        write_back_var = tk.StringVar(value=settings.get("vfs_write_back", DEFAULTS["vfs_write_back"]))
        ttk.Entry(frame, textvariable=write_back_var, width=30).grid(row=row, column=1, columnspan=2, sticky="ew")
        row += 1

        ttk.Label(frame, text="Dir Cache Time:").grid(row=row, column=0, sticky="e", padx=(0, 8))
        dir_cache_var = tk.StringVar(value=settings.get("dir_cache_time", DEFAULTS["dir_cache_time"]))
        ttk.Entry(frame, textvariable=dir_cache_var, width=30).grid(row=row, column=1, columnspan=2, sticky="ew")
        row += 1

        ttk.Label(frame, text="Stats Interval:").grid(row=row, column=0, sticky="e", padx=(0, 8))
        stats_var = tk.StringVar(value=settings.get("stats_interval", DEFAULTS["stats_interval"]))
        ttk.Entry(frame, textvariable=stats_var, width=30).grid(row=row, column=1, columnspan=2, sticky="ew")
        row += 1

        error_var = tk.StringVar()
        ttk.Label(frame, textvariable=error_var, foreground="red").grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )
        row += 1

        def _save() -> None:
            nonlocal result
            remote_val = remote_var.get().strip()
            mount_val = mount_var.get().strip()
            errors = []
            if not remote_val:
                errors.append("No remote selected")
            if not mount_val:
                errors.append("Mount Folder cannot be empty")
            if errors:
                error_var.set(" | ".join(errors))
                return

            result = {
                "remote": remote_val,
                "mount_point": mount_val,
                "vfs_cache_mode": cache_mode_var.get() or DEFAULTS["vfs_cache_mode"],
                "vfs_cache_max_size": cache_size_var.get().strip() or DEFAULTS["vfs_cache_max_size"],
                "vfs_write_back": write_back_var.get().strip() or DEFAULTS["vfs_write_back"],
                "dir_cache_time": dir_cache_var.get().strip() or DEFAULTS["dir_cache_time"],
                "stats_interval": stats_var.get().strip() or DEFAULTS["stats_interval"],
            }
            root.destroy()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=(12, 0))
        ttk.Button(btn_frame, text="Cancel", command=root.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="Save", command=_save).pack(side="left")

        root.mainloop()
        return result

    def show_logs(self, text: str) -> None:
        import tkinter as tk
        from tkinter import scrolledtext

        root = tk.Tk()
        root.title("Rclone Mount - Logs")
        root.geometry("800x500")

        st = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Courier New", 10))
        st.pack(fill="both", expand=True)
        st.insert("1.0", text)
        st.config(state="disabled")
        st.see("end")

        tk.Button(root, text="Close", command=root.destroy).pack(side="right", padx=8, pady=8)

        root.mainloop()

    def open_folder(self, path: str) -> None:
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except Exception:
            try:
                subprocess.Popen(["explorer", path])
            except Exception:
                pass

    def open_terminal_with(self, cmd: list[str]) -> bool:
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "cmd", "/k"] + cmd,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False
