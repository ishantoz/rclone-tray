# rclone-tray

Mount your cloud storage as a local folder. Runs in the system tray.

Works on **Linux**, **macOS**, and **Windows**.

Supports Google Drive, OneDrive, Dropbox, S3, SFTP, and [40+ other services](https://rclone.org/overview/) through [rclone](https://rclone.org/).

## The Problem

Using Google Drive, OneDrive, or any cloud storage on Linux is painfully hard. On Windows and macOS you get official sync clients that just work. On Linux — especially Arch-based distros like CachyOS, Manjaro, and EndeavourOS — you get nothing. There's no official Google Drive client for Linux. OneDrive has no native app. Dropbox barely maintains theirs.

The few third-party options are either paid, half-broken, or abandoned. If you've ever tried to sync your files on an Arch install, you know the frustration: searching the AUR for sketchy packages, wrestling with OAuth tokens, or settling for a janky web-only workflow.

**A common real-world example:** many people use [Obsidian](https://obsidian.md/) and want to sync their vault across devices. Obsidian Sync costs money, and the free workaround is to put your vault folder on Google Drive or OneDrive. That works great on Windows and macOS — but on Linux, there's no simple way to keep that cloud folder mounted and in sync. You end up with stale notes, merge conflicts, or just giving up and paying for Sync.

This is exactly the kind of problem [rclone](https://rclone.org/) solves. rclone supports [40+ cloud storage providers](https://rclone.org/overview/) — Google Drive, OneDrive, Dropbox, S3, SFTP, and many more — all through a single command-line tool. It can mount any of them as a regular folder on your computer. It's free, open-source, and rock-solid. If your cloud provider exists, rclone almost certainly supports it.

The only catch: rclone is a CLI tool. There's no GUI, no tray icon, no "set it and forget it" experience. You have to run commands in a terminal, write your own systemd unit files, and manage everything by hand. That's where rclone-tray comes in.

## Why This Exists

rclone-tray puts a friendly tray icon on top of rclone so you can mount, unmount, and configure your cloud storage without touching a terminal. It handles the systemd service (or launchd on macOS, or a background process on Windows), autostart on login, and gives you a settings dialog for everything.

I built it because I wanted a minimal, useful tray app that handles all of that — install, configure, mount, and forget. Right-click when you need to change something. No terminal required after setup.

Whether you want to sync your Obsidian vault, keep your documents backed up, or just have Google Drive available as a folder on your Arch Linux desktop — rclone-tray makes it work the same way it does on every other OS.

It's written in Python so anyone can read, modify, or extend it to fit their own workflow.

---

## How It Works

1. You set up a cloud storage connection with `rclone config` (one-time setup)
2. rclone-tray mounts it as a regular folder on your computer
3. The tray icon lets you start, stop, and configure everything

Your cloud files appear in a local folder (like `~/GoogleDrive`) and stay in sync. When you're done, stop the mount from the tray or just close the app.

## What You Get

- A tray icon that shows whether your cloud storage is mounted
- Right-click menu to control everything
- Starts automatically when you log in (configurable)
- A settings dialog to change the remote, mount folder, and cache options
- Desktop notifications when the mount starts or stops
- Single instance only — running it again won't open duplicates
- Cross-platform: same interface on Linux, macOS, and Windows

---

## Before You Install

You need two things ready before running the installer.

### 1. Install system packages

#### Linux (Arch / CachyOS / Manjaro)

```bash
sudo pacman -S python rclone fuse2
```

#### Linux (Ubuntu / Debian)

```bash
sudo apt install python3 rclone fuse
```

#### Linux (Fedora)

```bash
sudo dnf install python3 rclone fuse
```

#### macOS

```bash
brew install rclone macfuse python
```

> After installing macFUSE, allow the kernel extension in System Preferences > Security & Privacy.

#### Windows

1. Install [Python 3.11+](https://www.python.org/downloads/)
2. Install [rclone](https://rclone.org/downloads/)
3. Install [WinFsp](https://winfsp.dev/) (FUSE layer for Windows)
4. Make sure `rclone` is in your PATH

### 2. Set up your cloud storage in rclone

rclone-tray mounts whatever remote you've configured in rclone. If you haven't done this yet, open a terminal and run:

```bash
rclone config
```

This walks you through connecting to your cloud storage step by step. Pick your provider, sign in, and you're done. Each provider has its own page in the [rclone docs](https://rclone.org/docs/) if you get stuck.

**Quick example for Google Drive:**

```bash
rclone config
```

```
n            # new remote
gdrive       # name it whatever you want
drive        # pick Google Drive
             # press Enter through client ID and secret (use defaults)
1            # full access scope
             # press Enter through the rest
y            # auto config — a browser opens, sign in and allow access
n            # not a shared drive (unless it is)
y            # confirm
q            # quit config
```

**Verify it works:**

```bash
rclone ls gdrive: --max-depth 1
```

If you see your files listed, you're ready.

> This works the same way for any provider. Just pick a different storage type in step 3. See [rclone.org/overview](https://rclone.org/overview/) for the full list.

---

## Install

### Linux

```bash
git clone https://github.com/ishantoz/rclone-tray.git
cd rclone-tray
./install.sh
```

The installer checks dependencies, builds a standalone binary, installs it to `~/.local/bin/`, adds it to your app menu and autostart, and launches the tray.

### macOS

```bash
git clone https://github.com/ishantoz/rclone-tray.git
cd rclone-tray
./install-macos.sh
```

The installer checks for rclone and Python, builds a binary, installs it to `/usr/local/bin/`, and launches the tray. Autostart can be enabled from the tray menu.

### Windows

```bash
git clone https://github.com/ishantoz/rclone-tray.git
cd rclone-tray
pip install .
rclone-tray
```

Or run from source:

```bash
pip install .
python -m rclone_tray
```

To enable autostart, use the "Enable Autostart" option in the tray menu (sets a Registry Run key).

---

On first launch, a **Settings** dialog opens where you pick your remote and mount folder.

From the next login onward, it starts automatically and mounts your storage.

## Uninstall

### Linux

```bash
./uninstall.sh
```

Removes the binary, systemd service, desktop entries, and settings. Your mount folder and rclone configuration are **not** deleted — your files stay safe.

### macOS

Remove the binary and LaunchAgents:

```bash
rm -f /usr/local/bin/rclone-tray
rm -f ~/Library/LaunchAgents/com.rclone-tray.mount.plist
rm -f ~/Library/LaunchAgents/com.rclone-tray.plist
rm -rf ~/Library/Application\ Support/rclone-tray
rm -rf ~/Library/Caches/rclone-tray
```

### Windows

```bash
pip uninstall rclone-tray
```

Then remove the autostart Registry entry (if enabled) from the tray menu first, or manually delete `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\RcloneTray`.

Settings are stored in `%APPDATA%\rclone-tray\` — delete that folder to clean up fully.

---

## Using the Tray Menu

Right-click the tray icon to see these options:

| Option | What it does |
|---|---|
| **Status line** | Shows if the mount is running or stopped, plus uptime and disk usage |
| **Start Mount** | Starts the mount |
| **Stop Mount** | Stops the mount |
| **Restart Mount** | Restarts the mount |
| **Open Mount Folder** | Opens your mount folder in the file manager |
| **View Logs** | Opens live service logs (terminal on Linux, dialog on macOS/Windows) |
| **Reconfigure Rclone** | Stops the mount, opens `rclone config` in a terminal, then restarts |
| **Settings** | Change remote, mount folder, cache size, and other options |
| **Enable/Disable Autostart** | Toggle whether it starts on login |
| **Uninstall Service** | Removes the service and autostart, then exits |
| **Quit** | Stops the mount and exits |

## Settings You Can Change

Open **Settings** from the tray menu. Everything is configurable:

| Setting | Default | What it controls |
|---|---|---|
| **Remote** | `gdrive:` | Which rclone remote to mount (dropdown of your configured remotes) |
| **Mount Folder** | `~/GoogleDrive` | Where the files appear on your computer (has a folder picker) |
| **VFS Cache Mode** | `full` | How aggressively rclone caches files locally |
| **VFS Cache Max Size** | `10G` | Maximum local disk space for the cache |
| **VFS Write-Back** | `5s` | How quickly writes are pushed to the cloud |
| **Dir Cache Time** | `2m` | How long directory listings are cached |
| **Stats Interval** | `30s` | How often transfer stats are logged |

After saving, the service restarts automatically with the new settings.

---

## Tips

- **Slow uploads?** Increase **VFS Write-Back** to `30s` or `1m` so writes batch together.
- **Running out of disk?** Lower **VFS Cache Max Size** to `2G` or `5G`.
- **Files not updating?** Lower **Dir Cache Time** to `30s` or `10s`.
- **Using multiple cloud accounts?** Set up multiple remotes with `rclone config`, then switch between them in Settings.
- **Something broken?** Click **View Logs** to see what rclone is doing. Most issues are visible there.
- **Want to change cloud provider?** Click **Reconfigure Rclone** to open the rclone setup wizard, then update the remote in Settings.

---

## For Developers

To run from source without building:

```bash
uv run rclone-tray
# or
python -m rclone_tray
```

### Project Structure

```
rclone-tray/
├── src/rclone_tray/
│   ├── app.py                 # Main orchestrator (platform-agnostic)
│   ├── config.py              # Platform-aware paths and constants
│   ├── settings.py            # Persistent JSON settings
│   ├── tray.py                # pystray-based system tray icon
│   └── platform/
│       ├── __init__.py        # Platform detection and backend factory
│       ├── base.py            # Abstract interfaces
│       ├── linux/
│       │   ├── service.py     # systemd service manager
│       │   ├── dialogs.py     # GTK settings & log dialogs
│       │   ├── autostart.py   # .desktop file autostart
│       │   └── lock.py        # fcntl file lock
│       ├── macos/
│       │   ├── service.py     # launchd service manager
│       │   ├── dialogs.py     # tkinter dialogs
│       │   ├── autostart.py   # LaunchAgent autostart
│       │   └── lock.py        # fcntl file lock
│       └── windows/
│           ├── service.py     # subprocess-based service
│           ├── dialogs.py     # tkinter dialogs
│           ├── autostart.py   # Registry Run key
│           └── lock.py        # msvcrt file lock
├── data/
│   └── icons/                 # Tray icons (active / stopped)
├── entry.py                   # PyInstaller entry point
├── install.sh                 # Linux installer
├── install-macos.sh           # macOS installer
├── uninstall.sh               # Linux uninstaller
├── build.sh                   # Build standalone binary
└── pyproject.toml             # Project metadata
```

### Platform Architecture

The app uses a backend abstraction layer. At startup, it detects the OS and loads the right implementations for:

- **ServiceBackend** — manages the rclone mount process (systemd / launchd / subprocess)
- **DialogBackend** — settings and log dialogs (GTK on Linux, tkinter elsewhere)
- **AutostartBackend** — login autostart (.desktop / LaunchAgent / Registry)
- **InstanceLock** — single-instance guard (fcntl / msvcrt)

The core `app.py` and `tray.py` are completely platform-agnostic.

## License

MIT
