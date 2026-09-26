# Setup

The project has no external services or environment variables to configure —
the NEIS meal API needs no key, and the school/region codes are resolved and
cached automatically on first run. Setup is just Python, dependencies, and an
optional PyInstaller build.

All commands below run from the `개발용` directory, where the source lives.

## Requirements

- Python 3.10 or newer
- Dependencies (`requirements.txt`):
  - `requests` — NEIS meal API and comci.net timetable
  - `Pillow` — wallpaper rendering
  - `pystray` — system tray
  - `pyinstaller` — standalone builds
  - `pyobjc-framework-Cocoa` — macOS only, installed automatically by the
    `sys_platform == "darwin"` marker

## Install

```bash
cd 개발용
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

On Windows, use `.venv\Scripts\pip` instead of `.venv/bin/pip`.

## Run from source

```bash
.venv/bin/python main.py
```

The full application window opens: class/theme/background/autostart settings,
image generation, wallpaper application, and meal/timetable preview. On first
run it asks you to pick your class (1-1 to 1-4).

Command-line modes:

| Command | Behavior |
|---|---|
| `python main.py --ui` | open the app window only |
| `python main.py --render-only` | render the wallpaper PNG to the config dir and exit |
| `python main.py --once` | refresh once, apply the wallpaper, exit |
| `python main.py --once --no-wallpaper` | render once without touching the desktop |
| `python main.py --background` | refresh, then stay in the system tray |

On macOS, applying the wallpaper uses `System Events`, so the first run may
prompt for automation/accessibility permission. If a managed policy blocks
wallpaper changes entirely, use `--render-only` to generate the image without
applying it.

## Build a standalone executable

Windows (cmd):

```bat
pip install -r requirements.txt
build.bat
```

Windows (PowerShell):

```powershell
pip install -r requirements.txt
.\build.ps1
```

If the execution policy blocks the script:
`powershell -ExecutionPolicy Bypass -File build.ps1`

Output: `dist\하태욱 프로그램.exe` (icon: `assets/icons/app_icon.ico`).
`build.bat` and `build.ps1` generate the Windows version metadata from
`version.py` before packaging.

macOS:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./build_macos.sh
```

Output: `dist-macos/하태욱 프로그램.app` (icon: `assets/icons/app_icon.icns`).

## Publish a Windows auto-update

The release workflow builds from `windows_lunch_dist` when a semantic-version
tag is pushed. Set the same `APP_VERSION` in `개발용/version.py` and
`windows_lunch_dist/version.py`, commit it, then push the matching tag:

```bash
git tag v1.1.0
git push origin v1.1.0
```

The tag and `APP_VERSION` must match exactly. GitHub Actions publishes
`hataewook-program-windows.exe` and its `.sha256` file. Packaged Windows apps
check the latest stable release at startup and install newer versions silently.

## Development checks

```bash
.venv/bin/python fetch_meal.py        # meal fetch, standalone
.venv/bin/python fetch_timetable.py   # timetable fetch, standalone
.venv/bin/python render.py            # writes preview.png (1920×1080)
.venv/bin/python test_app.py          # logic tests; uses temp dirs, never touches real settings
.venv/bin/python test_ui.py           # UI stress test; opens real Tk windows
```

## Data locations

Settings, cache, and logs are stored per user, never in the repository:

- Windows: `%APPDATA%\하태욱프로그램\`
- macOS: `~/.config/하태욱프로그램/`
