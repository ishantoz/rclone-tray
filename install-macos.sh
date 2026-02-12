#!/usr/bin/env bash
# install-macos.sh — Build and install rclone-tray on macOS
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_NAME="rclone-tray"
BIN_DIR="/usr/local/bin"

echo "==> Installing rclone-tray (macOS)"
echo ""

echo "[0/3] Checking system dependencies..."
MISSING=()

command -v rclone &>/dev/null || MISSING+=("rclone  (brew install rclone)")
command -v python3 &>/dev/null || MISSING+=("python3 (brew install python)")

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    echo "  ERROR: Missing required dependencies:"
    for dep in "${MISSING[@]}"; do
        echo "    - $dep"
    done
    echo ""
    echo "  Install Homebrew first (if not installed):"
    echo "    /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    echo ""
    echo "  Then install dependencies:"
    echo "    brew install rclone macfuse python"
    echo ""
    echo "  Note: macFUSE is required for rclone mount to work on macOS."
    echo "  After installing macFUSE, you may need to allow the kernel extension"
    echo "  in System Preferences > Security & Privacy."
    echo ""
    echo "  Then re-run: ./install-macos.sh"
    exit 1
fi

echo "  All dependencies found."
echo ""

echo "[1/3] Building binary..."
bash "$SCRIPT_DIR/build.sh"

echo "[2/3] Installing binary to $BIN_DIR/$BIN_NAME"
if [ -w "$BIN_DIR" ]; then
    cp "$SCRIPT_DIR/dist/$BIN_NAME" "$BIN_DIR/$BIN_NAME"
else
    echo "  (requires sudo for /usr/local/bin)"
    sudo cp "$SCRIPT_DIR/dist/$BIN_NAME" "$BIN_DIR/$BIN_NAME"
fi
chmod +x "$BIN_DIR/$BIN_NAME"
rm -rf "$SCRIPT_DIR/dist"

echo "[3/3] Done!"
echo ""
echo "  rclone-tray installed successfully!"
echo ""
echo "  Binary: $BIN_DIR/$BIN_NAME"
echo ""
echo "  To start:  rclone-tray"
echo "  Autostart can be enabled from the tray menu (creates a LaunchAgent)."
echo ""
echo "  Launching rclone-tray..."
nohup "$BIN_DIR/$BIN_NAME" &>/dev/null &
disown
