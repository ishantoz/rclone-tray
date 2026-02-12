#!/usr/bin/env bash
# build.sh — Build the rclone-tray standalone binary
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_NAME="rclone-tray"

echo "==> Building rclone-tray"

echo "[1/2] Installing dependencies..."
if command -v uv &>/dev/null; then
    (cd "$SCRIPT_DIR" && uv sync)
    uv pip install --python "$SCRIPT_DIR/.venv/bin/python" pyinstaller
else
    python3 -m venv "$SCRIPT_DIR/.venv"
    "$SCRIPT_DIR/.venv/bin/pip" install -q "$SCRIPT_DIR" pyinstaller
fi

PY="$SCRIPT_DIR/.venv/bin/python"

HIDDEN_IMPORTS=(
    --hidden-import=rclone_tray
    --hidden-import=rclone_tray.app
    --hidden-import=rclone_tray.config
    --hidden-import=rclone_tray.settings
    --hidden-import=rclone_tray.tray
    --hidden-import=rclone_tray.platform
    --hidden-import=rclone_tray.platform.base
    --hidden-import=pystray
    --hidden-import=PIL
)

case "$(uname -s)" in
    Linux*)
        HIDDEN_IMPORTS+=(
            --hidden-import=rclone_tray.platform.linux
            --hidden-import=rclone_tray.platform.linux.service
            --hidden-import=rclone_tray.platform.linux.dialogs
            --hidden-import=rclone_tray.platform.linux.autostart
            --hidden-import=rclone_tray.platform.linux.lock
            --hidden-import=gi
            --hidden-import=gi.repository.Gtk
            --hidden-import=gi.repository.GdkPixbuf
        )
        ;;
    Darwin*)
        HIDDEN_IMPORTS+=(
            --hidden-import=rclone_tray.platform.macos
            --hidden-import=rclone_tray.platform.macos.service
            --hidden-import=rclone_tray.platform.macos.dialogs
            --hidden-import=rclone_tray.platform.macos.autostart
            --hidden-import=rclone_tray.platform.macos.lock
            --hidden-import=tkinter
            --hidden-import=plistlib
        )
        ;;
esac

echo "[2/2] Building binary..."
PYTHONPATH="$SCRIPT_DIR/src" $PY -m PyInstaller \
    --onefile \
    --name "$BIN_NAME" \
    --noconfirm \
    --clean \
    --paths "$SCRIPT_DIR/src" \
    --add-data "$SCRIPT_DIR/data:data" \
    "${HIDDEN_IMPORTS[@]}" \
    "$SCRIPT_DIR/entry.py" \
    --distpath "$SCRIPT_DIR/dist" \
    --workpath "$SCRIPT_DIR/build" \
    --specpath "$SCRIPT_DIR" \
    2>&1 | tail -3

rm -rf "$SCRIPT_DIR/build" "$SCRIPT_DIR/$BIN_NAME.spec"

echo ""
echo "  Binary ready: $SCRIPT_DIR/dist/$BIN_NAME"
