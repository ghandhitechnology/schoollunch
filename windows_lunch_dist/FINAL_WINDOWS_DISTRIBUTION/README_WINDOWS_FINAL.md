# Final Windows Distribution

This folder is the clean Windows package. It intentionally excludes the old
backup-on-backup setup scripts.

## Use On Windows

1. Copy `FINAL_WINDOWS_DISTRIBUTION.zip` or this folder to the Windows PC.
2. Extract it to a simple path, preferably `C:\schoollunch_final\`.
3. Double-click `RUN_ME_ON_WINDOWS.bat`.

The script will:

- verify the required source files, fonts, icon, manifest, and version metadata
- move itself to a safe ASCII build path if the copied path has spaces or Korean
  characters that can break Windows build tools
- find Python 3.10+ or install Python 3.12.4 for the current user
- create a clean virtual environment
- install `requirements.txt`
- run `test_app.py`
- build `dist\하태욱 프로그램.exe` with `assets\icons\app_icon.ico`
- install the app into `%LOCALAPPDATA%\하태욱프로그램`
- create Start Menu and desktop shortcuts
- register user-level startup with both the Windows Run key and Task Scheduler

## Files To Keep Together

Do not remove these from the package:

- `main.py`, `app_ui.py`, `fetch_meal.py`, `fetch_timetable.py`, `render.py`,
  `wallpaper.py`, `config.py`, `autostart.py`, `settings_ui.py`,
  `custom_editor.py`, `ui_common.py`
- `assets\fonts\neodgm.ttf`
- `assets\fonts\handdrawn.ttf`
- `assets\icons\app_icon.ico`
- `requirements.txt`
- `windows_build.spec`
- `windows_manifest.xml`
- `windows_version_info.txt`
- `setup_windows_final.ps1`
- `RUN_ME_ON_WINDOWS.bat`

## Useful Commands

Build only:

```bat
BUILD_ONLY_WINDOWS.bat
```

Install an already-built `dist\하태욱 프로그램.exe` or
`prebuilt\하태욱 프로그램.exe`:

```bat
INSTALL_EXISTING_EXE_WINDOWS.bat
```

Uninstall:

```bat
UNINSTALL_WINDOWS.bat
```

## Mac To Windows Note

Build the Windows exe on Windows. PyInstaller does not reliably cross-compile a
Windows `.exe` from macOS. This package is made on macOS, but the final build
step must happen after copying it to the Windows machine.

If Windows has no Python, keep internet enabled and run `RUN_ME_ON_WINDOWS.bat`;
it installs Python for the current user before building. After PyInstaller
builds the app, the installed `하태욱 프로그램.exe` no longer needs Python to
be present on PATH.
