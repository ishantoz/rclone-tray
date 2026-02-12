"""Linux dialog backend using GTK 3."""

from __future__ import annotations

import os
import subprocess
import shutil
from typing import Optional

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Gtk  # type: ignore[attr-defined]

from ...config import ICON_RUNNING, SERVICE_NAME
from ...settings import DEFAULTS, get_mount_point, load as load_settings
from ..base import DialogBackend

_VFS_CACHE_MODES = ["off", "minimal", "writes", "full"]

_APP_ICON: GdkPixbuf.Pixbuf | None = None

_TERMINALS = (
    "kitty", "alacritty", "foot", "wezterm", "ghostty",
    "gnome-terminal", "konsole", "xfce4-terminal", "xterm",
)


def _get_app_icon() -> GdkPixbuf.Pixbuf | None:
    global _APP_ICON
    if _APP_ICON is None:
        try:
            _APP_ICON = GdkPixbuf.Pixbuf.new_from_file(ICON_RUNNING)
        except Exception:
            pass
    return _APP_ICON


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


def _find_terminal() -> str | None:
    env = os.environ.get("TERMINAL")
    if env and shutil.which(env):
        return env
    for t in _TERMINALS:
        if shutil.which(t):
            return t
    return None


class GtkDialogs(DialogBackend):
    """GTK-based dialogs for Linux."""

    def show_settings(self) -> Optional[dict[str, str]]:
        icon = _get_app_icon()
        if icon:
            Gtk.Window.set_default_icon(icon)

        settings = load_settings()

        dialog = Gtk.Dialog(title="Rclone Mount - Settings")
        if icon:
            dialog.set_icon(icon)
        dialog.set_default_size(480, 0)
        dialog.set_resizable(False)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Save", Gtk.ResponseType.OK)

        content = dialog.get_content_area()
        content.set_spacing(8)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_margin_top(12)
        content.set_margin_bottom(12)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)
        content.pack_start(grid, True, True, 0)

        row = 0

        grid.attach(_grid_label("Remote"), 0, row, 1, 1)
        remotes = _get_rclone_remotes()
        current_remote = settings.get("remote", DEFAULTS["remote"])
        remote_combo = Gtk.ComboBoxText()
        active_idx = -1
        for i, name in enumerate(remotes):
            remote_combo.append_text(name)
            if name == current_remote:
                active_idx = i
        if active_idx >= 0:
            remote_combo.set_active(active_idx)
        elif remotes:
            remote_combo.set_active(0)
        remote_combo.set_hexpand(True)

        if not remotes:
            no_remote_label = Gtk.Label()
            no_remote_label.set_markup(
                '<span foreground="orange">No remotes found. Run "rclone config" first.</span>'
            )
            no_remote_label.set_xalign(0.0)
            grid.attach(no_remote_label, 1, row, 2, 1)
        else:
            grid.attach(remote_combo, 1, row, 2, 1)
        row += 1

        grid.attach(_grid_label("Mount Folder"), 0, row, 1, 1)
        mount_entry = Gtk.Entry()
        mount_entry.set_text(settings.get("mount_point", DEFAULTS["mount_point"]))
        mount_entry.set_hexpand(True)
        grid.attach(mount_entry, 1, row, 1, 1)

        browse_btn = Gtk.Button(label="Browse")

        def _on_browse(_btn: Gtk.Button) -> None:
            chooser = Gtk.FileChooserDialog(
                title="Select Mount Folder",
                parent=dialog,
                action=Gtk.FileChooserAction.SELECT_FOLDER,
            )
            ic = _get_app_icon()
            if ic:
                chooser.set_icon(ic)
            chooser.add_button("Cancel", Gtk.ResponseType.CANCEL)
            chooser.add_button("Select", Gtk.ResponseType.OK)
            current = os.path.expanduser(mount_entry.get_text())
            if os.path.isdir(current):
                chooser.set_current_folder(current)
            if chooser.run() == Gtk.ResponseType.OK:
                selected = chooser.get_filename()
                home = os.path.expanduser("~")
                if selected and selected.startswith(home):
                    selected = "~" + selected[len(home):]
                mount_entry.set_text(selected or "")
            chooser.destroy()

        browse_btn.connect("clicked", _on_browse)
        grid.attach(browse_btn, 2, row, 1, 1)
        row += 1

        grid.attach(_grid_label("VFS Cache Mode"), 0, row, 1, 1)
        cache_combo = Gtk.ComboBoxText()
        for mode in _VFS_CACHE_MODES:
            cache_combo.append_text(mode)
        current_mode = settings.get("vfs_cache_mode", DEFAULTS["vfs_cache_mode"])
        if current_mode in _VFS_CACHE_MODES:
            cache_combo.set_active(_VFS_CACHE_MODES.index(current_mode))
        else:
            cache_combo.set_active(3)
        cache_combo.set_hexpand(True)
        grid.attach(cache_combo, 1, row, 2, 1)
        row += 1

        grid.attach(_grid_label("VFS Cache Max Size"), 0, row, 1, 1)
        cache_size_entry = Gtk.Entry()
        cache_size_entry.set_text(
            settings.get("vfs_cache_max_size", DEFAULTS["vfs_cache_max_size"])
        )
        cache_size_entry.set_hexpand(True)
        grid.attach(cache_size_entry, 1, row, 2, 1)
        row += 1

        grid.attach(_grid_label("VFS Write-Back"), 0, row, 1, 1)
        write_back_entry = Gtk.Entry()
        write_back_entry.set_text(
            settings.get("vfs_write_back", DEFAULTS["vfs_write_back"])
        )
        write_back_entry.set_hexpand(True)
        grid.attach(write_back_entry, 1, row, 2, 1)
        row += 1

        grid.attach(_grid_label("Dir Cache Time"), 0, row, 1, 1)
        dir_cache_entry = Gtk.Entry()
        dir_cache_entry.set_text(
            settings.get("dir_cache_time", DEFAULTS["dir_cache_time"])
        )
        dir_cache_entry.set_hexpand(True)
        grid.attach(dir_cache_entry, 1, row, 2, 1)
        row += 1

        grid.attach(_grid_label("Stats Interval"), 0, row, 1, 1)
        stats_entry = Gtk.Entry()
        stats_entry.set_text(
            settings.get("stats_interval", DEFAULTS["stats_interval"])
        )
        stats_entry.set_hexpand(True)
        grid.attach(stats_entry, 1, row, 2, 1)

        error_label = Gtk.Label()
        error_label.set_markup("")
        error_label.set_xalign(0.0)
        error_label.set_no_show_all(True)
        content.pack_start(error_label, False, False, 0)

        dialog.show_all()

        result: Optional[dict[str, str]] = None
        while True:
            response = dialog.run()
            if response != Gtk.ResponseType.OK:
                break

            remote_val = (remote_combo.get_active_text() or "").strip()
            mount_val = mount_entry.get_text().strip()

            errors: list[str] = []
            if not remote_val:
                errors.append("No remote selected")
            if not mount_val:
                errors.append("Mount Folder cannot be empty")

            if errors:
                error_label.set_markup(
                    f'<span foreground="red">{" | ".join(errors)}</span>'
                )
                error_label.show()
                continue

            result = {
                "remote": remote_val,
                "mount_point": mount_val,
                "vfs_cache_mode": cache_combo.get_active_text()
                or DEFAULTS["vfs_cache_mode"],
                "vfs_cache_max_size": cache_size_entry.get_text().strip()
                or DEFAULTS["vfs_cache_max_size"],
                "vfs_write_back": write_back_entry.get_text().strip()
                or DEFAULTS["vfs_write_back"],
                "dir_cache_time": dir_cache_entry.get_text().strip()
                or DEFAULTS["dir_cache_time"],
                "stats_interval": stats_entry.get_text().strip()
                or DEFAULTS["stats_interval"],
            }
            break

        dialog.destroy()
        return result

    def show_logs(self, text: str) -> None:
        icon = _get_app_icon()

        dialog = Gtk.Dialog(title="Rclone Mount - Logs")
        if icon:
            dialog.set_icon(icon)
        dialog.set_default_size(780, 500)
        dialog.add_button("Close", Gtk.ResponseType.CLOSE)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        tv = Gtk.TextView()
        tv.set_editable(False)
        tv.set_monospace(True)
        tv.get_buffer().set_text(text)
        scroll.add(tv)

        dialog.get_content_area().pack_start(scroll, True, True, 0)
        dialog.show_all()

        adj = scroll.get_vadjustment()
        adj.set_value(adj.get_upper())

        dialog.run()
        dialog.destroy()

    def open_folder(self, path: str) -> None:
        try:
            subprocess.Popen(
                ["xdg-open", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    def open_terminal_with(self, cmd: list[str]) -> bool:
        term = _find_terminal()
        if not term:
            return False
        if term == "gnome-terminal":
            prefix = [term, "--"]
        else:
            prefix = [term, "-e"]
        try:
            subprocess.Popen(
                prefix + cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False


def _grid_label(text: str) -> Gtk.Label:
    label = Gtk.Label(label=text)
    label.set_xalign(1.0)
    return label
