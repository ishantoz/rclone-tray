# rclone-tray

Mount your cloud storage as a local folder on Linux. Runs in the system tray.

Works with Google Drive, OneDrive, Dropbox, S3, SFTP, and [40+ other services](https://rclone.org/overview/) through [rclone](https://rclone.org/).

## Why This Exists

rclone is powerful, but there's no simple way to run it as a background mount and control it from the desktop. You either babysit a terminal, write your own systemd service, or dig through config files every time something needs to change.

I built rclone-tray because I wanted a minimal, useful tray app that handles all of that — install, configure, mount, and forget. Right-click when you need to change something. No terminal required after setup.

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
- Starts automatically when you log in
- A settings dialog to change the remote, mount folder, and cache options
- Desktop notifications when the mount starts or stops
- Single instance only — clicking the icon again won't open duplicates

---

## Before You Install

You need two things ready before running the installer.

### 1. Install system packages

The installer will check for these and tell you what's missing, but it's easier to install them upfront.

**Arch / CachyOS / Manjaro:**

```bash
sudo pacman -S python rclone libappindicator-gtk3 libnotify fuse2
```

**Ubuntu / Debian:**

```bash
sudo apt install python3 rclone gir1.2-appindicator3-0.1 libnotify-dev fuse
```

**Fedora:**

```bash
sudo dnf install python3 rclone libappindicator-gtk3 libnotify fuse
```

**Other distros:** install `rclone`, `python 3.11+`, `gtk3`, `libappindicator-gtk3`, `libnotify`, and `fuse` using your package manager.

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

```bash
git clone https://github.com/ishantoz/rclone-tray.git
cd rclone-tray
./install.sh
```

That's it. The installer:

1. Checks all dependencies are present
2. Builds a standalone binary (no Python needed after this)
3. Installs it to `~/.local/bin/rclone-tray`
4. Adds it to your app menu and autostart
5. Launches the tray app

On first launch, a **Settings** dialog opens where you pick your remote and mount folder.

From the next login onward, it starts automatically and mounts your storage.

## Uninstall

```bash
./uninstall.sh
```

This removes the binary, the systemd service, the desktop entries, and the settings. Your mount folder and rclone configuration are **not** deleted — your files stay safe.

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
| **View Logs** | Opens live service logs in a terminal window |
| **Reconfigure Rclone** | Stops the mount, opens `rclone config` in a terminal, then restarts |
| **Settings** | Change remote, mount folder, cache size, and other options |
| **Enable/Disable Autostart** | Toggle whether it starts on login |
| **Uninstall Service** | Removes the systemd service and autostart, then exits |
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
├── src/rclone_tray/        # Python source
│   ├── app.py              # Main app class, lifecycle, callbacks
│   ├── config.py           # Paths and constants
│   ├── settings.py         # Persistent JSON settings (~/.config/rclone-tray/)
│   ├── service.py          # Systemd service manager + unit file generator
│   ├── ui.py               # GTK tray menu, settings dialog, log viewer
│   └── utils.py            # Formatting, terminal detection, file locking
├── data/
│   └── icons/              # Tray icons (active / stopped)
├── entry.py                # PyInstaller entry point
├── install.sh              # Build + install + autostart
├── uninstall.sh            # Full cleanup
├── build.sh                # Build standalone binary
└── pyproject.toml          # Project metadata
```

## License

MIT
