# -*- coding: utf-8 -*-
"""UI 스트레스 테스트: 실제 Tk 창을 띄워 내비게이션/테마/리사이즈/연타/에디터 입력을 폭격한다.

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

import customtkinter as ctk

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
    out = {}
    for b in find_widgets(root, ctk.CTkButton):
        try:
            out[str(b.cget("text"))] = b
        except Exception:
            pass
    return out


def var_texts(root):
    """textvariable 이 걸린 라벨들의 현재 값 모음 (상태 문자열 확인용)."""
    values = []
    for label in find_widgets(root, ctk.CTkLabel):
        try:
            name = label.cget("textvariable")
        except Exception:
            continue
        if not name:
            continue
        try:
            values.append(str(root.getvar(str(name))))
        except tk.TclError:
            pass
    return values


def status_of(root):
    return " | ".join(var_texts(root))


def has_status(root, *needles):
    text = status_of(root)
    return any(n in text for n in needles)


def enabled(button):
    return str(button.cget("state")) == "normal"


def mapped_pages(root):
    """지금 보이는 페이지 인덱스 목록 (0=홈, 1=꾸미기, 2=설정).

    사이드바도 CTkFrame 자식 3개를 갖고 있어서, 나중에 만들어진 content 를 쓴다.
    """
    candidates = [w for w in root.winfo_children()
                  if isinstance(w, ctk.CTkFrame)
                  and len([k for k in w.winfo_children() if isinstance(k, ctk.CTkFrame)]) == 3]
    if not candidates:
        return []
    pages = [k for k in candidates[-1].winfo_children() if isinstance(k, ctk.CTkFrame)]
    return [i for i, p in enumerate(pages) if p.winfo_ismapped()]


def script(root):
    """제너레이터: yield (설명, 조건함수, 타임아웃초) 로 대기, 그 외엔 즉시 실행."""

    # 1. 시작 자동 새로고침이 끝날 때까지 대기
    yield ("startup auto refresh",
           lambda: has_status(root, "불러옴", "오프라인", "실패"), 25)
    check(not has_status(root, "실패"), f"startup refresh clean (status={status_of(root)!r})")

    # 2. 미리보기 이미지가 CTkLabel 에 붙었는지
    def preview_labels():
        return [l for l in find_widgets(root, ctk.CTkLabel)
                if getattr(l, "_image", None) is not None]
    yield ("preview image rendered", lambda: len(preview_labels()) >= 1, 20)
    check(len(preview_labels()) >= 1, "preview image rendered into label")

    # 3. 내비게이션 왕복 — 설정 → 홈
    btns = buttons_by_text(root)
    check("홈" in btns and "꾸미기" in btns and "설정" in btns, "sidebar has three nav items")
    check(mapped_pages(root) == [0], f"only home visible at startup (got {mapped_pages(root)})")
    btns["설정"].invoke()
    yield ("settings page", lambda: mapped_pages(root) == [2], 3)
    check(mapped_pages(root) == [2],
          f"only settings visible after nav (got {mapped_pages(root)})")
    check(any(isinstance(w, ctk.CTkSwitch) for w in find_widgets(root, ctk.CTkSwitch)),
          "settings page shows the autostart switch")
    seg_buttons = find_widgets(root, ctk.CTkSegmentedButton)
    check(len(seg_buttons) >= 1, "settings page has the wallpaper theme picker")

    # 4. 테마 스팸 — 사용자 클릭과 같은 경로(set + command)로 15회
    theme_seg = seg_buttons[0]
    theme_values = list(theme_seg.cget("values"))
    for i in range(15):
        value = theme_values[i % len(theme_values)]
        theme_seg.set(value)
        theme_seg._command(value)
        yield ("theme settle", lambda: True, 1)
    theme_seg.set(theme_values[0])
    theme_seg._command(theme_values[0])
    check(True, "15 rapid theme switches survived")

    # 4b. 자동 갱신 주기 설정이 존재하고 저장되는지
    menus = find_widgets(root, ctk.CTkOptionMenu)
    check(len(menus) >= 2, f"settings has class + interval option menus (got {len(menus)})")
    interval_menu = menus[-1]
    interval_values = list(interval_menu.cget("values"))
    check(set(interval_values) == set(_config.REFRESH_INTERVAL_LABELS.values()),
          f"interval picker offers all intervals ({interval_values})")
    interval_menu.set("30분")
    buttons_by_text(root)["설정 저장"].invoke()
    yield ("settings saved", lambda: has_status(root, "설정 저장"), 10)
    check(_config.load_config()["refresh_interval_min"] == 30,
          f"interval persisted to config (got {_config.load_config()['refresh_interval_min']})")

    btns = buttons_by_text(root)
    btns["홈"].invoke()
    yield ("back home", lambda: mapped_pages(root) == [0], 3)
    check(mapped_pages(root) == [0], f"only home visible again (got {mapped_pages(root)})")

    # 5. 리사이즈 스팸
    for w, h in ((1000, 660), (1400, 900), (1001, 661), (1200, 760)) * 2:
        root.geometry(f"{w}x{h}")
        yield ("resize settle", lambda: True, 0.05)
    check(True, "8 rapid resizes survived")

    # 6. 재생성 연타 — busy 중 클릭은 무시되고 버튼은 비활성화돼야 한다
    btns = buttons_by_text(root)
    regen = btns["다시 만들기"]
    regen.invoke()
    yield ("busy state engages", lambda: not enabled(regen), 10)
    check(not enabled(regen), "buttons disabled while busy")
    for _ in range(10):
        regen.invoke()  # 연타 (무시되어야 함)
    yield ("regen completes", lambda: has_status(root, "완료", "실패"), 30)
    check(has_status(root, "완료"), f"regenerate after click-spam (status={status_of(root)!r})")
    check(enabled(regen), "buttons re-enabled after work")

    # 7. 에디터 열기 (사이드바에서 바로 갈 수 있어야 한다)
    buttons_by_text(root)["꾸미기"].invoke()
    yield ("editor visible", lambda: any(
        isinstance(o, CustomWallpaperEditor) and o.frame.winfo_ismapped()
        for o in gc.get_objects() if isinstance(o, CustomWallpaperEditor)), 15)
    editor = next(o for o in gc.get_objects() if isinstance(o, CustomWallpaperEditor))
    check(editor.frame.winfo_ismapped(), "editor opened from sidebar")
    yield ("editor preview", lambda: editor.image_item is not None, 20)
    check(editor.image_item is not None, "editor preview image rendered")

    # 8. 펜 폭격: 150 모션 이벤트
    editor.set_mode("pen")
    cv = editor.canvas
    cv.event_generate("<ButtonPress-1>", x=200, y=150)
    for i in range(150):
        cv.event_generate("<B1-Motion>", x=200 + (i % 60) * 5, y=150 + (i % 40) * 4)
        if i % 25 == 0:
            yield ("pen breathing", lambda: True, 0.02)
    cv.event_generate("<ButtonRelease-1>", x=500, y=300)
    check(editor.drawing.getchannel("A").getbbox() is not None, "pen strokes landed on drawing layer")

    # 9. 모드 전환 + 지우개 (세그먼트 버튼 상태도 따라와야 한다)
    editor.set_mode("eraser")
    check(editor.mode_button.get() == "지우개", "segmented button reflects eraser mode")
    cv.event_generate("<ButtonPress-1>", x=210, y=160)
    for i in range(40):
        cv.event_generate("<B1-Motion>", x=210 + i * 7, y=160 + i * 3)
    cv.event_generate("<ButtonRelease-1>", x=480, y=280)
    check(True, "eraser strokes survived")

    # 10. 패널 드래그 + 핸들 리사이즈
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

    # 11. 스티커 추가/선택/회전/삭제
    sticker_count = len(editor.custom.get("stickers", []))
    editor.custom.setdefault("stickers", []).append(
        {"path": _config.WALLPAPER_PATH, "rect": [0.4, 0.4, 0.15, 0.15], "angle": 0})
    editor.selected = ("sticker", sticker_count)
    editor.update_overlays()
    editor.rotate_selected_sticker(15)
    check(editor.custom["stickers"][sticker_count]["angle"] == 15, "selected sticker rotated")

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
    check(editor.drag is not None and editor.drag["type"] == "rotate",
          "drag mode is rotate after press on handle")
    cv.event_generate("<B1-Motion>", x=int(rx + 50), y=int(ry + 20))
    angle_after = editor.custom["stickers"][sticker_count]["angle"]
    check(angle_after != angle_before,
          f"dragged rotate handle changed sticker angle from {angle_before} to {angle_after}")
    cv.event_generate("<ButtonRelease-1>", x=int(rx + 50), y=int(ry + 20))

    editor.delete_selected_sticker()
    check(len(editor.custom.get("stickers", [])) == sticker_count, "sticker deleted via method")
    editor.delete_selected_sticker()  # 스티커 미선택 → 안내 메시지, 크래시 없어야 함
    check(has_status(root, "선택", "삭제"), "delete without selection is graceful")

    # 12. 공유 시간표 대화상자 — 에디터 쪽에서 열기
    editor.edit_timetable()
    yield ("editor timetable dialog", lambda: any(
        "시간표" in str(c.title()) for c in root.winfo_children()
        if isinstance(c, tk.Toplevel)), 8)
    dialog = next((c for c in root.winfo_children()
                   if isinstance(c, tk.Toplevel) and "시간표" in str(c.title())), None)
    check(dialog is not None, "timetable editor dialog popped up from editor")
    if dialog:
        entries = find_widgets(dialog, ctk.CTkEntry)
        check(len(entries) >= 3, f"dialog has entry widgets (got {len(entries)})")
        entries[1].delete(0, "end")
        entries[1].insert(0, "파이썬")
        ok = next((b for b in find_widgets(dialog, ctk.CTkButton)
                   if str(b.cget("text")) == "확인"), None)
        check(ok is not None, "confirm button found in dialog")
        if ok:
            ok.invoke()
        yield ("dialog closed", lambda: not dialog.winfo_exists(), 5)
        cached = _config.load_cache().get("timetable")
        check(cached is not None, "timetable cached after edit")
        if cached:
            check(cached.get("_edited") is True, "timetable marked _edited")
            check(any(p.get("subject") == "파이썬" for p in cached.get("periods", [])),
                  "edited subject saved to cache")

    # 13. 홈으로 돌아오기 — 에디터가 확실히 감춰져야 한다
    buttons_by_text(root)["홈"].invoke()
    yield ("editor hidden", lambda: not editor.frame.winfo_ismapped(), 8)
    check(not editor.frame.winfo_ismapped(), "editor hidden after returning home")
    check(mapped_pages(root) == [0], f"only home visible after editor (got {mapped_pages(root)})")

    # 14. 데이터 패널이 읽기 전용인지
    boxes = find_widgets(root, ctk.CTkTextbox)
    check(len(boxes) >= 2, f"home has timetable + meal textboxes (got {len(boxes)})")
    check(all(str(b.cget("state")) == "disabled" for b in boxes),
          "data panels read-only but selectable")

    print(f"\nmax event-loop stall: {max_stall['value']*1000:.0f}ms")
    check(max_stall["value"] < 0.6,
          f"event loop never stalled badly ({max_stall['value']*1000:.0f}ms)")


def main():
    def driver():
        root = tk._default_root
        if root is None:
            return
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
                import traceback
                traceback.print_exc()
                failures.append(f"driver crashed: {e!r}")
                try:
                    root.destroy()
                except tk.TclError:
                    pass

        root.after(400, tick)

    # show_app이 mainloop을 돌리기 전에 드라이버를 심는다 (CTk가 mainloop을 재정의한다)
    original_mainloop = ctk.CTk.mainloop

    def patched_mainloop(self, *a, **k):
        driver()
        original_mainloop(self, *a, **k)

    ctk.CTk.mainloop = patched_mainloop
    try:
        app_ui.show_app()
    finally:
        ctk.CTk.mainloop = original_mainloop

    print(f"\n{'FAILED' if failures else 'ALL UI STRESS TESTS PASSED'}"
          + (f" ({len(failures)} failures)" if failures else ""))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
