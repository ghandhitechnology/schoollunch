# -*- coding: utf-8 -*-
"""OS wallpaper integration."""
import os
import shutil
import subprocess
import sys

import config

_LIVE_NAMES = ("wallpaper_live_a.png", "wallpaper_live_b.png")


def _macos_live_path(current: str | None) -> str:
    """macOS는 같은 경로의 이미지를 다시 지정하면 갱신을 무시할 수 있으므로
    두 파일명을 번갈아 사용한다."""
    a, b = (os.path.join(config.app_dir(), name) for name in _LIVE_NAMES)
    if current and os.path.basename(current) == _LIVE_NAMES[0]:
        return b
    return a


def _set_macos_wallpaper_appkit(png_path: str) -> tuple[bool, str]:
    try:
        from AppKit import NSScreen, NSWorkspace
        from Foundation import NSURL
    except Exception as e:
        return False, f"AppKit import 실패: {e!r}"

    try:
        url = NSURL.fileURLWithPath_(os.path.abspath(png_path))
        workspace = NSWorkspace.sharedWorkspace()
        screens = list(NSScreen.screens() or [])
        if not screens:
            return False, "화면 정보를 찾지 못함"
        failures = []
        for screen in screens:
            result = workspace.setDesktopImageURL_forScreen_options_error_(url, screen, {}, None)
            ok = result[0] if isinstance(result, tuple) else bool(result)
            if not ok:
                failures.append(str(screen))
        if failures:
            return False, f"일부 화면 적용 실패: {', '.join(failures)}"
        return True, ""
    except Exception as e:
        return False, f"AppKit 적용 실패: {e!r}"


def _set_macos_wallpaper_osascript(png_path: str) -> tuple[bool, str]:
    script = """
    on run argv
        set imagePath to POSIX file (item 1 of argv)
        tell application "System Events"
            set picture of every desktop to imagePath
        end tell
    end run
    """
    try:
        subprocess.run(["osascript", "-e", script, png_path], check=True,
                       capture_output=True, text=True, timeout=15)
        return True, ""
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        err = getattr(e, "stderr", "") or str(e)
        return False, err


def set_wallpaper(png_path: str) -> bool:
    if not png_path or not os.path.exists(png_path):
        config.log(f"바탕화면 적용 실패: 파일 없음 {png_path}")
        return False

    if sys.platform == "win32":
        import ctypes
        from PIL import Image
        # SystemParametersInfo works most reliably with BMP paths.
        bmp_path = os.path.splitext(png_path)[0] + ".bmp"
        Image.open(png_path).convert("RGB").save(bmp_path)
        SPI_SETDESKWALLPAPER, SPIF_UPDATE_AND_SEND = 20, 3
        ok = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, bmp_path, SPIF_UPDATE_AND_SEND
        )
        config.log(f"바탕화면 적용 {'성공' if ok else '실패'}: {bmp_path}")
        return bool(ok)

    if sys.platform == "darwin":
        try:
            live_path = _macos_live_path(config.load_cache().get("wallpaper_live"))
            shutil.copyfile(png_path, live_path)
            png_path = live_path
        except OSError as e:
            config.log(f"바탕화면 사본 생성 실패, 원본 경로로 적용: {e!r}")
        ok, err = _set_macos_wallpaper_appkit(png_path)
        if ok:
            config.save_cache_entry("wallpaper_live", png_path)
            config.log(f"macOS 바탕화면 적용 성공: {png_path}")
            return True
        config.log(f"macOS AppKit 바탕화면 적용 실패, AppleScript 재시도: {err}")
        ok, script_err = _set_macos_wallpaper_osascript(png_path)
        if ok:
            config.save_cache_entry("wallpaper_live", png_path)
            config.log(f"macOS 바탕화면 적용 성공(AppleScript): {png_path}")
            return True
        config.log(f"macOS 바탕화면 적용 실패: AppKit={err}; AppleScript={script_err}")
        return False

    config.log(f"(개발 모드) 바탕화면 미적용, 이미지: {png_path}")
    return False
