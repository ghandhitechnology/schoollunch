# -*- coding: utf-8 -*-
"""UI 스트레스 테스트: 실제 Tk 창을 띄워 테마 변경/리사이즈/연타/에디터 입력을 폭격한다.

실행:  .venv/bin/python test_ui.py
메인 스레드의 after 체인으로 구동하므로 스레드 안전하다.
종료 코드 0 = 통과.
"""
import gc
import math
import os
import shutil
import sys
import tempfile
import time
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config as _config

# 실제 사용자 설정/캐시를 절대 건드리지 않도록 모든 경로를 임시 폴더로 돌린다
_TMP = tempfile.mkdtemp(prefix="hataewook-ui-test-")
_REAL_CACHE = _config.CACHE_PATH
for _name in ("CONFIG_PATH", "CACHE_PATH", "LOG_PATH", "WALLPAPER_PATH", "CUSTOM_DRAWING_PATH"):
    setattr(_config, _name, os.path.join(_TMP, os.path.basename(getattr(_config, _name))))
_config.DEFAULT_CUSTOM_WALLPAPER["drawing_overlay"] = _config.CUSTOM_DRAWING_PATH
_config.DEFAULTS["custom_wallpaper"] = _config.DEFAULT_CUSTOM_WALLPAPER
if os.path.exists(_REAL_CACHE):  # 미리보기에 쓸 샘플 데이터 (읽기 전용 복사)
    shutil.copyfile(_REAL_CACHE, _config.CACHE_PATH)

import app_ui
from custom_editor import CustomWallpaperEditor
from ui_common import ThemedButton

failures = []
max_stall = {"value": 0.0, "last": None}


def check(condition, message):
    if not condition:
        failures.append(message)
        print(f"  FAIL: {message}")
    else:
        print(f"  ok: {message}")


def find_widgets(root, klass):
    found = []
    def walk(w):
        for c in w.winfo_children():
            if isinstance(c, klass):
                found.append(c)
            walk(c)
    walk(root)
    return found


def buttons_by_text(root):
    return {b.cget("text"): b for b in find_widgets(root, ThemedButton)}


