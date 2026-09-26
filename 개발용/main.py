# -*- coding: utf-8 -*-
"""하태욱 프로그램 — 인천과학고 급식·시간표 바탕화면 자동 갱신.

흐름: 중복 실행 방지 → (최초 실행 시 설정창) → 인터넷 대기 → fetch → 렌더 →
바탕화면 적용 → 트레이 상주 (지금 갱신 / 설정 / 종료).
갱신은 부팅 시 1회가 기본이며 주기적 갱신은 하지 않는다.
"""
import os
import argparse
import subprocess
import sys
import threading
import time

# PyInstaller --noconsole 으로 빌드 시 sys.stdout/stderr 이 None 이 되어
# 라이브러리 경고 출력 등에서 AttributeError 가 발생하는 문제를 방지한다.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import requests

import autostart
import config
import fetch_meal
import fetch_timetable
import render
import settings_ui
import updater
import wallpaper

MUTEX_NAME = "hataewook-program-mutex"
INTERNET_RETRY_SEC = 10
INTERNET_MAX_WAIT_SEC = 300

# 예외 발생 시 콘솔 대신 로그 파일에 기록 (PyInstaller --noconsole 호환)
def _excepthook(exc_type, exc_value, exc_tb):
    import traceback
    err = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    config.log(f"Unhandled exception:\n{err}")

sys.excepthook = _excepthook

_mutex_handle = None


def already_running() -> bool:
    if sys.platform != "win32":
        return False
    import ctypes
    global _mutex_handle
    _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    return ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS


def wait_for_internet() -> bool:
    deadline = time.monotonic() + INTERNET_MAX_WAIT_SEC
    while time.monotonic() < deadline:
        try:
            requests.head("https://open.neis.go.kr", timeout=5)
            return True
        except requests.RequestException:
            config.log("인터넷 연결 대기 중...")
            time.sleep(INTERNET_RETRY_SEC)
    return False


_update_lock = threading.Lock()


def update(apply_wallpaper: bool = True) -> str | None:
    if not _update_lock.acquire(blocking=False):
        return None  # 이미 갱신 중
    try:
        cfg = config.load_config()
        config.log(f"갱신 시작 (반: {cfg.get('grade')}-{cfg.get('class_num')})")
        meals = fetch_meal.fetch_meals(cfg)
        timetable = fetch_timetable.fetch_today(cfg)
        path = render.render_wallpaper(meals, timetable, cfg)
        if apply_wallpaper:
            if not wallpaper.set_wallpaper(path):
                config.log(f"바탕화면 적용 없이 이미지 생성까지만 완료: {path}")
        else:
            config.log(f"이미지 생성까지만 완료: {path}")
        config.log("갱신 완료")
        return path
    except Exception as e:
        config.log(f"갱신 실패: {e!r}")
        return None
    finally:
        _update_lock.release()


def make_tray_icon():
    from PIL import Image, ImageDraw, ImageFont
    tray_themes = {
        "black_on_white": ((255, 255, 255), (0, 0, 0)),
        "white_on_black": ((0, 0, 0), (255, 255, 255)),
        "crayon_sketch": ((253, 251, 247), (44, 44, 44)),
        "cyber_terminal": ((10, 16, 13), (0, 255, 102)),
    }
    cfg = config.load_config()
    bg, fg = tray_themes.get(cfg.get("ui_theme"), tray_themes[config.DEFAULT_UI_THEME])
    img = Image.new("RGB", (64, 64), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([2, 2, 61, 61], outline=fg, width=3)
    try:
        font = ImageFont.truetype(render.FONT_PATH, 32)
        d.text((12, 14), ">_", font=font, fill=fg)
    except OSError:
        d.text((20, 24), ">", fill=fg)
    return img


def _settings_command() -> list:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--ui"]
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    return [sys.executable, script, "--ui"]


def run_tray() -> None:
    import pystray

    def on_update(icon, item):
        threading.Thread(target=update, daemon=True).start()

    def on_settings(icon, item):
        # Tk는 메인 스레드에서만 안전하므로 설정 창은 별도 프로세스로 연다.
        # (트레이 스레드에서 tk.Tk()를 만들면 macOS에서 회색 화면으로 멈춘다)
        def open_and_apply():
            try:
                subprocess.run(_settings_command(), check=False)
            except OSError as e:
                config.log(f"설정 창 실행 실패: {e!r}")
                return
            icon.icon = make_tray_icon()
            update()
        threading.Thread(target=open_and_apply, daemon=True).start()

    def on_quit(icon, item):
        icon.stop()

    icon = pystray.Icon(
        "hataewook",
        make_tray_icon(),
        "하태욱 프로그램 — 인천과학고",
        menu=pystray.Menu(
            pystray.MenuItem("지금 갱신", on_update),
            pystray.MenuItem("설정", on_settings),
            pystray.MenuItem("종료", on_quit),
        ),
    )
    icon.run()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="하태욱 프로그램")
    parser.add_argument("--render-only", action="store_true",
                        help="급식/시간표를 가져와 wallpaper.png만 만들고 바탕화면 적용과 트레이 실행은 하지 않습니다.")
    parser.add_argument("--once", action="store_true",
                        help="한 번 갱신한 뒤 트레이에 상주하지 않고 종료합니다.")
    parser.add_argument("--no-wallpaper", action="store_true",
                        help="이미지는 만들지만 OS 바탕화면으로 적용하지 않습니다.")
    parser.add_argument("--ui", action="store_true",
                        help="전체 애플리케이션 UI를 열고 종료합니다.")
    parser.add_argument("--background", action="store_true",
                        help="UI 없이 갱신 후 트레이에 상주합니다. 자동 실행용입니다.")
    # macOS LaunchServices adds a -psn_* argument when opening .app bundles.
    # Unknown launch metadata should not make the windowed app exit silently.
    args, _unknown = parser.parse_known_args()
    return args


def main() -> None:
    args = _parse_args()
    default_launch = not (args.background or args.render_only or args.once or args.no_wallpaper)

    # 트레이에서 연 설정 창(--ui)은 실행 중인 본체의 업데이트를 방해하지 않는다.
    if args.ui:
        settings_ui.show_settings()
        return

    if default_launch:
        running = already_running()
        if not running and updater.check_and_install(launch_mode="default"):
            return
        settings_ui.show_settings()
        return

    if already_running():
        config.log("이미 실행 중 — 종료")
        return

    # 자동 실행 때 최대 6시간에 한 번 새 GitHub Release를 확인한다.
    if args.background and updater.check_and_install(launch_mode="background"):
        return

    cfg = config.load_config()
    if not cfg.get("configured"):
        if not settings_ui.show_settings():
            config.log("최초 설정이 완료되지 않아 종료")
            return
        cfg = config.load_config()
    if not args.render_only:
        autostart.apply(cfg.get("autostart", True))

    if not wait_for_internet():
        config.log("인터넷 연결 실패 — 캐시로 갱신 시도")
    path = update(apply_wallpaper=not (args.render_only or args.no_wallpaper))
    if args.render_only or args.once:
        if path:
            print(path)
        return
    run_tray()


if __name__ == "__main__":
    main()
