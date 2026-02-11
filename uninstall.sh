#!/usr/bin/env bash
# uninstall.sh — Completely reverse everything install.sh did
set -euo pipefail

SERVICE_NAME="rclone-mount.service"
DESKTOP_NAME="rclone-tray.desktop"
BIN_NAME="rclone-tray"

BIN_DIR="$HOME/.local/bin"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
AUTOSTART_DIR="$HOME/.config/autostart"
APPS_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons"
ICON_NAME="rclone-tray.png"
LOCK_FILE="$HOME/.cache/rclone-tray.lock"
SETTINGS_FILE="$HOME/.config/rclone-tray/settings.json"
SETTINGS_DIR="$HOME/.config/rclone-tray"

# Read mount point from settings, fall back to default
if [ -f "$SETTINGS_FILE" ] && command -v python3 &>/dev/null; then
    MOUNT_POINT="$(python3 -c "import json,os; d=json.load(open('$SETTINGS_FILE')); print(os.path.expanduser(d.get('mount_point','~/GoogleDrive')))" 2>/dev/null || echo "$HOME/GoogleDrive")"
else
    MOUNT_POINT="$HOME/GoogleDrive"
fi

echo "==> Uninstalling rclone-tray"

# Kill any running instance
if pgrep -xf ".*rclone-tray.*" &>/dev/null; then
    echo "  -> Killing running rclone-tray process"
    pkill -xf ".*rclone-tray.*" 2>/dev/null || true
    sleep 1
fi

# Stop and disable systemd service
if systemctl --user is-active "$SERVICE_NAME" &>/dev/null; then
    echo "  -> Stopping $SERVICE_NAME"
    systemctl --user stop "$SERVICE_NAME"
fi

if systemctl --user is-enabled "$SERVICE_NAME" &>/dev/null; then
    echo "  -> Disabling $SERVICE_NAME"
    systemctl --user disable "$SERVICE_NAME"
fi

# Remove service file and reload
if [ -f "$SYSTEMD_USER_DIR/$SERVICE_NAME" ]; then
    echo "  -> Removing $SYSTEMD_USER_DIR/$SERVICE_NAME"
    rm -f "$SYSTEMD_USER_DIR/$SERVICE_NAME"
fi
systemctl --user daemon-reload
systemctl --user reset-failed 2>/dev/null || true

# Remove binary
if [ -f "$BIN_DIR/$BIN_NAME" ]; then
    echo "  -> Removing $BIN_DIR/$BIN_NAME"
    rm -f "$BIN_DIR/$BIN_NAME"
fi

# Remove autostart desktop entry
if [ -f "$AUTOSTART_DIR/$DESKTOP_NAME" ]; then
    echo "  -> Removing $AUTOSTART_DIR/$DESKTOP_NAME"
    rm -f "$AUTOSTART_DIR/$DESKTOP_NAME"
fi

# Remove app menu desktop entry
if [ -f "$APPS_DIR/$DESKTOP_NAME" ]; then
    echo "  -> Removing $APPS_DIR/$DESKTOP_NAME"
    rm -f "$APPS_DIR/$DESKTOP_NAME"
fi

# Remove icon
if [ -f "$ICON_DIR/$ICON_NAME" ]; then
    echo "  -> Removing $ICON_DIR/$ICON_NAME"
    rm -f "$ICON_DIR/$ICON_NAME"
fi

# Remove lock file
rm -f "$LOCK_FILE"

# Unmount but keep the folder
if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
    echo "  -> Unmounting $MOUNT_POINT"
    fusermount -uz "$MOUNT_POINT" 2>/dev/null || fusermount3 -uz "$MOUNT_POINT" 2>/dev/null || true
fi

# Remove settings
if [ -d "$SETTINGS_DIR" ]; then
    echo "  -> Removing $SETTINGS_DIR"
    rm -rf "$SETTINGS_DIR"
fi

# Remove any leftover symlinks systemd may have created
rm -f "$SYSTEMD_USER_DIR/default.target.wants/$SERVICE_NAME" 2>/dev/null || true

echo ""
echo "  rclone-tray fully uninstalled."
echo ""
echo "  Removed:"
echo "    $BIN_DIR/$BIN_NAME"
echo "    $SYSTEMD_USER_DIR/$SERVICE_NAME"
echo "    $APPS_DIR/$DESKTOP_NAME"
echo "    $AUTOSTART_DIR/$DESKTOP_NAME"
echo "    $ICON_DIR/$ICON_NAME"
echo "    $LOCK_FILE"
echo "    $SETTINGS_DIR"
echo ""
echo "  Untouched:"
echo "    $MOUNT_POINT        (your files)"
echo "    ~/.config/rclone/   (your rclone remotes)"
echo "    rclone binary       (system package)"
