#!/usr/bin/env bash
# install.sh — Build and install rclone-tray
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

echo "[1/5] Checking system dependencies..."
MISSING=()

command -v rclone &>/dev/null || MISSING+=("rclone")
{ command -v fusermount &>/dev/null || command -v fusermount3 &>/dev/null; } || MISSING+=("fuse (fuse2 or fuse3)")
python3 -c "import gi; gi.require_version('Gtk', '3.0')" &>/dev/null || MISSING+=("gtk3 (pygobject)")
python3 -c "import gi; gi.require_version('AppIndicator3', '0.1')" &>/dev/null || MISSING+=("libappindicator-gtk3")
python3 -c "import gi; gi.require_version('Notify', '0.7')" &>/dev/null || MISSING+=("libnotify")

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    echo "  ERROR: Missing required dependencies:"
    for dep in "${MISSING[@]}"; do
        echo "    - $dep"
    done
    echo ""
    if command -v pacman &>/dev/null; then
        echo "  Install on Arch / CachyOS:"
        echo "    sudo pacman -S rclone libappindicator-gtk3 libnotify fuse2"
    elif command -v apt &>/dev/null; then
        echo "  Install on Ubuntu / Debian:"
        echo "    sudo apt install rclone gir1.2-appindicator3-0.1 libnotify-dev fuse"
    elif command -v dnf &>/dev/null; then
        echo "  Install on Fedora:"
        echo "    sudo dnf install rclone libappindicator-gtk3 libnotify fuse"
    else
        echo "  Please install the missing packages using your package manager."
    fi
    echo ""
    echo "  Then re-run: ./install.sh"
    exit 1
fi

echo "  All dependencies found."
echo ""

echo "[2/5] Building binary..."
bash "$SCRIPT_DIR/build.sh"

echo "[3/5] Installing binary to $BIN_DIR/$BIN_NAME"
mkdir -p "$BIN_DIR"
cp "$SCRIPT_DIR/dist/$BIN_NAME" "$BIN_DIR/$BIN_NAME"
chmod +x "$BIN_DIR/$BIN_NAME"
rm -rf "$SCRIPT_DIR/dist"

echo "[4/5] Installing icon"
mkdir -p "$ICON_DIR"
cp "$SCRIPT_DIR/data/icons/rclone-active.png" "$ICON_DIR/$ICON_NAME"

echo "[5/5] Installing desktop entries"
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
