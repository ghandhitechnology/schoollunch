# -*- coding: utf-8 -*-
"""앱 창 스크린샷을 ~/Desktop 에 저장한다 (홈 / 꾸미기 / 설정).

실행:  .venv/bin/python screenshots.py

주의: macOS 화면 기록 권한이 필요하다. SSH 로 접속해 실행하면
"could not create image from display" 로 실패한다 — 맥에 직접 붙어서 실행하거나,
시스템 설정 > 개인정보 보호 및 보안 > 화면 기록 에서 터미널을 허용해야 한다.

실제 설정/캐시는 건드리지 않는다 (임시 폴더로 복사해 쓴다).
"""
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

_TMP = tempfile.mkdtemp(prefix="hataewook-shots-")
_REAL = {"cache": config.CACHE_PATH, "config": config.CONFIG_PATH}
for _name in ("CONFIG_PATH", "CACHE_PATH", "LOG_PATH", "WALLPAPER_PATH", "CUSTOM_DRAWING_PATH"):
    setattr(config, _name, os.path.join(_TMP, os.path.basename(getattr(config, _name))))
config.DEFAULT_CUSTOM_WALLPAPER["drawing_overlay"] = config.CUSTOM_DRAWING_PATH
config.DEFAULTS["custom_wallpaper"] = config.DEFAULT_CUSTOM_WALLPAPER
for _src, _dst in ((_REAL["cache"], config.CACHE_PATH), (_REAL["config"], config.CONFIG_PATH)):
    if os.path.exists(_src):
        shutil.copyfile(_src, _dst)

import customtkinter as ctk

import app_ui

OUT_DIR = os.path.expanduser("~/Desktop")
PAGES = [("home", "홈"), ("editor", "꾸미기"), ("settings", "설정")]
SETTLE_MS = 1800  # 미리보기 렌더가 끝날 시간


def find_buttons(root):
    found = {}

    def walk(widget):
        for child in widget.winfo_children():
            if isinstance(child, ctk.CTkButton):
                try:
                    found[str(child.cget("text"))] = child
                except Exception:
                    pass
            walk(child)
    walk(root)
    return found


def capture(root, path):
    root.update_idletasks()
    root.update()
    region = (f"{root.winfo_rootx()},{root.winfo_rooty()},"
              f"{root.winfo_width()},{root.winfo_height()}")
    result = subprocess.run(["screencapture", "-x", "-o", "-R", region, path],
                            capture_output=True, text=True)
    if result.returncode != 0 or not os.path.exists(path):
        err = (result.stderr or "").strip()
        print(f"  실패: {os.path.basename(path)} — {err or 'screencapture 오류'}")
        if "could not create image" in err:
            print("  → 화면 기록 권한이 없습니다. 맥에 직접 붙어서 실행하거나,")
            print("     시스템 설정 > 개인정보 보호 및 보안 > 화면 기록 에서 터미널을 허용하세요.")
        return False
    print(f"  저장: {path}")
    return True


def main():
    original_mainloop = ctk.CTk.mainloop

    def patched(self, *args, **kwargs):
        def run(index=0):
            if index >= len(PAGES):
                self.destroy()
                return
            key, label = PAGES[index]
            buttons = find_buttons(self)
            if label in buttons:
                buttons[label].invoke()
            self.lift()
            self.focus_force()

            def shoot():
                capture(self, os.path.join(OUT_DIR, f"하태욱-{key}.png"))
                run(index + 1)
            self.after(SETTLE_MS, shoot)
        self.after(2500, run)  # 시작 시 급식·시간표 fetch 가 끝나길 기다린다
        original_mainloop(self, *args, **kwargs)

    ctk.CTk.mainloop = patched
    try:
        app_ui.show_app()
    finally:
        ctk.CTk.mainloop = original_mainloop
    print("완료 — ~/Desktop 을 확인하세요.")


if __name__ == "__main__":
    main()
