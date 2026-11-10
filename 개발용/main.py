# -*- coding: utf-8 -*-
"""하태욱 프로그램 — 인천과학고 급식·시간표 바탕화면 자동 갱신.

흐름: 중복 실행 방지 → (최초 실행 시 설정창) → 인터넷 대기 → fetch → 렌더 →
바탕화면 적용 → 트레이 상주 (지금 갱신 / 설정 / 종료).
부팅 시 1회 갱신한 뒤 scheduler.RefreshScheduler 가 백그라운드로 이어받는다:
날짜 변경(자정 넘김), 절전 해제, 설정한 주기, 실패 시 backoff 재시도.
"""
import os
import argparse
import hashlib
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
import scheduler
import settings_ui
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

APPLIED_DIGEST_KEY = "applied_wallpaper_sha256"


def _file_digest(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return ""


def update_ex(apply_wallpaper: bool = True, force: bool = False) -> tuple[str, str | None]:
    """갱신 1회. 반환: (상태, 이미지 경로).

    상태: "ok" | "skipped"(내용 동일해 재적용 생략) | "failed" | "busy"(이미 갱신 중).
    스케줄러가 성공/실패/무시를 구분해야 해서 update() 대신 이쪽을 쓴다.
    """
    if not _update_lock.acquire(blocking=False):
        return "busy", None
    try:
        cfg = config.load_config()
        config.log(f"갱신 시작 (반: {cfg.get('grade')}-{cfg.get('class_num')})")
        meals = fetch_meal.fetch_meals(cfg)
        timetable = fetch_timetable.fetch_today(cfg)
        path = render.render_wallpaper(meals, timetable, cfg)

        if not apply_wallpaper:
            config.log(f"이미지 생성까지만 완료: {path}")
            return "ok", path

        digest = _file_digest(path)
        if not force and digest and digest == config.load_cache().get(APPLIED_DIGEST_KEY):
            # 렌더 결과가 직전과 같으면 다시 적용하지 않는다. macOS 는 적용할 때마다
            # 새 사본을 만들고 화면이 한 번 깜빡인다(wallpaper._macos_live_path 참고).
            # 주기 갱신이 켜져 있어도 조용히 지나가게 하는 부분.
            config.log("바탕화면 내용 변화 없음 — 재적용 생략")
            return "skipped", path

        if wallpaper.set_wallpaper(path):
            if digest:
                config.save_cache_entry(APPLIED_DIGEST_KEY, digest)
        else:
            # 다이제스트를 저장하지 않아 다음 주기에 적용을 다시 시도한다.
            config.log(f"바탕화면 적용 없이 이미지 생성까지만 완료: {path}")
        config.log("갱신 완료")
        return "ok", path
    except Exception as e:
        config.log(f"갱신 실패: {e!r}")
        return "failed", None
    finally:
        _update_lock.release()


def update(apply_wallpaper: bool = True, force: bool = False) -> str | None:
    return update_ex(apply_wallpaper, force)[1]


def _scheduled_refresh():
    """스케줄러 콜백. True=성공, False=실패, None=이미 갱신 중."""
    status, _path = update_ex(apply_wallpaper=True, force=False)
    if status == "busy":
        return None
    return status in ("ok", "skipped")


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


def run_tray(boot_success: bool = True) -> None:
    import pystray

    sched = scheduler.RefreshScheduler(_scheduled_refresh)
    sched.seed(boot_success)  # 부팅 직후 main()이 이미 갱신했으므로 즉시 재갱신하지 않는다

    def refresh_menu(icon):
        try:
            icon.update_menu()
        except Exception:
            pass  # 메뉴 라벨 갱신 실패는 기능에 영향이 없다

    def on_update(icon, item):
        def run():
            # 수동 갱신은 내용이 같아도 강제로 다시 적용한다
            # (사용자가 바탕화면을 직접 바꿨을 수 있다).
            status, _path = update_ex(apply_wallpaper=True, force=True)
            if status != "busy":
                sched.seed(status in ("ok", "skipped"))
            refresh_menu(icon)
        threading.Thread(target=run, daemon=True).start()

    def on_settings(icon, item):
        # Tk는 메인 스레드에서만 안전하므로 설정 창은 별도 프로세스로 연다.
        # (트레이 스레드에서 tk.Tk()를 만들면 macOS에서 회색 화면으로 멈춘다)
        # 설정 창에서 바꾼 자동 갱신 주기는 config.json 을 통해 스케줄러가 매 tick 다시 읽는다.
        def open_and_apply():
            try:
                subprocess.run(_settings_command(), check=False)
            except OSError as e:
                config.log(f"설정 창 실행 실패: {e!r}")
                return
            icon.icon = make_tray_icon()
            status, _path = update_ex(apply_wallpaper=True, force=True)
            if status != "busy":
                sched.seed(status in ("ok", "skipped"))
            refresh_menu(icon)
        threading.Thread(target=open_and_apply, daemon=True).start()

    def on_quit(icon, item):
        sched.stop()
        icon.stop()

    icon = pystray.Icon(
        "hataewook",
        make_tray_icon(),
        "하태욱 프로그램 — 인천과학고",
        menu=pystray.Menu(
            pystray.MenuItem(lambda item: sched.last_success_label(),
                             lambda icon, item: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("지금 갱신", on_update),
            pystray.MenuItem("설정", on_settings),
            pystray.MenuItem("종료", on_quit),
        ),
    )
    sched.start()
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

    # 설정 창은 트레이 인스턴스가 떠 있어도 열 수 있어야 하므로
    # 중복 실행(뮤텍스) 검사보다 먼저 처리한다.
    if args.ui or not (args.background or args.render_only or args.once or args.no_wallpaper):
        settings_ui.show_settings()
        return

    if already_running():
        config.log("이미 실행 중 — 종료")
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
    # 부팅 시에는 항상 강제 적용한다. 사용자가 그동안 바탕화면을 직접 바꿨을 수 있다.
    status, path = update_ex(apply_wallpaper=not (args.render_only or args.no_wallpaper),
                             force=True)
    if args.render_only or args.once:
        if path:
            print(path)
        return
    run_tray(boot_success=status in ("ok", "skipped"))


if __name__ == "__main__":
    main()