def script(root):
    """제너레이터: yield (설명, 조건함수, 타임아웃초) 로 대기, 그 외엔 즉시 실행."""
    status_label = None
    for label in find_widgets(root, tk.Label):
        if str(label.cget("text")) == "준비됨":
            status_label = label
    status = lambda: str(status_label.cget("text")) if status_label else ""

    # 1. 시작 자동 새로고침이 끝날 때까지 대기
    yield ("startup auto refresh", lambda: "불러옴" in status() or "오프라인" in status() or "실패" in status(), 25)
    check("실패" not in status(), f"startup refresh clean (status={status()!r})")

    # 2. 미리보기 캔버스에 이미지가 떴는지
    canvases = find_widgets(root, tk.Canvas)
    check(len(canvases) == 1, f"main view has one preview canvas (got {len(canvases)})")
    preview_canvas = canvases[0]
    yield ("preview image rendered", lambda: len(preview_canvas.find_all()) >= 1, 15)
    check(len(preview_canvas.find_all()) >= 1, "preview canvas shows an image")

    # 3. 테마 스팸 (OptionMenu 항목을 직접 invoke → command까지 실행)
    menus = find_widgets(root, tk.OptionMenu)
    theme_menu = menus[1]["menu"]
    for i in range(15):
        theme_menu.invoke(i % 3)
        yield ("theme settle", lambda: True, 1)
    theme_menu.invoke(0)
    check(True, "15 rapid theme switches survived")

    # 4. 리사이즈 스팸
    for w, h in ((1000, 640), (1400, 900), (981, 621), (1200, 760)) * 2:
        root.geometry(f"{w}x{h}")
        yield ("resize settle", lambda: True, 0.05)
    check(True, "8 rapid resizes survived")

    # 5. 재생성 연타 — busy 중 클릭은 무시되고 버튼은 비활성화돼야 한다
    btns = buttons_by_text(root)
    regen = btns["배경화면 재생성"]
    regen._command()
    yield ("busy state engages", lambda: not regen._enabled, 5)
    check(not regen._enabled, "buttons disabled while busy")
    for _ in range(10):
        regen._command()  # 연타 (무시되어야 함)
    yield ("regen completes", lambda: "완료" in status() or "실패" in status(), 30)
    check("완료" in status(), f"regenerate after click-spam (status={status()!r})")
    check(regen._enabled, "buttons re-enabled after work")

    # 6. 에디터 열기
    btns["사진추가"]._command()
    yield ("editor visible", lambda: any(
        isinstance(o, CustomWallpaperEditor) and o.frame.winfo_ismapped()
        for o in gc.get_objects() if isinstance(o, CustomWallpaperEditor)), 10)
    editor = next(o for o in gc.get_objects() if isinstance(o, CustomWallpaperEditor))
    check(editor.frame.winfo_ismapped(), "editor opened")
    yield ("editor preview", lambda: editor.image_item is not None, 15)
    check(editor.image_item is not None, "editor preview image rendered")

    # 7. 펜 폭격: 150 모션 이벤트
    editor.set_mode("pen")
    cv = editor.canvas
    cv.event_generate("<ButtonPress-1>", x=200, y=150)
    for i in range(150):
        cv.event_generate("<B1-Motion>", x=200 + (i % 60) * 5, y=150 + (i % 40) * 4)
        if i % 25 == 0:
            yield ("pen breathing", lambda: True, 0.02)
    cv.event_generate("<ButtonRelease-1>", x=500, y=300)
    check(editor.drawing.getchannel("A").getbbox() is not None, "pen strokes landed on drawing layer")

    # 8. 모드 전환 + 지우개
    editor.set_mode("eraser")
    cv.event_generate("<ButtonPress-1>", x=210, y=160)
    for i in range(40):
        cv.event_generate("<B1-Motion>", x=210 + i * 7, y=160 + i * 3)
    cv.event_generate("<ButtonRelease-1>", x=480, y=280)
    check(True, "eraser strokes survived")

    # 9. 패널 드래그 + 핸들 리사이즈
    editor.set_mode("select")
    rect_before = list(editor.custom["layout"]["timetable"])
    x0, y0, x1, y1 = editor.rect_to_canvas(rect_before)
    cx, cy = int((x0 + x1) / 2), int((y0 + y1) / 2)
    cv.event_generate("<ButtonPress-1>", x=cx, y=cy)
    for i in range(12):
        cv.event_generate("<B1-Motion>", x=cx + i * 6, y=cy + i * 4)
    cv.event_generate("<ButtonRelease-1>", x=cx + 66, y=cy + 44)
    yield ("drag preview settle", lambda: True, 0.5)
    check(editor.custom["layout"]["timetable"] != rect_before, "panel drag moved the rect")

    # 10. 스티커 추가/선택/삭제
    sticker_count = len(editor.custom.get("stickers", []))
    editor.custom.setdefault("stickers", []).append(
        {"path": app_ui.config.WALLPAPER_PATH, "rect": [0.4, 0.4, 0.15, 0.15], "angle": 0})
    editor.selected = ("sticker", sticker_count)
    editor.update_overlays()
    editor.rotate_selected_sticker(15)
    check(editor.custom["stickers"][sticker_count]["angle"] == 15, "selected sticker rotated")

    # 10b. 스티커 드래그 회전 테스트
    sticker = editor.custom["stickers"][sticker_count]
    s_rect = list(sticker["rect"])
    angle_before = sticker["angle"]
    x0, y0, x1, y1 = editor.rect_to_canvas(s_rect)
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    rad = math.radians(angle_before)
    dx = 0
    dy = (y0 - 25) - cy
    rx = cx + dx * math.cos(rad) - dy * math.sin(rad)
    ry = cy + dx * math.sin(rad) + dy * math.cos(rad)

    cv.event_generate("<ButtonPress-1>", x=int(rx), y=int(ry))
    check(editor.drag is not None and editor.drag["type"] == "rotate", "drag mode is rotate after press on handle")
    cv.event_generate("<B1-Motion>", x=int(rx + 50), y=int(ry + 20))
    angle_after = editor.custom["stickers"][sticker_count]["angle"]
    check(angle_after != angle_before, f"dragged rotate handle changed sticker angle from {angle_before} to {angle_after}")
    cv.event_generate("<ButtonRelease-1>", x=int(rx + 50), y=int(ry + 20))

    editor.delete_selected_sticker()
    check(len(editor.custom.get("stickers", [])) == sticker_count, "sticker deleted via method")
    editor.delete_selected_sticker()  # 스티커 미선택 → 안내 메시지, 크래시 없어야 함
    check("선택" in status() or "삭제" in status(), "delete without selection is graceful")

    # 10c. 시간표 직접 편집 테스트
    editor.edit_timetable()
    dialog = None
    for child in root.winfo_children():
        if isinstance(child, tk.Toplevel) and "시간표" in child.title():
            dialog = child
            break
    check(dialog is not None, "timetable editor dialog popped up")
    if dialog:
        entries = []
        def find_entries(w):
            for c in w.winfo_children():
                if isinstance(c, tk.Entry):
                    entries.append(c)
                find_entries(c)
        find_entries(dialog)
        check(len(entries) >= 3, "editor dialog has Entry widgets")
        if len(entries) >= 3:
            entries[1].delete(0, "end")
            entries[1].insert(0, "인공지능")

        ok_btn = None
        for child in dialog.winfo_children():
            if isinstance(child, tk.Frame):
                for btn in child.winfo_children():
                    if isinstance(btn, ThemedButton) and btn.cget("text") == "확인":
                        ok_btn = btn
                        break
        check(ok_btn is not None, "OK button found in dialog")
        if ok_btn:
            ok_btn._command()

        cached_tt = _config.load_cache().get("timetable")
        check(cached_tt is not None, "timetable cached after edit")
        if cached_tt:
            check(cached_tt.get("_edited") is True, "timetable marked as _edited")
            check(cached_tt["periods"][0]["subject"] == "인공지능", "edited subject saved to cache")

    # 11. 에디터 키 바인딩이 살아 있는지 + 뒤로가기
    #    (event_generate 키 입력은 OS 포커스가 필요해 백그라운드 실행에서 못 쓴다)
    check(bool(root.bind("<Escape>")), "Esc binding active while editor shown")
    check(bool(root.bind("<Delete>")), "Delete binding active while editor shown")
    editor.back()
    yield ("editor hidden", lambda: not editor.frame.winfo_ismapped(), 5)
    check(not editor.frame.winfo_ismapped(), "back() returns to main view")
    check(not root.bind("<Escape>"), "Esc binding removed after leaving editor")

    # 12. 저장 동작 + 단축키 바인딩
    check(bool(root.bind("<Command-s>")) and bool(root.bind("<Control-s>")),
          "save shortcuts bound")
    buttons_by_text(root)["설정 저장"]._command()
    yield ("save settles", lambda: "저장" in status(), 5)
    check("저장" in status(), f"save button works (status={status()!r})")
    check(app_ui.config.load_config()["configured"], "config persisted")

    # 13. 에디터 재진입 (상태 재사용 경로)
    buttons_by_text(root)["사진추가"]._command()
    yield ("editor reopened", lambda: editor.frame.winfo_ismapped(), 5)
    check(editor.frame.winfo_ismapped(), "editor reopens cleanly")
    editor.back()
    # 13b. 메인 대시보드 시간표 편집 테스트
    buttons_by_text(root)["시간표 편집"]._command()
    dashboard_dialog = None
    for child in root.winfo_children():
        if isinstance(child, tk.Toplevel) and "시간표" in child.title():
            dashboard_dialog = child
            break
    check(dashboard_dialog is not None, "dashboard timetable editor dialog popped up")
    if dashboard_dialog:
        entries = []
        def find_entries(w):
            for c in w.winfo_children():
                if isinstance(c, tk.Entry):
                    entries.append(c)
                find_entries(c)
        find_entries(dashboard_dialog)
        check(len(entries) >= 3, "dashboard editor dialog has Entry widgets")
        if len(entries) >= 3:
            entries[1].delete(0, "end")
            entries[1].insert(0, "파이썬")

        ok_btn = None
        for child in dashboard_dialog.winfo_children():
            if isinstance(child, tk.Frame):
                for btn in child.winfo_children():
                    if isinstance(btn, ThemedButton) and btn.cget("text") == "확인":
                        ok_btn = btn
                        break
        check(ok_btn is not None, "OK button found in dashboard dialog")
        if ok_btn:
            ok_btn._command()

        cached_tt = _config.load_cache().get("timetable")
        check(cached_tt is not None, "timetable cached after dashboard edit")
        if cached_tt:
            check(cached_tt.get("_edited") is True, "timetable marked as _edited after dashboard edit")
            check(cached_tt["periods"][0]["subject"] == "파이썬", "dashboard edited subject saved to cache")

    # 14. 읽기 전용 텍스트가 복사 가능(=disabled) 상태인지
    texts = find_widgets(root, tk.Text)
    check(all(str(t.cget("state")) == "disabled" for t in texts), "data panels read-only but selectable")

    print(f"\nmax event-loop stall: {max_stall['value']*1000:.0f}ms")
    check(max_stall["value"] < 0.6, f"event loop never stalled badly ({max_stall['value']*1000:.0f}ms)")


