# -*- coding: utf-8 -*-
"""앱 메인 창 — 사이드바 내비게이션(홈 / 꾸미기 / 설정).

창의 외관은 바탕화면 테마와 분리되어 있다(ui_common 참고). 테마를 바꿔도
앱 크롬 색은 그대로고, 미리보기 이미지만 다시 그려진다.

스레드 규칙은 그대로다: 네트워크·렌더는 데몬 스레드에서 하고 Tk 위젯은
ui_after() 큐를 거쳐 메인 스레드에서만 만진다.
"""
import datetime
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

import autostart
import config
import dialogs
import fetch_meal
import fetch_timetable
import render
import wallpaper
from custom_editor import CustomWallpaperEditor
from ui_common import (COLORS, RADIUS, SPACE, TYPE, card, font as _font,
                       init_appearance, mono_font, section_label,
                       theme_key as _theme_key)

NAV_ITEMS = (("home", "홈"), ("editor", "꾸미기"), ("settings", "설정"))
PREVIEW_SUPERSAMPLE = 2  # 고해상도 화면에서 미리보기가 뭉개지지 않도록 크게 렌더한 뒤 축소


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


def last_render_label() -> str:
    """바탕화면 파일의 수정 시각. 트레이(별도 프로세스)가 갱신해도 여기 반영된다."""
    try:
        stamp = datetime.datetime.fromtimestamp(os.path.getmtime(config.WALLPAPER_PATH))
    except OSError:
        return "아직 만든 적 없음"
    if stamp.date() == datetime.date.today():
        return f"마지막 갱신 {stamp:%H:%M}"
    return f"마지막 갱신 {stamp:%m/%d %H:%M}"


