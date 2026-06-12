# -*- coding: utf-8 -*-
"""Full tkinter application UI for configuring, generating, and applying wallpaper."""
import queue
import threading
import tkinter as tk
from tkinter import filedialog

from PIL import ImageTk

import autostart
import config
from custom_editor import CustomWallpaperEditor
import fetch_meal
import fetch_timetable
import render
import wallpaper
from ui_common import PALETTES, ThemedButton, font as _font, theme_key as _theme_key


def format_timetable_lines(timetable):
    date = timetable.get("date", "")
    weekday = timetable.get("weekday_label", "")
    lines = [f"{date} ({weekday})"] if date or weekday else []
    for period in timetable.get("periods", []):
        lines.append(
            f"{period.get('period', '?')}교시 {period.get('time') or '':<5}  "
            f"{period.get('subject') or '-'}  {period.get('teacher') or ''}"
        )
    if not lines or (len(lines) == 1 and not timetable.get("periods")):
        lines.append("시간표 정보 없음")
    return lines


def format_meal_lines(meals):
    lines = []
    for key in ("조식", "중식", "석식"):
        lines.append(f"[{key}]")
        items = meals.get(key) or ["급식 정보 없음"]
        lines.extend(f"  - {item}" for item in items)
    return lines


def show_app(on_save=None) -> bool:
    cfg = config.load_config()
    saved = {"ok": False}
    state = {"busy": False}

    root = tk.Tk()
    root.title("하태욱 프로그램")
    root.geometry("1120x720")
    root.minsize(980, 620)

    class_var = tk.StringVar(value=f"{cfg.get('grade', 1)}-{cfg.get('class_num', 1)}")
    theme_labels = {label: key for key, label in config.UI_THEMES.items()}
    theme_var = tk.StringVar(value=config.UI_THEMES[_theme_key(cfg.get("ui_theme", config.DEFAULT_UI_THEME))])
    bg_var = tk.StringVar(value=cfg.get("background_image", ""))
    auto_var = tk.BooleanVar(value=cfg.get("autostart", True))
    status_var = tk.StringVar(value="준비됨")

    widgets = []
    buttons = []
    wallpaper_buttons = []
    option_menus = []
    editor_holder = {}
    ui_queue = queue.Queue()

    def palette():
        return PALETTES[theme_labels.get(theme_var.get(), config.DEFAULT_UI_THEME)]

    def remember(widget, kind="normal"):
        widgets.append((widget, kind))
        return widget

    def section(parent, title):
        p = palette()
        frame = tk.Frame(parent, bg=p["panel"], highlightthickness=1, highlightbackground=p["border"])
        label = tk.Label(frame, text=f"[ {title} ]", font=_font(13, "bold"), anchor="w")
        label.pack(fill="x", padx=10, pady=(8, 2))
        remember(frame, "panel")
        remember(label, "label")
        return frame

    def style_all():
        p = palette()
        root.configure(bg=p["bg"])
        for widget, kind in widgets:
            if not widget.winfo_exists():
                continue
            if kind == "panel":
                widget.configure(bg=p["panel"], highlightbackground=p["border"])
            elif kind == "canvas":
                widget.configure(bg=p["panel_alt"], highlightbackground=p["border"])
            elif kind == "alt":
                widget.configure(bg=p["panel_alt"], fg=p["fg"])
                if isinstance(widget, tk.Text):
                    widget.configure(
                        insertbackground=p["fg"],
                        selectbackground=p["border"],
                        selectforeground=p["button_fg"],
                        highlightbackground=p["border"],
                        highlightcolor=p["border"],
                    )
            elif kind == "dim":
                widget.configure(bg=p["panel"], fg=p["dim"])
            else:
                widget.configure(bg=p["panel"], fg=p["fg"])
        for button in buttons:
            if button.winfo_exists():
                button.set_palette(p)
        for menu in option_menus:
            if menu.winfo_exists():
                menu.configure(bg=p["panel"], fg=p["fg"], activebackground=p["accent"],
                               activeforeground=p["button_fg"], highlightbackground=p["border"])
                menu["menu"].configure(bg=p["panel"], fg=p["fg"])

    def ui_after(callback, *args):
        ui_queue.put((callback, args))

    def pump_ui_queue():
        try:
            while True:
                callback, args = ui_queue.get_nowait()
                callback(*args)
        except queue.Empty:
            pass
        except (RuntimeError, tk.TclError):
            return
        try:
            root.after(25, pump_ui_queue)
        except (RuntimeError, tk.TclError):
            return

    def current_config():
        """저장하지 않고 현재 UI 상태를 설정 dict로 만든다 (미리보기용)."""
        latest = config.load_config()
        grade, cls = class_var.get().split("-")
        latest["grade"], latest["class_num"] = int(grade), int(cls)
        latest["background_image"] = bg_var.get()
        latest["ui_theme"] = theme_labels.get(theme_var.get(), config.DEFAULT_UI_THEME)
        latest["autostart"] = auto_var.get()
        return latest

    def collect_config():
        latest = current_config()
        latest["configured"] = True
        cfg.clear()
        cfg.update(latest)
        config.save_config(cfg)
        saved["ok"] = True
        return dict(cfg)

    def apply_autostart_async(enabled):
        def run():
            try:
                autostart.apply(enabled)
                ui_after(status_var.set, "설정 저장됨")
            except Exception as e:
                config.log(f"자동 실행 설정 실패: {e!r}")
                ui_after(status_var.set, "설정 저장됨, 자동 실행 설정 실패")
        threading.Thread(target=run, daemon=True).start()

    def save_config():
        current = collect_config()
        if on_save:
            on_save(current)
        apply_autostart_async(current["autostart"])
        status_var.set("설정 저장됨")

    def set_buttons_enabled(targets, enabled):
        for button in targets:
            if button.winfo_exists():
                button.set_enabled(enabled)

    def set_busy(value, text=None, scope="all"):
        if scope == "all":
            state["busy"] = value
        if text:
            status_var.set(text)
        targets = buttons if scope == "all" else wallpaper_buttons
        set_buttons_enabled(targets, not value)

    def show_main():
        if "editor" in editor_holder:
            editor_holder["editor"].hide()
        outer.pack(fill="both", expand=True, padx=18, pady=18)
        status_var.set("준비됨")
        request_preview(50)  # 에디터에서 레이아웃이 바뀌었을 수 있다

    def show_custom_editor():
        if state["busy"]:
            return
        collect_config()
        outer.pack_forget()
        if "editor" not in editor_holder:
            editor_holder["editor"] = CustomWallpaperEditor(
                root, show_main, status_var.set, on_regenerate=lambda: worker(True)
            )
        editor_holder["editor"].show()

    def edit_teacher_names():
        p = palette()
        dialog = tk.Toplevel(root)
        dialog.title("교사 명단")
        dialog.geometry("380x460")
        dialog.configure(bg=p["bg"])
        dialog.transient(root)
        info = tk.Label(
            dialog,
            text="컴시간알리미는 교사 이름을 '김완*'처럼 가려서 보냅니다.\n"
                 "전체 이름을 한 줄에 하나씩 입력해 두면, 이름이 정확히\n"
                 "한 명과 일치할 때 자동으로 전체 이름으로 표시합니다.",
            font=_font(11), justify="left", anchor="w", bg=p["bg"], fg=p["dim"])
        info.pack(fill="x", padx=14, pady=(12, 8))
        roster_text = tk.Text(dialog, font=_font(12), borderwidth=0, highlightthickness=1,
                              bg=p["panel_alt"], fg=p["fg"], insertbackground=p["fg"],
                              highlightbackground=p["border"], highlightcolor=p["border"])
        roster_text.pack(fill="both", expand=True, padx=14)
        roster_text.insert("1.0", "\n".join(config.load_config().get("teacher_names", [])))

        def save_roster():
            names = []
            for line in roster_text.get("1.0", "end").splitlines():
                name = line.strip()
                if name and name not in names:
                    names.append(name)
            latest = config.load_config()
            latest["teacher_names"] = names
            config.save_config(latest)
            cfg.clear()
            cfg.update(latest)
            dialog.destroy()
            status_var.set(f"교사 명단 저장됨 ({len(names)}명)")
            fill_cached_data()
            request_preview()

        footer = tk.Frame(dialog, bg=p["bg"])
        footer.pack(fill="x", padx=14, pady=10)
        for text, cmd, side in (("저장", save_roster, "right"), ("닫기", dialog.destroy, "right")):
            b = ThemedButton(footer, text, cmd, font=_font(12, "bold"))
            b.set_palette(p)
            b.pack(side=side, padx=(8, 0))
        roster_text.focus_set()

    def choose_background():
        path = filedialog.askopenfilename(
            title="배경 이미지 선택",
            filetypes=[("이미지", "*.png *.jpg *.jpeg *.bmp"), ("모든 파일", "*.*")],
        )
        if path:
            bg_var.set(path)
            request_preview()

    def clear_background():
        bg_var.set("")
        request_preview()

    def _set_text(widget, content):
        """읽기 전용 Text 갱신 (disabled 상태라 선택/복사는 가능)."""
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.mark_set("insert", "1.0")
        widget.configure(state="disabled")

    def fill_data(meals, timetable):
        _set_text(timetable_text, "\n".join(format_timetable_lines(timetable)))
        _set_text(meal_text, "\n".join(format_meal_lines(meals)))

    def cached_display_data():
        """캐시 데이터를 읽어 교사 명단 매칭까지 적용한다 (표시/미리보기 공용)."""
        import copy as _copy
        cache = config.load_cache()
        meals = dict(cache.get("meal", {}).get("data") or {})
        timetable = _copy.deepcopy(cache.get("timetable") or {})
        if not timetable:
            timetable = {"date": "", "weekday_label": "", "periods": []}
        fetch_timetable._resolve_teachers(timetable, config.load_config().get("teacher_names") or [])
        return meals, timetable

    def fill_cached_data():
        meals, timetable = cached_display_data()
        fill_data(meals, timetable)

    def worker(apply=False):
        if state["busy"]:
            return
        action_label = "배경화면 적용" if apply else "배경화면 재생성"
        set_busy(True, f"{action_label} 중...")
        current = collect_config()

        def run():
            try:
                meals = fetch_meal.fetch_meals(current)
                timetable = fetch_timetable.fetch_today(current)
                path = render.render_wallpaper(meals, timetable, current)
                is_offline = bool(meals.get("_cached") or timetable.get("_cached"))
                offline_suffix = " (오프라인: 캐시 데이터)" if is_offline else ""

                if apply:
                    def apply_on_main():
                        try:
                            result = wallpaper.apply_wallpaper(path)
                            if result["ok"]:
                                detail = f" ({result['method']}"
                                if result.get("screens"):
                                    detail += f", {result['screens']}개 화면"
                                detail += ")"
                                message = f"배경화면 적용 완료{detail}{offline_suffix}"
                            else:
                                message = f"이미지 저장 완료, OS 적용 실패: {result.get('detail') or result.get('path')}{offline_suffix}"
                            status_var.set(message)
                        except Exception as e:
                            status_var.set(f"배경화면 적용 실패: {e}")
                        finally:
                            set_busy(False)
                    ui_after(apply_on_main)
                else:
                    message = f"배경화면 재생성 완료: {path}{offline_suffix}"
                    ui_after(status_var.set, message)
                    ui_after(set_busy, False)

                ui_after(fill_data, meals, timetable)
                ui_after(path_var.set, path)
                ui_after(request_preview)
            except Exception as e:
                config.log(f"앱 UI 작업 실패: {e!r}")
                ui_after(status_var.set, f"{action_label} 실패: {e}")
                ui_after(set_busy, False)
        threading.Thread(target=run, daemon=True).start()

    def refresh_data():
        """시작 시 백그라운드로 급식/시간표만 가져와 화면을 채운다 (배경화면은 건드리지 않음)."""
        if state["busy"]:
            return
        set_busy(True, "급식·시간표 가져오는 중...", scope="wallpaper")
        snapshot = current_config()

        def run():
            try:
                meals = fetch_meal.fetch_meals(snapshot)
                timetable = fetch_timetable.fetch_today(snapshot)
                offline = meals.get("_cached") or timetable.get("_cached")
                ui_after(fill_data, meals, timetable)
                ui_after(status_var.set,
                         "오프라인 — 마지막으로 받은 데이터 표시 중" if offline else "최신 급식·시간표 불러옴")
                ui_after(request_preview)
            except Exception as e:
                config.log(f"데이터 갱신 실패: {e!r}")
                ui_after(status_var.set, f"데이터 갱신 실패: {e}")
            finally:
                ui_after(set_busy, False, None, "wallpaper")
        threading.Thread(target=run, daemon=True).start()

    # ── 바탕화면 라이브 미리보기 (캐시 데이터 + 현재 설정으로 렌더) ──
    preview = {"busy": False, "pending": False, "token": 0, "job": None,
               "photo": None, "item": None}

    def request_preview(delay=200):
        if preview["job"]:
            root.after_cancel(preview["job"])
        preview["job"] = root.after(delay, start_preview)

    def start_preview():
        preview["job"] = None
        if not preview_canvas.winfo_exists():
            return
        if preview["busy"]:
            preview["pending"] = True
            return
        cw = max(1, preview_canvas.winfo_width())
        ch = max(1, preview_canvas.winfo_height())
        pw = cw - 16
        ph = round(pw * 9 / 16)
        if ph > ch - 16:
            ph = ch - 16
            pw = round(ph * 16 / 9)
        pw, ph = max(64, pw), max(36, ph)
        ox, oy = (cw - pw) // 2, (ch - ph) // 2
        snapshot = current_config()
        meals, timetable = cached_display_data()
        preview["busy"] = True
        preview["token"] += 1
        token = preview["token"]
        size = (pw, ph)

        def run():
            try:
                img = render.render_wallpaper_image(meals, timetable, snapshot, size=size).convert("RGB")
            except Exception as e:
                config.log(f"미리보기 렌더 실패: {e!r}")
                ui_after(finish_preview, token, None, 0, 0)
                return
            ui_after(finish_preview, token, img, ox, oy)
        threading.Thread(target=run, daemon=True).start()

    def finish_preview(token, img, ox, oy):
        preview["busy"] = False
        if preview_canvas.winfo_exists() and img is not None and token == preview["token"]:
            preview["photo"] = ImageTk.PhotoImage(img)
            if preview["item"] is None:
                preview["item"] = preview_canvas.create_image(ox, oy, image=preview["photo"], anchor="nw")
            else:
                preview_canvas.itemconfigure(preview["item"], image=preview["photo"])
                preview_canvas.coords(preview["item"], ox, oy)
        if preview["pending"]:
            preview["pending"] = False
            request_preview(50)

    outer = tk.Frame(root)
    outer.pack(fill="both", expand=True, padx=18, pady=18)
    remember(outer, "panel")

    header = tk.Frame(outer)
    header.pack(fill="x", pady=(0, 12))
    remember(header, "panel")
    title = tk.Label(header, text="하태욱 프로그램", font=_font(22, "bold"), anchor="w")
    title.pack(side="left")
    remember(title, "label")
    custom_button = ThemedButton(header, "사진추가", show_custom_editor, font=_font(12, "bold"))
    custom_button.pack(side="right", padx=(8, 0))
    buttons.append(custom_button)
    status = tk.Label(header, textvariable=status_var, font=_font(12), anchor="e",
                      justify="right", wraplength=520)
    status.pack(side="right")
    remember(status, "dim")

    body = tk.Frame(outer)
    body.pack(fill="both", expand=True)
    remember(body, "panel")

    left = tk.Frame(body)
    left.pack(side="left", fill="y", padx=(0, 14))
    remember(left, "panel")
    right = tk.Frame(body)
    right.pack(side="left", fill="both", expand=True)
    remember(right, "panel")

    control = section(left, "설정")
    control.pack(fill="x")

    def row(parent, text):
        f = tk.Frame(parent)
        f.pack(fill="x", padx=10, pady=6)
        remember(f, "panel")
        l = tk.Label(f, text=text, width=13, anchor="w", font=_font(12))
        l.pack(side="left")
        remember(l, "label")
        return f

    class_row = row(control, "반")
    class_menu = tk.OptionMenu(class_row, class_var, "1-1", "1-2", "1-3", "1-4",
                               command=lambda _: request_preview())
    class_menu.pack(side="left", fill="x", expand=True)
    option_menus.append(class_menu)

    def on_theme_change(_value):
        style_all()
        request_preview()

    theme_row = row(control, "UI 테마")
    theme_menu = tk.OptionMenu(theme_row, theme_var, *theme_labels.keys(), command=on_theme_change)
    theme_menu.pack(side="left", fill="x", expand=True)
    option_menus.append(theme_menu)

    bg_row = row(control, "배경 이미지")
    bg_label = tk.Label(bg_row, textvariable=bg_var, width=24, anchor="w", font=_font(10))
    bg_label.pack(side="left", fill="x", expand=True)
    remember(bg_label, "dim")

    bg_buttons = tk.Frame(control)
    bg_buttons.pack(fill="x", padx=10, pady=(0, 8))
    remember(bg_buttons, "panel")
    for text, cmd in (("찾기", choose_background), ("지움", clear_background)):
        b = ThemedButton(bg_buttons, text, cmd, font=_font(12))
        b.pack(side="left", fill="x", expand=True, padx=(0, 6))
        buttons.append(b)

    teacher_button = ThemedButton(control, "교사 명단 (이름 가림 해제)", edit_teacher_names, font=_font(12))
    teacher_button.pack(fill="x", padx=10, pady=(0, 8))
    buttons.append(teacher_button)

    auto = tk.Checkbutton(control, text="시작 시 자동 실행", variable=auto_var, font=_font(12), anchor="w")
    auto.pack(fill="x", padx=10, pady=(0, 10))
    remember(auto, "label")

    action = section(left, "배경화면")
    action.pack(fill="x", pady=(14, 0))
    for text, cmd in (
        ("설정 저장", save_config),
        ("배경화면 재생성", lambda: worker(False)),
        ("배경화면 적용", lambda: worker(True)),
    ):
        b = ThemedButton(action, text, cmd, font=_font(13, "bold"))
        b.pack(fill="x", padx=10, pady=5)
        buttons.append(b)
        if text != "설정 저장":
            wallpaper_buttons.append(b)

    info = section(left, "파일")
    info.pack(fill="x", pady=(14, 0))
    path_var = tk.StringVar(value=config.WALLPAPER_PATH)
    path_label = tk.Label(info, textvariable=path_var, wraplength=300, justify="left", font=_font(10), anchor="w")
    path_label.pack(fill="x", padx=10, pady=10)
    remember(path_label, "dim")

    preview_panel = section(right, "바탕화면 미리보기")
    preview_panel.pack(fill="both", expand=True, pady=(0, 14))
    preview_canvas = tk.Canvas(preview_panel, highlightthickness=1, borderwidth=0)
    preview_canvas.pack(fill="both", expand=True, padx=10, pady=(4, 10))
    preview_canvas.bind("<Configure>", lambda _e: request_preview(120))
    remember(preview_canvas, "canvas")

    data = tk.Frame(right)
    data.pack(fill="both", expand=True)
    remember(data, "panel")
    tt_panel = section(data, "시간표")
    tt_panel.pack(side="left", fill="both", expand=True, padx=(0, 7))
    meal_panel = section(data, "급식")
    meal_panel.pack(side="left", fill="both", expand=True, padx=(7, 0))

    timetable_text = tk.Text(tt_panel, height=9, font=_font(11), relief="flat", wrap="word",
                             borderwidth=0, state="disabled")
    timetable_text.pack(fill="both", expand=True, padx=10, pady=10)
    remember(timetable_text, "alt")
    meal_text = tk.Text(meal_panel, height=9, font=_font(11), relief="flat", wrap="word",
                        borderwidth=0, state="disabled")
    meal_text.pack(fill="both", expand=True, padx=10, pady=10)
    remember(meal_text, "alt")

    def on_save_shortcut(_event):
        if not state["busy"]:
            save_config()
        return "break"

    root.bind("<Command-s>", on_save_shortcut)
    root.bind("<Control-s>", on_save_shortcut)

    style_all()
    fill_cached_data()
    root.after(25, pump_ui_queue)
    root.after(600, refresh_data)  # 시작하자마자 최신 급식·시간표를 백그라운드로
    root.eval("tk::PlaceWindow . center")
    root.mainloop()
    return saved["ok"]


if __name__ == "__main__":
    show_app()