def main():
    root_holder = {}

    def driver():
        root = tk._default_root
        if root is None:
            return
        root_holder["root"] = root
        gen = script(root)
        state = {"wait": None, "deadline": None, "desc": None}

        def tick():
            now = time.monotonic()
            if max_stall["last"] is not None:
                max_stall["value"] = max(max_stall["value"], now - max_stall["last"] - 0.015)
            max_stall["last"] = now
            try:
                if state["wait"]:
                    if state["wait"]():
                        state["wait"] = None
                    elif now > state["deadline"]:
                        failures.append(f"timeout waiting for: {state['desc']}")
                        print(f"  FAIL: timeout waiting for: {state['desc']}")
                        state["wait"] = None
                    else:
                        root.after(15, tick)
                        return
                step = next(gen, None)
                if step is None:
                    root.destroy()
                    return
                desc, cond, timeout = step
                state.update(wait=cond, deadline=now + timeout, desc=desc)
                root.after(15, tick)
            except tk.TclError:
                pass
            except Exception as e:
                import traceback; traceback.print_exc()
                failures.append(f"driver crashed: {e!r}")
                try:
                    root.destroy()
                except tk.TclError:
                    pass

        root.after(400, tick)

    # show_app이 mainloop을 돌리기 전에 드라이버를 심는다
    original_mainloop = tk.Tk.mainloop

    def patched_mainloop(self, *a, **k):
        driver()
        original_mainloop(self, *a, **k)

    tk.Tk.mainloop = patched_mainloop
    try:
        app_ui.show_app()
    finally:
        tk.Tk.mainloop = original_mainloop

    print(f"\n{'FAILED' if failures else 'ALL UI STRESS TESTS PASSED'}"
          + (f" ({len(failures)} failures)" if failures else ""))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