def show_app(on_save=None) -> bool:
    cfg = config.load_config()
    saved = {"ok": False}
    state = {"busy": False, "page": None}

    init_appearance()
    root = ctk.CTk()
    root.title("하태욱 프로그램")
    root.geometry("1180x760")
    root.minsize(1000, 660)

    theme_labels = {label: key for key, label in config.UI_THEMES.items()}
    interval_labels = {label: minutes
                       for minutes, label in config.REFRESH_INTERVAL_LABELS.items()}

    class_var = tk.StringVar(value=f"{cfg.get('grade', 1)}-{cfg.get('class_num', 1)}")
    theme_var = tk.StringVar(
        value=config.UI_THEMES[_theme_key(cfg.get("ui_theme", config.DEFAULT_UI_THEME))])
    bg_var = tk.StringVar(value=cfg.get("background_image", ""))
    auto_var = tk.BooleanVar(value=cfg.get("autostart", True))
    interval_var = tk.StringVar(
        value=config.REFRESH_INTERVAL_LABELS[
            config.safe_refresh_interval(cfg.get("refresh_interval_min"))])
    status_var = tk.StringVar(value="준비됨")
    path_var = tk.StringVar(value=config.WALLPAPER_PATH)
    last_var = tk.StringVar(value=last_render_label())

    editor_holder = {}
    pages = {}
    nav_buttons = {}
    action_buttons = []   # 배경화면 생성/적용 — 데이터 새로고침 중에도 잠근다
    all_buttons = []      # 무거운 작업 중 전부 잠근다
    ui_queue = queue.Queue()

    # ── 스레드 → UI 마샬링 (기존 구조 유지) ──
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

    def set_status(text):
        status_var.set(text)

    # ── 설정 읽기/쓰기 ──
    def current_config():
        """저장하지 않고 현재 UI 상태를 설정 dict로 만든다 (미리보기용)."""
        latest = config.load_config()
        grade, cls = class_var.get().split("-")
        latest["grade"], latest["class_num"] = int(grade), int(cls)
        latest["background_image"] = bg_var.get()
        latest["ui_theme"] = theme_labels.get(theme_var.get(), config.DEFAULT_UI_THEME)
        latest["autostart"] = auto_var.get()
        latest["refresh_interval_min"] = interval_labels.get(
            interval_var.get(), config.DEFAULTS["refresh_interval_min"])
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
                ui_after(set_status, "설정 저장됨")
            except Exception as e:
                config.log(f"자동 실행 설정 실패: {e!r}")
                ui_after(set_status, "설정 저장됨, 자동 실행 설정 실패")
        threading.Thread(target=run, daemon=True).start()

    def save_settings():
        current = collect_config()
        if on_save:
            on_save(current)
        apply_autostart_async(current["autostart"])
        set_status("설정 저장됨")

    # ── 잠금 ──
    def set_buttons_enabled(targets, enabled):
        for button in targets:
            if button.winfo_exists():
                button.configure(state="normal" if enabled else "disabled")

    def set_busy(value, text=None, scope="all"):
        if scope == "all":
            state["busy"] = value
        if text:
            set_status(text)
        set_buttons_enabled(all_buttons if scope == "all" else action_buttons, not value)

    # ── 내비게이션 ──
    def show_page(name):
        if state["page"] == name:
            return
        if state["page"] == "editor" and "editor" in editor_holder:
            editor_holder["editor"].hide()
        state["page"] = name
        for frame in pages.values():
            frame.grid_remove()
        pages[name].grid(row=0, column=0, sticky="nsew")
        for key, button in nav_buttons.items():
            active = key == name
            button.configure(
                fg_color=COLORS["nav_active"] if active else "transparent",
                text_color=COLORS["text"] if active else COLORS["text_dim"],
                font=_font(TYPE["body"], "bold" if active else "normal"),
            )
        if name == "editor":
            collect_config()  # 에디터는 저장된 설정을 읽어 렌더한다
            if "editor" not in editor_holder:
                editor_holder["editor"] = CustomWallpaperEditor(
                    pages["editor"], lambda: show_page("home"), set_status,
                    on_regenerate=lambda: worker(True))
            editor_holder["editor"].show()
        elif name == "home":
            set_status("준비됨")
            request_preview(50)  # 에디터에서 레이아웃이 바뀌었을 수 있다

    # ── 데이터 표시 ──
    def _set_text(widget, content):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
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

    # ── 무거운 작업 ──
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
                                message = (f"이미지 저장 완료, OS 적용 실패: "
                                           f"{result.get('detail') or result.get('path')}{offline_suffix}")
                            set_status(message)
                        except Exception as e:
                            set_status(f"배경화면 적용 실패: {e}")
                        finally:
                            set_busy(False)
                            last_var.set(last_render_label())
                    ui_after(apply_on_main)
                else:
                    ui_after(set_status, f"배경화면 재생성 완료{offline_suffix}")
                    ui_after(set_busy, False)
                    ui_after(last_var.set, last_render_label())

                ui_after(fill_data, meals, timetable)
                ui_after(path_var.set, path)
                ui_after(request_preview)
            except Exception as e:
                config.log(f"앱 UI 작업 실패: {e!r}")
                ui_after(set_status, f"{action_label} 실패: {e}")
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
                ui_after(set_status,
                         "오프라인 — 마지막으로 받은 데이터 표시 중" if offline else "최신 급식·시간표 불러옴")
                ui_after(request_preview)
            except Exception as e:
                config.log(f"데이터 갱신 실패: {e!r}")
                ui_after(set_status, f"데이터 갱신 실패: {e}")
            finally:
                ui_after(set_busy, False, None, "wallpaper")
        threading.Thread(target=run, daemon=True).start()

    # ── 바탕화면 라이브 미리보기 (캐시 데이터 + 현재 설정으로 렌더) ──
    preview = {"busy": False, "pending": False, "token": 0, "job": None, "image": None}

    def request_preview(delay=200):
        if preview["job"]:
            try:
                root.after_cancel(preview["job"])
            except (ValueError, tk.TclError):
                pass
        preview["job"] = root.after(delay, start_preview)

    def start_preview():
        preview["job"] = None
        if not preview_holder.winfo_exists():
            return
        if preview["busy"]:
            preview["pending"] = True
            return
        cw = max(1, preview_holder.winfo_width())
        ch = max(1, preview_holder.winfo_height())
        pw = cw - 2 * SPACE["sm"]
        ph = round(pw * 9 / 16)
        if ph > ch - 2 * SPACE["sm"]:
            ph = ch - 2 * SPACE["sm"]
            pw = round(ph * 16 / 9)
        pw, ph = max(64, pw), max(36, ph)
        snapshot = current_config()
        meals, timetable = cached_display_data()
        preview["busy"] = True
        preview["token"] += 1
        token = preview["token"]
        # 실제 픽셀보다 크게 렌더한 뒤 CTkImage 가 줄이도록 해서 선명도를 얻는다
        render_size = (pw * PREVIEW_SUPERSAMPLE, ph * PREVIEW_SUPERSAMPLE)

        def run():
            try:
                img = render.render_wallpaper_image(
                    meals, timetable, snapshot, size=render_size).convert("RGB")
            except Exception as e:
                config.log(f"미리보기 렌더 실패: {e!r}")
                ui_after(finish_preview, token, None, 0, 0)
                return
            ui_after(finish_preview, token, img, pw, ph)
        threading.Thread(target=run, daemon=True).start()

    def finish_preview(token, img, pw, ph):
        preview["busy"] = False
        if preview_label.winfo_exists() and img is not None and token == preview["token"]:
            # CTkImage 는 참조를 잡아 둬야 GC 되지 않는다
            preview["image"] = ctk.CTkImage(light_image=img, dark_image=img, size=(pw, ph))
            preview_label.configure(image=preview["image"], text="")
        if preview["pending"]:
            preview["pending"] = False
            request_preview(50)

    # ── 설정 조작 ──
    def choose_background():
        path = filedialog.askopenfilename(
            title="배경 이미지 선택",
            filetypes=[("이미지", "*.png *.jpg *.jpeg *.bmp"), ("모든 파일", "*.*")],
        )
        if path:
            bg_var.set(path)
            bg_path_var.set(os.path.basename(path))
            request_preview()

    def clear_background():
        bg_var.set("")
        bg_path_var.set("선택 안 함")
        request_preview()

    def on_theme_change(_value=None):
        request_preview()  # 앱 크롬은 그대로, 미리보기만 다시 그린다

    def open_teacher_roster():
        def saved(names):
            cfg.update(config.load_config())
            set_status(f"교사 명단 저장됨 ({len(names)}명)")
            fill_cached_data()
            request_preview()
        dialogs.open_teacher_roster(root, on_saved=saved)

    def open_timetable_editor():
        _meals, timetable = cached_display_data()

        def saved(_timetable):
            fill_cached_data()
            request_preview(30)
            set_status("시간표를 직접 수정했습니다 — 배경화면 적용을 눌러야 완전히 반영됩니다")
        dialogs.open_timetable_editor(root, timetable, on_saved=saved)

    # ── 위젯 헬퍼 ──
    def nav_button(parent, key, label):
        button = ctk.CTkButton(
            parent, text=label, command=lambda: show_page(key), anchor="w",
            height=38, corner_radius=RADIUS["sm"], fg_color="transparent",
            hover_color=COLORS["nav_hover"], text_color=COLORS["text_dim"],
            font=_font(TYPE["body"]),
        )
        button.pack(fill="x", padx=SPACE["sm"], pady=2)
        nav_buttons[key] = button
        return button

    def primary_button(parent, text, command, **kw):
        opts = dict(text=text, command=command, height=38, corner_radius=RADIUS["sm"],
                    font=_font(TYPE["body"], "bold"), fg_color=COLORS["accent"],
                    hover_color=COLORS["accent_hover"])
        opts.update(kw)
        return ctk.CTkButton(parent, **opts)

    def secondary_button(parent, text, command, **kw):
        opts = dict(text=text, command=command, height=38, corner_radius=RADIUS["sm"],
                    font=_font(TYPE["body"]), fg_color="transparent",
                    hover_color=COLORS["nav_hover"], text_color=COLORS["text"],
                    border_width=1, border_color=COLORS["border"])
        opts.update(kw)
        return ctk.CTkButton(parent, **opts)

    def settings_card(parent, title):
        outer = card(parent)
        outer.pack(fill="x", pady=(0, SPACE["md"]))
        section_label(outer, title).pack(fill="x", padx=SPACE["md"],
                                         pady=(SPACE["md"], SPACE["xs"]))
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="x", padx=SPACE["md"], pady=(0, SPACE["md"]))
        return inner

    def settings_row(parent, label):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=SPACE["xs"])
        ctk.CTkLabel(row, text=label, width=110, anchor="w",
                     font=_font(TYPE["body"])).pack(side="left")
        return row

    # ══ 레이아웃 ══
    root.grid_columnconfigure(1, weight=1)
    root.grid_rowconfigure(0, weight=1)

    # ── 사이드바 ──
    sidebar = ctk.CTkFrame(root, width=212, corner_radius=0,
                           fg_color=COLORS["sidebar"], border_width=0)
    sidebar.grid(row=0, column=0, sticky="nsew")
    sidebar.grid_propagate(False)

    brand = ctk.CTkFrame(sidebar, fg_color="transparent")
    brand.pack(fill="x", padx=SPACE["md"], pady=(SPACE["lg"], SPACE["lg"]))
    ctk.CTkLabel(brand, text="하태욱 프로그램", anchor="w",
                 font=_font(TYPE["title"], "bold")).pack(fill="x")
    ctk.CTkLabel(brand, text="인천과학고 급식·시간표", anchor="w",
                 font=_font(TYPE["caption"]),
                 text_color=COLORS["text_dim"]).pack(fill="x", pady=(1, 0))

    nav = ctk.CTkFrame(sidebar, fg_color="transparent")
    nav.pack(fill="x")
    for key, label in NAV_ITEMS:
        nav_button(nav, key, label)

    footer = ctk.CTkFrame(sidebar, fg_color="transparent")
    footer.pack(side="bottom", fill="x", padx=SPACE["md"], pady=SPACE["md"])
    ctk.CTkLabel(footer, textvariable=last_var, anchor="w", font=_font(TYPE["caption"]),
                 text_color=COLORS["text_dim"]).pack(fill="x")
    ctk.CTkLabel(footer, textvariable=status_var, anchor="w", justify="left",
                 wraplength=180, font=_font(TYPE["caption"]),
                 text_color=COLORS["text_dim"]).pack(fill="x", pady=(SPACE["xs"], 0))

    # ── 콘텐츠 ──
    content = ctk.CTkFrame(root, fg_color="transparent")
    content.grid(row=0, column=1, sticky="nsew")
    content.grid_rowconfigure(0, weight=1)
    content.grid_columnconfigure(0, weight=1)
    # 모든 페이지를 같은 셀에 미리 grid 한 뒤 감춰 둔다.
    # grid() 를 한 번도 안 한 위젯에는 grid_remove() 가 아무 일도 하지 않아
    # 페이지가 서로 겹쳐 보이게 된다.
    for key, _label in NAV_ITEMS:
        pages[key] = ctk.CTkFrame(content, fg_color="transparent")
        pages[key].grid(row=0, column=0, sticky="nsew")
        pages[key].grid_remove()

    # ── 홈 ──
    home = pages["home"]
    home.grid_columnconfigure(0, weight=1)
    home.grid_rowconfigure(0, weight=3)
    home.grid_rowconfigure(1, weight=2)

    preview_card = card(home)
    preview_card.grid(row=0, column=0, sticky="nsew",
                      padx=SPACE["lg"], pady=(SPACE["lg"], SPACE["md"]))
    preview_card.grid_columnconfigure(0, weight=1)
    preview_card.grid_rowconfigure(1, weight=1)
    section_label(preview_card, "바탕화면 미리보기").grid(
        row=0, column=0, sticky="ew", padx=SPACE["md"], pady=(SPACE["md"], SPACE["xs"]))
    preview_holder = ctk.CTkFrame(preview_card, fg_color=COLORS["canvas"],
                                  corner_radius=RADIUS["sm"])
    preview_holder.grid(row=1, column=0, sticky="nsew",
                        padx=SPACE["md"], pady=(0, SPACE["md"]))
    preview_holder.bind("<Configure>", lambda _e: request_preview(120))
    preview_label = ctk.CTkLabel(preview_holder, text="미리보기 준비 중...",
                                 font=_font(TYPE["caption"]),
                                 text_color=COLORS["text_dim"])
    preview_label.place(relx=0.5, rely=0.5, anchor="center")

    data_row = ctk.CTkFrame(home, fg_color="transparent")
    data_row.grid(row=1, column=0, sticky="nsew", padx=SPACE["lg"])
    data_row.grid_columnconfigure((0, 1), weight=1)
    data_row.grid_rowconfigure(0, weight=1)

    tt_card = card(data_row)
    tt_card.grid(row=0, column=0, sticky="nsew", padx=(0, SPACE["sm"]))
    tt_card.grid_columnconfigure(0, weight=1)
    tt_card.grid_rowconfigure(1, weight=1)
    tt_head = ctk.CTkFrame(tt_card, fg_color="transparent")
    tt_head.grid(row=0, column=0, sticky="ew", padx=SPACE["md"],
                 pady=(SPACE["md"], SPACE["xs"]))
    section_label(tt_head, "시간표").pack(side="left")
    edit_tt_button = ctk.CTkButton(
        tt_head, text="편집", command=open_timetable_editor, width=56, height=26,
        corner_radius=RADIUS["sm"], font=_font(TYPE["caption"]),
        fg_color="transparent", hover_color=COLORS["nav_hover"],
        text_color=COLORS["accent"], border_width=1, border_color=COLORS["border"])
    edit_tt_button.pack(side="right")
    all_buttons.append(edit_tt_button)
    timetable_text = ctk.CTkTextbox(tt_card, font=mono_font(TYPE["mono"]), wrap="word",
                                    fg_color=COLORS["surface_alt"], border_width=0,
                                    corner_radius=RADIUS["sm"], activate_scrollbars=True)
    timetable_text.grid(row=1, column=0, sticky="nsew", padx=SPACE["md"],
                        pady=(0, SPACE["md"]))
    timetable_text.configure(state="disabled")

    meal_card = card(data_row)
    meal_card.grid(row=0, column=1, sticky="nsew", padx=(SPACE["sm"], 0))
    meal_card.grid_columnconfigure(0, weight=1)
    meal_card.grid_rowconfigure(1, weight=1)
    section_label(meal_card, "급식").grid(row=0, column=0, sticky="ew", padx=SPACE["md"],
                                         pady=(SPACE["md"], SPACE["xs"]))
    meal_text = ctk.CTkTextbox(meal_card, font=mono_font(TYPE["mono"]), wrap="word",
                               fg_color=COLORS["surface_alt"], border_width=0,
                               corner_radius=RADIUS["sm"], activate_scrollbars=True)
    meal_text.grid(row=1, column=0, sticky="nsew", padx=SPACE["md"], pady=(0, SPACE["md"]))
    meal_text.configure(state="disabled")

    actions = ctk.CTkFrame(home, fg_color="transparent")
    actions.grid(row=2, column=0, sticky="ew", padx=SPACE["lg"],
                 pady=(SPACE["md"], SPACE["lg"]))
    apply_button = primary_button(actions, "배경화면 적용", lambda: worker(True), width=150)
    apply_button.pack(side="right")
    regen_button = secondary_button(actions, "다시 만들기", lambda: worker(False), width=120)
    regen_button.pack(side="right", padx=(0, SPACE["sm"]))
    for button in (apply_button, regen_button):
        all_buttons.append(button)
        action_buttons.append(button)
    ctk.CTkLabel(actions, textvariable=path_var, anchor="w", font=_font(TYPE["caption"]),
                 text_color=COLORS["text_dim"]).pack(side="left", fill="x", expand=True)

    # ── 설정 ──
    # 설정은 읽기 좋은 폭으로 묶어 왼쪽에 세운다 (창을 넓혀도 컨트롤이 늘어나지 않게).
    settings_page = ctk.CTkScrollableFrame(pages["settings"], fg_color="transparent",
                                           width=560)
    settings_page.pack(side="left", fill="y", expand=False,
                       padx=SPACE["lg"], pady=SPACE["lg"])

    class_box = settings_card(settings_page, "학급")
    class_row = settings_row(class_box, "반")
    ctk.CTkOptionMenu(class_row, variable=class_var, values=["1-1", "1-2", "1-3", "1-4"],
                      command=lambda _v: request_preview(), width=140,
                      font=_font(TYPE["body"]), corner_radius=RADIUS["sm"],
                      fg_color=COLORS["surface_alt"], button_color=COLORS["border"],
                      button_hover_color=COLORS["nav_hover"],
                      text_color=COLORS["text"]).pack(side="left")

    look_box = settings_card(settings_page, "바탕화면 모양")
    ctk.CTkSegmentedButton(
        look_box, values=list(theme_labels.keys()), variable=theme_var,
        command=on_theme_change, font=_font(TYPE["body"]), corner_radius=RADIUS["sm"],
        selected_color=COLORS["accent"], selected_hover_color=COLORS["accent_hover"],
        unselected_color=COLORS["surface_alt"], unselected_hover_color=COLORS["nav_hover"],
        text_color=COLORS["text"],
    ).pack(fill="x", pady=(0, SPACE["sm"]))

    bg_path_var = tk.StringVar(value=os.path.basename(bg_var.get()) or "선택 안 함")
    bg_row = settings_row(look_box, "배경 이미지")
    ctk.CTkLabel(bg_row, textvariable=bg_path_var, anchor="w", font=_font(TYPE["caption"]),
                 text_color=COLORS["text_dim"]).pack(side="left", fill="x", expand=True)
    for text, cmd in (("지움", clear_background), ("찾기", choose_background)):
        button = secondary_button(bg_row, text, cmd, width=64, height=30)
        button.pack(side="right", padx=(SPACE["xs"], 0))
        all_buttons.append(button)

    refresh_box = settings_card(settings_page, "자동 갱신")
    interval_row = settings_row(refresh_box, "갱신 주기")
    ctk.CTkOptionMenu(interval_row, variable=interval_var,
                      values=[config.REFRESH_INTERVAL_LABELS[m]
                              for m in config.VALID_REFRESH_INTERVALS],
                      width=140, font=_font(TYPE["body"]), corner_radius=RADIUS["sm"],
                      fg_color=COLORS["surface_alt"], button_color=COLORS["border"],
                      button_hover_color=COLORS["nav_hover"],
                      text_color=COLORS["text"]).pack(side="left")
    ctk.CTkLabel(
        refresh_box,
        text="'끔'으로 둬도 날짜가 바뀌거나 절전에서 깨어나면 한 번 갱신합니다.\n"
             "어제 급식이 그대로 남아 있는 걸 막기 위한 최소 동작입니다.",
        anchor="w", justify="left", height=40, font=_font(TYPE["caption"]),
        text_color=COLORS["text_dim"]).pack(fill="x", pady=(SPACE["xs"], 0))

    misc_box = settings_card(settings_page, "기타")
    teacher_button = secondary_button(misc_box, "교사 명단 (이름 가림 해제)",
                                      open_teacher_roster)
    teacher_button.pack(fill="x", pady=(0, SPACE["sm"]))
    all_buttons.append(teacher_button)
    ctk.CTkSwitch(misc_box, text="컴퓨터 시작 시 자동 실행", variable=auto_var,
                  onvalue=True, offvalue=False, font=_font(TYPE["body"]),
                  progress_color=COLORS["accent"]).pack(fill="x", pady=SPACE["xs"])

    save_button = primary_button(settings_page, "설정 저장", save_settings, width=140)
    save_button.pack(anchor="e", pady=(SPACE["sm"], 0))
    all_buttons.append(save_button)

    # ── 단축키 ──
    def on_save_shortcut(_event):
        if not state["busy"]:
            save_settings()
        return "break"

    root.bind("<Command-s>", on_save_shortcut)
    root.bind("<Control-s>", on_save_shortcut)

    show_page("home")
    fill_cached_data()
    root.after(25, pump_ui_queue)
    root.after(600, refresh_data)  # 시작하자마자 최신 급식·시간표를 백그라운드로
    root.mainloop()
    return saved["ok"]


if __name__ == "__main__":
    show_app()
