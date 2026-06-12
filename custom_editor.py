# -*- coding: utf-8 -*-
"""커스텀 배경 레이아웃 에디터.

캔버스를 매번 전부 지우고 다시 그리는 대신 아이템을 태그로 부분 갱신한다:
미리보기 이미지 1개("preview") + 패널/스티커 사각형("overlay") + 펜 획("ink").
드래그·펜 입력은 캔버스에 즉시 반영하고, 무거운 미리보기 렌더는
백그라운드 스레드에서 디바운스로 따라온다. Tk 접근은 전부 메인 스레드 큐를 거친다.
"""
import copy
import os
import queue
import threading
import tkinter as tk
from tkinter import colorchooser, filedialog

from PIL import Image, ImageDraw, ImageTk

import config
import fetch_timetable
import render
import ui_common
from ui_common import ThemedButton, font as _font

EDITOR_SIZE = (1920, 1080)
HANDLE_PX = 12
PREVIEW_DEBOUNCE_MS = 150
PEN_WIDTH = 10
ERASER_WIDTH = 28


def _clamp(value, minimum=0.0, maximum=1.0):
    return max(minimum, min(maximum, float(value)))


def _clamp_rect(rect, min_w=0.035, min_h=0.035):
    x, y, w, h = [float(v) for v in rect]
    w = _clamp(w, min_w, 1.0)
    h = _clamp(h, min_h, 1.0)
    x = _clamp(x, 0.0, 1.0 - w)
    y = _clamp(y, 0.0, 1.0 - h)
    return [x, y, w, h]


def _rect_contains(rect, x, y):
    rx, ry, rw, rh = rect
    return rx <= x <= rx + rw and ry <= y <= ry + rh


