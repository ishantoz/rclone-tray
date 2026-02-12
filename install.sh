#!/usr/bin/env bash
# install.sh — Build and install rclone-tray (Linux)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_NAME="rclone-tray.desktop"
BIN_NAME="rclone-tray"

BIN_DIR="$HOME/.local/bin"
AUTOSTART_DIR="$HOME/.config/autostart"
APPS_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons"
ICON_NAME="rclone-tray.png"

echo "==> Installing rclone-tray"
echo ""

echo "[0/4] Checking system dependencies..."
MISSING=()

command -v rclone &>/dev/null || MISSING+=("rclone")
{ command -v fusermount &>/dev/null || command -v fusermount3 &>/dev/null; } || MISSING+=("fuse (fuse2 or fuse3)")

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    echo "  ERROR: Missing required dependencies:"
    for dep in "${MISSING[@]}"; do
        echo "    - $dep"
    done
    echo ""
    if command -v pacman &>/dev/null; then
        echo "  Install on Arch / CachyOS:"
        echo "    sudo pacman -S rclone fuse2"
    elif command -v apt &>/dev/null; then
        echo "  Install on Ubuntu / Debian:"
        echo "    sudo apt install rclone fuse"
    elif command -v dnf &>/dev/null; then
        echo "  Install on Fedora:"
        echo "    sudo dnf install rclone fuse"
    else
        echo "  Please install the missing packages using your package manager."
    fi
    echo ""
    echo "  Then re-run: ./install.sh"
    exit 1
fi

echo "  All dependencies found."
echo ""

echo "[1/4] Building binary..."
bash "$SCRIPT_DIR/build.sh"

echo "[2/4] Installing binary to $BIN_DIR/$BIN_NAME"
mkdir -p "$BIN_DIR"
cp "$SCRIPT_DIR/dist/$BIN_NAME" "$BIN_DIR/$BIN_NAME"
chmod +x "$BIN_DIR/$BIN_NAME"
rm -rf "$SCRIPT_DIR/dist"

echo "[3/4] Installing icon"
mkdir -p "$ICON_DIR"
cp "$SCRIPT_DIR/data/icons/rclone-active.png" "$ICON_DIR/$ICON_NAME"

echo "[4/4] Installing desktop entries"
mkdir -p "$AUTOSTART_DIR"
mkdir -p "$APPS_DIR"

cat > "$APPS_DIR/$DESKTOP_NAME" <<EOF
[Desktop Entry]
Type=Application
Name=Rclone Tray
Comment=System tray controller for rclone cloud storage mounts
Exec=$BIN_DIR/$BIN_NAME
Icon=$ICON_DIR/$ICON_NAME
Terminal=false
Categories=Utility;System;Network;FileTransfer;
StartupNotify=false
EOF

cat > "$AUTOSTART_DIR/$DESKTOP_NAME" <<EOF
[Desktop Entry]
Type=Application
Name=Rclone Tray
Comment=System tray controller for rclone cloud storage mounts
Exec=$BIN_DIR/$BIN_NAME
Icon=$ICON_DIR/$ICON_NAME
Terminal=false
Categories=Utility;System;
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF

echo ""
echo "  rclone-tray installed successfully!"
echo ""
echo "  Binary:    $BIN_DIR/$BIN_NAME"
echo "  App menu:  $APPS_DIR/$DESKTOP_NAME"
echo "  Autostart: $AUTOSTART_DIR/$DESKTOP_NAME"
echo "  Icon:      $ICON_DIR/$ICON_NAME"
echo ""
echo "  Launching rclone-tray..."
nohup "$BIN_DIR/$BIN_NAME" &>/dev/null &
disown
