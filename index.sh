#!/usr/bin/env bash
# index.sh — Download and install rclone-tray without git
# Usage: curl -fsSL https://raw.githubusercontent.com/ishantoz/rclone-tray/main/index.sh | bash
set -euo pipefail

REPO_URL="https://github.com/ishantoz/rclone-tray/archive/refs/heads/main.tar.gz"
TMPDIR="$(mktemp -d)"

cleanup() {
    rm -rf "$TMPDIR"
}
trap cleanup EXIT

echo "==> Downloading rclone-tray..."
curl -fsSL "$REPO_URL" -o "$TMPDIR/rclone-tray.tar.gz"

echo "==> Extracting..."
tar -xzf "$TMPDIR/rclone-tray.tar.gz" -C "$TMPDIR"

cd "$TMPDIR/rclone-tray-main"
bash ./install.sh