class CustomWallpaperEditor:
    def __init__(self, root, on_back, set_status, on_regenerate=None):
        self.root = root
        self.on_back = on_back
        self.set_status = set_status
        self.on_regenerate = on_regenerate
        self.frame = tk.Frame(root)
        self.canvas = None
        self.toolbar = None
        self.photo = None
        self.image_item = None
        self.placeholder_items = []
        self.preview_box = (0, 0, 1, 1)
        self.custom = config.default_custom_wallpaper()
        self.drawing = Image.new("RGBA", EDITOR_SIZE, (0, 0, 0, 0))
        self.mode = tk.StringVar(value="select")
        self.selected = ("panel", "timetable")
        self.drag = None
        self.preview_job = None
        self.preview_token = 0
        self.preview_busy = False
        self.preview_pending = False
        self.stroke_seq = 0      # 펜/지우개 입력 횟수 (미리보기 반영 추적용)
        self.saving = False
        self.regenerate_after_save = False
        self.buttons = []
        self.mode_buttons = {}
        self.ui_queue = queue.Queue()
        self.ink_var = tk.StringVar(value="#245cff")
        self._palette = None
        self.build()

    def palette(self):
        if self._palette is None:
            self._palette = ui_common.palette(config.load_config().get("ui_theme"))
        return self._palette

    def ui_after(self, callback, *args):
        self.ui_queue.put((callback, args))

    def pump_ui_queue(self):
        try:
            while True:
                callback, args = self.ui_queue.get_nowait()
                callback(*args)
        except queue.Empty:
            pass
        except (RuntimeError, tk.TclError):
            return
        try:
            self.root.after(25, self.pump_ui_queue)
        except (RuntimeError, tk.TclError):
            return

    def build(self):
        self.toolbar = tk.Frame(self.frame)
        self.toolbar.pack(fill="x", padx=12, pady=(10, 4))
        row1 = tk.Frame(self.toolbar)
        row1.pack(fill="x")
        row2 = tk.Frame(self.toolbar)
        row2.pack(fill="x", pady=(6, 0))
        self.toolbar_rows = [row1, row2]

        self._button(row1, "뒤로", self.back).pack(side="left", padx=(0, 6))
        self._button(row1, "저장", self.save).pack(side="left", padx=(0, 14))
        self._button(row1, "배경화면 재생성", lambda: self.save(regenerate=True)).pack(side="left", padx=(0, 14))
        self._button(row1, "배경 이미지", self.choose_background).pack(side="left", padx=(0, 6))
        self._button(row1, "스티커 추가", self.add_sticker).pack(side="left", padx=(0, 6))
        self._button(row1, "스티커 삭제", self.delete_selected_sticker).pack(side="left")

        for label, mode in (("선택", "select"), ("펜", "pen"), ("지우개", "eraser")):
            button = self._button(row2, label, lambda m=mode: self.set_mode(m))
            button.pack(side="left", padx=(0, 6))
            self.mode_buttons[mode] = button
        self._button(row2, "드로잉 지움", self.clear_drawing).pack(side="left", padx=(0, 14))

        swatch = tk.Canvas(row2, width=32, height=32, highlightthickness=0)
        swatch.pack(side="left")
        swatch.bind("<Button-1>", lambda _e: self.pick_color())
        self.swatch = swatch

        self._button(row2, "글자 −", lambda: self.adjust_font_scale(-0.1)).pack(side="left", padx=(14, 6))
        self.font_scale_label = tk.Label(row2, text="글자 100%", font=_font(12, "bold"))
        self.font_scale_label.pack(side="left")
        self._button(row2, "글자 +", lambda: self.adjust_font_scale(0.1)).pack(side="left", padx=(6, 0))

        self.canvas = tk.Canvas(self.frame, highlightthickness=1)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.canvas.bind("<Configure>", lambda _e: self.on_canvas_resize())
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.apply_style()
        self.root.after(25, self.pump_ui_queue)

    def _button(self, parent, text, command):
        b = ThemedButton(parent, text, command, font=_font(12, "bold"))
        self.buttons.append(b)
        return b

    def apply_style(self):
        p = self.palette()
        self.frame.configure(bg=p["bg"])
        self.toolbar.configure(bg=p["panel"])
        for toolbar_row in self.toolbar_rows:
            toolbar_row.configure(bg=p["panel"])
        self.canvas.configure(bg=p["canvas_bg"], highlightbackground=p["border"])
        self.font_scale_label.configure(bg=p["panel"], fg=p["fg"])
        for button in self.buttons:
            button.set_palette(p)
        active = self.mode.get()
        for mode, button in self.mode_buttons.items():
            button.set_selected(mode == active)
        self.draw_swatch()

    def set_busy(self, value):
        self.saving = value
        for button in self.buttons:
            if button.winfo_exists():
                button.set_enabled(not value)

    def draw_swatch(self):
        self.swatch.delete("all")
        self.swatch.create_oval(4, 4, 28, 28, fill=self.ink_var.get(),
                                outline=self.palette()["border"], width=2)

    def set_mode(self, mode):
        self.mode.set(mode)
        for name, button in self.mode_buttons.items():
            button.set_selected(name == mode)
        labels = {"select": "선택", "pen": "펜", "eraser": "지우개"}
        self.set_status(f"커스텀 배경: {labels.get(mode, mode)}")

    def load_state(self):
        cfg = config.load_config()
        self.custom = copy.deepcopy(cfg.get("custom_wallpaper", config.default_custom_wallpaper()))
        self.ink_var.set(self.custom.get("pen_color", "#245cff"))
        path = self.custom.get("drawing_overlay", config.CUSTOM_DRAWING_PATH)
        if path and os.path.exists(path):
            try:
                self.drawing = Image.open(path).convert("RGBA").resize(EDITOR_SIZE, Image.Resampling.LANCZOS)
            except Exception:
                self.drawing = Image.new("RGBA", EDITOR_SIZE, (0, 0, 0, 0))
        else:
            self.drawing = Image.new("RGBA", EDITOR_SIZE, (0, 0, 0, 0))
        self._palette = None  # 메인 화면에서 테마가 바뀌었을 수 있다
        self.apply_style()
        self.update_font_scale_label()
        self.update_overlays()
        self.request_preview(30)

    def show(self):
        self.load_state()
        self.frame.pack(fill="both", expand=True)
        self.root.bind("<Escape>", lambda _e: self.back())
        self.root.bind("<Delete>", lambda _e: self.delete_selected_sticker())
        self.root.bind("<BackSpace>", lambda _e: self.delete_selected_sticker())
        self.set_status("커스텀 배경 편집")

    def hide(self):
        for sequence in ("<Escape>", "<Delete>", "<BackSpace>"):
            self.root.unbind(sequence)
        self.frame.pack_forget()

    def back(self):
        self.hide()
        self.on_back()

    def adjust_font_scale(self, delta):
        scale = config._safe_font_scale(self.custom.get("font_scale", 1.0) + delta)
        scale = round(scale * 10) / 10
        self.custom["font_scale"] = scale
        self.update_font_scale_label()
        self.request_preview(120)
        self.set_status(f"글자 크기 {round(scale * 100)}% (저장을 눌러야 적용됩니다)")

    def update_font_scale_label(self):
        scale = config._safe_font_scale(self.custom.get("font_scale", 1.0))
        self.font_scale_label.configure(text=f"글자 {round(scale * 100)}%")

    def pick_color(self):
        color = colorchooser.askcolor(color=self.ink_var.get(), parent=self.root)[1]
        if color:
            self.ink_var.set(color)
            self.custom["pen_color"] = color
            self.draw_swatch()

    def choose_background(self):
        path = filedialog.askopenfilename(
            title="커스텀 배경 이미지 선택",
            filetypes=[("이미지", "*.png *.jpg *.jpeg *.bmp"), ("모든 파일", "*.*")],
        )
        if path:
            self.custom["background_image"] = path
            self.request_preview(30)

    def add_sticker(self):
        path = filedialog.askopenfilename(
            title="스티커 이미지 선택",
            filetypes=[("이미지", "*.png *.jpg *.jpeg *.bmp"), ("모든 파일", "*.*")],
        )
        if path:
            self.custom.setdefault("stickers", []).append({"path": path, "rect": [0.38, 0.36, 0.18, 0.18]})
            self.selected = ("sticker", len(self.custom["stickers"]) - 1)
            self.update_overlays()
            self.request_preview(30)

    def delete_selected_sticker(self):
        kind, key = self.selected
        stickers = self.custom.get("stickers", [])
        if kind == "sticker" and 0 <= key < len(stickers):
            del stickers[key]
            self.selected = ("panel", "timetable")
            self.update_overlays()
            self.request_preview(30)
            self.set_status("스티커 삭제됨")
        else:
            self.set_status("삭제할 스티커를 먼저 선택하세요")

    def clear_drawing(self):
        self.drawing = Image.new("RGBA", EDITOR_SIZE, (0, 0, 0, 0))
        if self.canvas.winfo_exists():
            self.canvas.delete("ink")
        self.request_preview(30)

    def save(self, regenerate=False):
        if self.saving:
            return
        self.regenerate_after_save = bool(regenerate and self.on_regenerate)
        custom = copy.deepcopy(self.custom)
        drawing = self.drawing.copy()
        custom["pen_color"] = self.ink_var.get()
        custom["drawing_overlay"] = config.CUSTOM_DRAWING_PATH
        self.set_busy(True)
        self.set_status("커스텀 배경 저장 중...")

        def run():
            try:
                os.makedirs(os.path.dirname(config.CUSTOM_DRAWING_PATH), exist_ok=True)
                if drawing.getchannel("A").getbbox() is None:
                    # 빈 드로잉은 저장하지 않는다 (기본 레이아웃 복귀가 가능하도록)
                    custom["drawing_overlay"] = ""
                    if os.path.exists(config.CUSTOM_DRAWING_PATH):
                        os.remove(config.CUSTOM_DRAWING_PATH)
                else:
                    drawing.save(config.CUSTOM_DRAWING_PATH)
                for name, rect in list(custom.get("layout", {}).items()):
                    custom["layout"][name] = _clamp_rect(rect)
                for sticker in custom.get("stickers", []):
                    sticker["rect"] = _clamp_rect(sticker.get("rect", [0, 0, 0.1, 0.1]))
                cfg = config.load_config()
                cfg["custom_wallpaper"] = custom
                cfg["configured"] = True
                config.save_config(cfg)
            except Exception as e:
                config.log(f"커스텀 배경 저장 실패: {e!r}")
                self.ui_after(self.finish_save, False, str(e), custom)
                return
            self.ui_after(self.finish_save, True, "", custom)

        threading.Thread(target=run, daemon=True).start()

    def finish_save(self, ok, error, custom):
        self.set_busy(False)
        if ok:
            self.custom = copy.deepcopy(custom)
            self.set_status("커스텀 배경 저장됨")
            self.request_preview(30)
            if self.regenerate_after_save and self.on_regenerate:
                self.regenerate_after_save = False
                self.on_regenerate()
        else:
            self.regenerate_after_save = False
            self.set_status(f"커스텀 배경 저장 실패: {error}")

    def sample_data(self):
        cache = config.load_cache()
        meals = dict(cache.get("meal", {}).get("data") or {})
        timetable = copy.deepcopy(cache.get("timetable") or {})
        fetch_timetable._resolve_teachers(timetable, config.load_config().get("teacher_names") or [])
        if not timetable:
            timetable = {
                "date": "2026-06-12",
                "weekday_label": "금",
                "periods": [
                    {"period": 1, "time": "08:40", "subject": "수학", "teacher": "김"},
                    {"period": 2, "time": "09:40", "subject": "물리", "teacher": "박"},
                    {"period": 3, "time": "10:40", "subject": "정보", "teacher": "최"},
                ],
            }
        if not meals:
            meals = {"조식": ["쌀밥"], "중식": ["카레라이스", "김치"], "석식": ["닭갈비"]}
        return meals, timetable

    # ── 미리보기 (백그라운드 렌더) ─────────────────────────

    def on_canvas_resize(self):
        self.update_layout()
        self.update_overlays()
        self.request_preview()

    def update_layout(self):
        """캔버스 크기에 맞춰 16:9 미리보기 영역을 계산한다."""
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        aspect = 16 / 9
        pw = cw - 24
        ph = round(pw / aspect)
        if ph > ch - 24:
            ph = ch - 24
            pw = round(ph * aspect)
        pw, ph = max(1, pw), max(1, ph)
        ox = (cw - pw) // 2
        oy = (ch - ph) // 2
        self.preview_box = (ox, oy, pw, ph)
        if self.image_item is not None:
            self.canvas.coords(self.image_item, ox, oy)

    def request_preview(self, delay=PREVIEW_DEBOUNCE_MS):
        if self.saving:
            return
        if self.preview_job:
            self.root.after_cancel(self.preview_job)
        self.preview_job = self.root.after(delay, self.start_preview)

    def start_preview(self):
        self.preview_job = None
        if not self.canvas.winfo_exists():
            return
        if self.preview_busy:
            self.preview_pending = True
            return
        self.update_layout()
        ox, oy, pw, ph = self.preview_box
        if self.image_item is None and not self.placeholder_items:
            p = self.palette()
            self.placeholder_items = [
                self.canvas.create_rectangle(ox, oy, ox + pw, oy + ph,
                                             fill=p["canvas_bg"], outline=p["border"]),
                self.canvas.create_text(ox + pw / 2, oy + ph / 2, text="미리보기 생성 중...",
                                        fill=p["dim"], font=_font(13, "bold")),
            ]
            self.canvas.tag_raise("overlay")
        self.preview_busy = True
        self.preview_token += 1
        token = self.preview_token
        seq = self.stroke_seq
        cfg = config.load_config()
        cfg["custom_wallpaper"] = copy.deepcopy(self.custom)
        cfg["custom_wallpaper"]["_drawing_image"] = self.drawing.copy()
        meals, timetable = self.sample_data()
        size = (pw, ph)

        def run():
            try:
                img = render.render_wallpaper_image(meals, timetable, cfg, size=size).convert("RGB")
            except Exception as e:
                config.log(f"커스텀 배경 미리보기 실패: {e!r}")
                self.ui_after(self.finish_preview, token, seq, None, str(e))
                return
            self.ui_after(self.finish_preview, token, seq, img, "")

        threading.Thread(target=run, daemon=True).start()

    def finish_preview(self, token, seq, img, error):
        self.preview_busy = False
        if not self.canvas.winfo_exists() or token != self.preview_token:
            return
        if error:
            self.set_status(f"미리보기 실패: {error}")
        elif img is not None:
            for item in self.placeholder_items:
                self.canvas.delete(item)
            self.placeholder_items = []
            ox, oy, _, _ = self.preview_box
            self.photo = ImageTk.PhotoImage(img)
            if self.image_item is None:
                self.image_item = self.canvas.create_image(ox, oy, image=self.photo, anchor="nw")
                self.canvas.tag_lower(self.image_item)
            else:
                self.canvas.itemconfigure(self.image_item, image=self.photo)
                self.canvas.coords(self.image_item, ox, oy)
            if seq >= self.stroke_seq:
                self.canvas.delete("ink")  # 임시 획이 미리보기에 반영됨
            self.canvas.tag_raise("overlay")
        if self.preview_pending:
            self.preview_pending = False
            self.request_preview(30)

    # ── 오버레이 (즉시 갱신) ──────────────────────────────

    def update_overlays(self):
        if not self.canvas or not self.canvas.winfo_exists():
            return
        self.canvas.delete("overlay")
        p = self.palette()
        labels = {"prompt": "프롬프트", "timetable": "시간표", "meal": "급식"}
        for name, rect in self.custom.get("layout", {}).items():
            self.draw_rect(rect, labels.get(name, name),
                           p["accent"] if self.selected == ("panel", name) else p["border"])
        for idx, sticker in enumerate(self.custom.get("stickers", [])):
            self.draw_rect(sticker.get("rect", [0, 0, 0.1, 0.1]), f"스티커 {idx + 1}",
                           p["accent"] if self.selected == ("sticker", idx) else p["dim"])

    def draw_rect(self, rect, label, color):
        x0, y0, x1, y1 = self.rect_to_canvas(rect)
        self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=2, tags="overlay")
        self.canvas.create_text(x0 + 6, y0 + 6, text=label, anchor="nw", fill=color,
                                font=_font(10, "bold"), tags="overlay")
        self.canvas.create_rectangle(x1 - HANDLE_PX, y1 - HANDLE_PX, x1, y1,
                                     fill=color, outline=color, tags="overlay")

    def rect_to_canvas(self, rect):
        ox, oy, pw, ph = self.preview_box
        x, y, w, h = _clamp_rect(rect)
        return [ox + x * pw, oy + y * ph, ox + (x + w) * pw, oy + (y + h) * ph]

    def canvas_to_norm(self, x, y):
        ox, oy, pw, ph = self.preview_box
        return _clamp((x - ox) / pw), _clamp((y - oy) / ph)

    def current_rect(self):
        kind, key = self.selected
        if kind == "panel":
            return self.custom["layout"][key]
        if kind == "sticker" and 0 <= key < len(self.custom.get("stickers", [])):
            return self.custom["stickers"][key]["rect"]
        return None

    def set_current_rect(self, rect):
        rect = _clamp_rect(rect)
        kind, key = self.selected
        if kind == "panel":
            self.custom["layout"][key] = rect
        elif kind == "sticker" and 0 <= key < len(self.custom.get("stickers", [])):
            self.custom["stickers"][key]["rect"] = rect

    def hit_test(self, nx, ny):
        for idx in reversed(range(len(self.custom.get("stickers", [])))):
            if _rect_contains(_clamp_rect(self.custom["stickers"][idx]["rect"]), nx, ny):
                return ("sticker", idx)
        for name, rect in self.custom.get("layout", {}).items():
            if _rect_contains(_clamp_rect(rect), nx, ny):
                return ("panel", name)
        return None

    # ── 마우스 입력 ───────────────────────────────────────

    def on_press(self, event):
        if self.saving:
            return
        nx, ny = self.canvas_to_norm(event.x, event.y)
        if self.mode.get() in ("pen", "eraser"):
            self.drag = {"type": self.mode.get(), "last": (nx, ny)}
            self.draw_at(nx, ny, nx, ny)
            return
        hit = self.hit_test(nx, ny)
        if hit:
            self.selected = hit
            rect = _clamp_rect(self.current_rect())
            x0, y0, x1, y1 = self.rect_to_canvas(rect)
            action = "resize" if abs(event.x - x1) <= HANDLE_PX * 2 and abs(event.y - y1) <= HANDLE_PX * 2 else "move"
            self.drag = {"type": action, "start": (nx, ny), "rect": rect}
        else:
            self.drag = None
        self.update_overlays()

    def on_drag(self, event):
        if not self.drag or self.saving:
            return
        nx, ny = self.canvas_to_norm(event.x, event.y)
        if self.drag["type"] in ("pen", "eraser"):
            lx, ly = self.drag["last"]
            self.draw_at(lx, ly, nx, ny)
            self.drag["last"] = (nx, ny)
            return
        sx, sy = self.drag["start"]
        x, y, w, h = self.drag["rect"]
        if self.drag["type"] == "move":
            self.set_current_rect([x + nx - sx, y + ny - sy, w, h])
        else:
            self.set_current_rect([x, y, w + nx - sx, h + ny - sy])
        self.update_overlays()
        self.request_preview()

    def on_release(self, _event):
        if self.drag:
            self.drag = None
            self.request_preview(30)

    def draw_at(self, x0, y0, x1, y1):
        p0 = (round(x0 * EDITOR_SIZE[0]), round(y0 * EDITOR_SIZE[1]))
        p1 = (round(x1 * EDITOR_SIZE[0]), round(y1 * EDITOR_SIZE[1]))
        mode = self.mode.get()
        width = PEN_WIDTH if mode == "pen" else ERASER_WIDTH
        if mode == "eraser":
            mask = Image.new("L", EDITOR_SIZE, 0)
            ImageDraw.Draw(mask).line([p0, p1], fill=255, width=width)
            r, g, b, alpha = self.drawing.split()
            alpha.paste(0, mask=mask)
            self.drawing = Image.merge("RGBA", (r, g, b, alpha))
        else:
            ImageDraw.Draw(self.drawing, "RGBA").line([p0, p1], fill=self.ink_var.get(), width=width)
            # 미리보기 렌더를 기다리지 않고 캔버스에 획을 바로 보여 준다
            ox, oy, pw, ph = self.preview_box
            self.canvas.create_line(
                ox + x0 * pw, oy + y0 * ph, ox + x1 * pw, oy + y1 * ph,
                fill=self.ink_var.get(), width=max(1, round(width * pw / EDITOR_SIZE[0])),
                capstyle="round", tags="ink",
            )
            self.canvas.tag_raise("overlay")
        self.stroke_seq += 1
        self.request_preview(250 if mode == "pen" else PREVIEW_DEBOUNCE_MS)
