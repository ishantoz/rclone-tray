"""GTK tray indicator, menu construction, log dialog, and settings dialog."""

from __future__ import annotations

import os
import subprocess
from typing import Callable, Optional

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
from gi.repository import AppIndicator3, GdkPixbuf, Gtk  # type: ignore[attr-defined]  # noqa: E402

from .config import APP_ID, ICON_RUNNING, ICON_STOPPED, SERVICE_NAME  # noqa: E402

_APP_ICON: GdkPixbuf.Pixbuf | None = None


def _get_app_icon() -> GdkPixbuf.Pixbuf | None:
    """Load and cache the app icon as a pixbuf."""
    global _APP_ICON
    if _APP_ICON is None:
        try:
            _APP_ICON = GdkPixbuf.Pixbuf.new_from_file(ICON_RUNNING)
        except Exception:
            pass
    return _APP_ICON
from .settings import DEFAULTS, get_mount_point, load as load_settings  # noqa: E402
from .service import SystemdService  # noqa: E402
from .utils import find_terminal  # noqa: E402

_VFS_CACHE_MODES = ["off", "minimal", "writes", "full"]


def _get_rclone_remotes() -> list[str]:
    """Return a list of configured rclone remotes (e.g. ['gdrive:', 'onedrive:'])."""
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


def create_indicator() -> AppIndicator3.Indicator:
    icon = _get_app_icon()
    if icon:
        Gtk.Window.set_default_icon(icon)
    indicator = AppIndicator3.Indicator.new(
        APP_ID,
        ICON_STOPPED,
        AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
    )
    indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
    return indicator


class TrayMenu:
    """Builds and exposes the tray context menu."""

    def __init__(
        self,
        *,
        on_start: Callable,
        on_stop: Callable,
        on_restart: Callable,
        on_open_folder: Callable,
        on_view_logs: Callable,
        on_reconfigure: Callable,
        on_settings: Callable,
        on_toggle_autostart: Callable,
        on_quit: Callable,
        on_uninstall: Callable,
    ) -> None:
        self.menu = Gtk.Menu()

        self.status_item = _label(self.menu, "Checking...")
        self.info_item = _label(self.menu, "")
        _sep(self.menu)

        self.start_item = _action(self.menu, "Start Mount", on_start)
        self.stop_item = _action(self.menu, "Stop Mount", on_stop)
        self.restart_item = _action(self.menu, "Restart Mount", on_restart)
        _sep(self.menu)

        _action(self.menu, "Open Mount Folder", on_open_folder)
        _action(self.menu, "View Logs", on_view_logs)
        _action(self.menu, "Reconfigure Rclone", on_reconfigure)
        _action(self.menu, "Settings", on_settings)
        self.autostart_item = _action(self.menu, "Enable Autostart", on_toggle_autostart)
        _sep(self.menu)

        _action(self.menu, "Uninstall Service", on_uninstall)
        _action(self.menu, "Quit (Unmount && Disable)", on_quit)

        self.menu.show_all()

    @property
    def gtk_menu(self) -> Gtk.Menu:
        return self.menu


def open_live_logs() -> None:
    """Open a live journal tail in a terminal, or a GTK dialog as fallback."""
    cmd = ["journalctl", "--user", "-u", SERVICE_NAME, "-f", "--no-pager"]
    term_cmd = _find_term_cmd()
    if term_cmd:
        try:
            subprocess.Popen(
                term_cmd + cmd,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return
        except Exception:
            pass
    _show_logs_dialog()


def _find_term_cmd() -> list[str] | None:
    """Return the terminal prefix args (e.g. ['kitty', '-e']) or None."""
    term = find_terminal()
    if not term:
        return None
    if term == "gnome-terminal":
        return [term, "--"]
    return [term, "-e"]


def open_mount_folder() -> None:
    """Open the mount point in the default file manager."""
    try:
        subprocess.Popen(
            ["xdg-open", get_mount_point()],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def _show_logs_dialog() -> None:
    text = SystemdService.get_recent_logs(100)

    dialog = Gtk.Dialog(title="Rclone Mount - Logs")
    icon = _get_app_icon()
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


def show_settings_dialog() -> Optional[dict[str, str]]:
    """Open a GTK dialog for editing service settings. Returns new settings or None."""
    settings = load_settings()

    dialog = Gtk.Dialog(title="Rclone Mount - Settings")
    icon = _get_app_icon()
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

    # Remote name
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

    # Mount folder with browse button
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
        icon = _get_app_icon()
        if icon:
            chooser.set_icon(icon)
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

    # VFS cache mode dropdown
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

    # VFS cache max size
    grid.attach(_grid_label("VFS Cache Max Size"), 0, row, 1, 1)
    cache_size_entry = Gtk.Entry()
    cache_size_entry.set_text(settings.get("vfs_cache_max_size", DEFAULTS["vfs_cache_max_size"]))
    cache_size_entry.set_hexpand(True)
    grid.attach(cache_size_entry, 1, row, 2, 1)
    row += 1

    # VFS write-back
    grid.attach(_grid_label("VFS Write-Back"), 0, row, 1, 1)
    write_back_entry = Gtk.Entry()
    write_back_entry.set_text(settings.get("vfs_write_back", DEFAULTS["vfs_write_back"]))
    write_back_entry.set_hexpand(True)
    grid.attach(write_back_entry, 1, row, 2, 1)
    row += 1

    # Dir cache time
    grid.attach(_grid_label("Dir Cache Time"), 0, row, 1, 1)
    dir_cache_entry = Gtk.Entry()
    dir_cache_entry.set_text(settings.get("dir_cache_time", DEFAULTS["dir_cache_time"]))
    dir_cache_entry.set_hexpand(True)
    grid.attach(dir_cache_entry, 1, row, 2, 1)
    row += 1

    # Stats interval
    grid.attach(_grid_label("Stats Interval"), 0, row, 1, 1)
    stats_entry = Gtk.Entry()
    stats_entry.set_text(settings.get("stats_interval", DEFAULTS["stats_interval"]))
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
            "vfs_cache_mode": cache_combo.get_active_text() or DEFAULTS["vfs_cache_mode"],
            "vfs_cache_max_size": cache_size_entry.get_text().strip() or DEFAULTS["vfs_cache_max_size"],
            "vfs_write_back": write_back_entry.get_text().strip() or DEFAULTS["vfs_write_back"],
            "dir_cache_time": dir_cache_entry.get_text().strip() or DEFAULTS["dir_cache_time"],
            "stats_interval": stats_entry.get_text().strip() or DEFAULTS["stats_interval"],
        }
        break

    dialog.destroy()
    return result


def _grid_label(text: str) -> Gtk.Label:
    """Create a right-aligned label for the settings grid."""
    label = Gtk.Label(label=text)
    label.set_xalign(1.0)
    return label


def _label(menu: Gtk.Menu, text: str) -> Gtk.MenuItem:
    item = Gtk.MenuItem(label=text)
    item.set_sensitive(False)
    menu.append(item)
    return item


def _action(menu: Gtk.Menu, text: str, callback: Callable) -> Gtk.MenuItem:
    item = Gtk.MenuItem(label=text)
    item.connect("activate", callback)
    menu.append(item)
    return item


def _sep(menu: Gtk.Menu) -> None:
    menu.append(Gtk.SeparatorMenuItem())
