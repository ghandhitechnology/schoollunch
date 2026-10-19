"""Local HTML/CSS/JS desktop UI. The existing Python data/render pipeline is reused."""
import base64
import copy
import datetime
import io
import json
import os
import sys
import threading
import secrets
from daily_quote import ALL_QUOTES, quote_for_day

import config
import fetch_meal
import fetch_timetable
import render
import wallpaper
import autostart
from modern_themes import is_modern_theme, theme_catalog


class DesktopApi:
    def __init__(self, on_save=None):
        self._window = None
        self._lock = threading.RLock()
        self._on_save = on_save
        self._saved = False

    def _options(self, options=None):
        cfg = config.load_config()
        cfg["background_image"] = cfg.get("custom_wallpaper", {}).get("background_image") or cfg.get("background_image", "")
        for key in ("grade", "class_num", "ui_theme", "autostart", "background_image",
                    "prompt_text", "teacher_names", "quote_enabled", "quote_date", "quote_index"):
            if options and key in options:
                cfg[key] = options[key]
        if options and "background_image" in options:
            cfg["custom_wallpaper"]["background_image"] = options["background_image"]
        if cfg["grade"] != 1 or cfg["class_num"] not in (1, 2, 3, 4):
            raise ValueError("지원하는 반은 1학년 1~4반입니다.")
        if cfg["ui_theme"] not in config.UI_THEMES:
            raise ValueError("선택한 테마를 확인해 주세요.")
        if not isinstance(cfg["autostart"], bool):
            raise ValueError("자동 실행 설정을 확인해 주세요.")
        if not isinstance(cfg.get("quote_enabled"), bool):
            raise ValueError("명언 표시 설정을 확인해 주세요.")
        index = cfg.get("quote_index", -1)
        if type(index) is not int or not -1 <= index < len(ALL_QUOTES):
            raise ValueError("명언 번호를 확인해 주세요.")
        if not isinstance(cfg.get("quote_date"), str):
            raise ValueError("명언 선택 날짜를 확인해 주세요.")
        cfg["teacher_names"] = [str(n).strip() for n in cfg.get("teacher_names", []) if str(n).strip()]
        return cfg

    def _data(self, cfg, fetch=False):
        cache = config.load_cache()
        meal = cache.get("meal", {})
        tt = copy.deepcopy(cache.get("timetable", {}))
        target = fetch_timetable._target_date().isoformat()
        tt_valid = (tt.get("date") == target and tt.get("grade") == cfg["grade"]
                    and tt.get("class_num") == cfg["class_num"])
        # One-time migration: old cache has no change metadata.
        metadata_valid = all("changed" in p for p in tt.get("periods", []))
        meal_valid = meal.get("date") == datetime.date.today().strftime("%Y%m%d")
        if fetch and (not tt_valid or not metadata_valid):
            tt = fetch_timetable.fetch_today(cfg)
        elif not tt_valid:
            tt = {"date": target, "weekday_label": "월화수목금토일"[datetime.date.fromisoformat(target).weekday()],
                  "periods": [], "_cached": False}
        meals = fetch_meal.fetch_meals(cfg) if fetch and not meal_valid else copy.deepcopy(meal.get("data", {}))
        fetch_timetable._resolve_teachers(tt, cfg.get("teacher_names", []))
        return meals, tt

    def _preview(self, cfg, meals, tt):
        # Rendering reads local data only. No background refresh timer.
        width, height = render.detect_resolution()
        image = render.render_wallpaper_image(meals, tt, cfg, size=(width, height))
        image.thumbnail((1200, 750))
        out = io.BytesIO()
        image.convert("RGB").save(out, format="PNG")
        return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode("ascii")

    def state(self):
        with self._lock:
            cfg = self._options()
            meals, tt = self._data(cfg, fetch=True)
            return {"config": cfg, "meals": meals, "timetable": tt,
                    "quote": quote_for_day(cfg=cfg),
                    "today": datetime.date.today().isoformat(),
                    "preview": self._preview(cfg, meals, tt)}

    def preview(self, options):
        with self._lock:
            cfg = self._options(options)
            meals, tt = self._data(cfg)
            return self._preview(cfg, meals, tt)

    def save(self, options):
        with self._lock:
            cfg = self._options(options)
            cfg["configured"] = True
            config.save_config(cfg)
            self._saved = True
            if self._on_save:
                self._on_save(cfg)
            try:
                autostart.apply(cfg["autostart"])
            except Exception as exc:
                config.log(f"자동 실행 설정 실패: {exc!r}")
                return {"message": "설정은 저장됐지만 자동 실행 등록에 실패했어요."}
            return {"message": "설정을 저장했어요."}

    def apply(self, options):
        with self._lock:
            # A different class requires one fetch; appearance-only edits use cache.
            cfg = self._options(options)
            meals, tt = self._data(cfg, fetch=True)
            expected = fetch_timetable._target_date().isoformat()
            if (tt.get("date") != expected or tt.get("grade") != cfg["grade"]
                    or tt.get("class_num") != cfg["class_num"] or not tt.get("periods")):
                raise ValueError("선택한 반의 최신 시간표를 가져오지 못했어요. 잠시 후 다시 시도해 주세요.")
            path = render.render_wallpaper(meals, tt, cfg)
            result = wallpaper.apply_wallpaper(path)
            if not result["ok"]:
                raise RuntimeError(result.get("detail") or "바탕화면 적용에 실패했어요.")
            save_result = self.save(options)
            return {"message": "바탕화면에 적용했어요." if save_result["message"] == "설정을 저장했어요." else save_result["message"],
                    "preview": self._preview(cfg, meals, tt), "meals": meals, "timetable": tt}

    def change_quote(self, options, reset=False):
        """Local preview only; save/apply commits today's choice."""
        with self._lock:
            cfg = self._options(options)
            if reset:
                cfg.update(quote_date="", quote_index=-1)
            else:
                current = quote_for_day(cfg=cfg)["text"]
                choices = [i for i, q in enumerate(ALL_QUOTES) if q["text"] != current]
                cfg.update(quote_date=datetime.date.today().isoformat(), quote_index=secrets.choice(choices))
            meals, tt = self._data(cfg)
            return {"quote": quote_for_day(cfg=cfg), "quote_date": cfg["quote_date"],
                    "quote_index": cfg["quote_index"], "preview": self._preview(cfg, meals, tt)}

    def choose_background(self):
        import webview
        paths = self._window.create_file_dialog(webview.FileDialog.OPEN,
                    file_types=("이미지 (*.png;*.jpg;*.jpeg;*.bmp;*.webp)",))
        return paths[0] if paths else None

    def edit_timetable(self, periods, options):
        with self._lock:
            cfg = self._options(options)
            _, tt = self._data(cfg)
            if not tt.get("periods"):
                raise ValueError("현재 표시 중인 반의 시간표만 수정할 수 있어요.")
            if not isinstance(periods, list) or len(periods) != len(tt["periods"]):
                raise ValueError("교시 수를 확인해 주세요.")
            for original, edited in zip(tt["periods"], periods):
                for field in ("subject", "teacher"):
                    value = edited.get(field)
                    if not isinstance(value, str) or len(value) > 60:
                        raise ValueError("과목명과 선생님 이름은 60자 이내로 입력해 주세요.")
                    if original.get(field) != value.strip():
                        original[field] = value.strip()
                        original["changed"] = True
            tt.update(grade=cfg["grade"], class_num=cfg["class_num"], _edited=True)
            config.save_cache_entry("timetable", tt)
            return {"timetable": tt, "preview": self._preview(cfg, self._data(cfg)[0], tt)}

    def editor(self, options, reset=False):
        import layout_editor
        with self._lock:
            cfg = self._options(options)
            if reset:
                cfg["custom_wallpaper"] = config.default_custom_wallpaper()
                cfg["custom_wallpaper"]["drawing_overlay"] = ""
                cfg["background_image"] = ""
            size = render.detect_resolution()
            cfg["custom_wallpaper"] = layout_editor.normalize(cfg["custom_wallpaper"], cfg, size)
            meals, tt = self._data(cfg)
            custom = cfg["custom_wallpaper"]
            key = "daily_layout" if is_modern_theme(cfg["ui_theme"]) else "layout"
            panels = [{"key": name, "label": layout_editor.LABELS[name],
                       "src": self._image_url(image), "rect": custom[key][name]}
                      for name, image in layout_editor.panel_images(meals, tt, cfg, size).items()]
            stickers = []
            for item in custom["stickers"]:
                try:
                    from PIL import Image
                    with Image.open(item["path"]) as image:
                        stickers.append(dict(item, src=self._image_url(image, (1000, 1000))))
                except OSError:
                    config.log(f"스티커 파일 없음: {item['path']}")
            custom["stickers"] = [{k: v for k, v in item.items() if k != "src"} for item in stickers]
            return {"custom": custom, "panels": panels, "stickers": stickers,
                    "layout_key": key, "defaults": layout_editor.regions(cfg, size),
                    "width": size[0], "height": size[1],
                    "base_color": "#%02x%02x%02x" % render._theme(cfg["ui_theme"])["bg"][:3],
                    "background": self._image_url(layout_editor.background(cfg, size), (1600, 1000)),
                    "drawing": self._image_url(layout_editor.drawing(cfg, size))}

    def _image_url(self, image, maximum=None):
        image = image.convert("RGBA")
        if maximum:
            image.thumbnail(maximum)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

    def pick_editor_image(self):
        from PIL import Image
        path = self.choose_background()
        if not path:
            return None
        with Image.open(path) as image:
            return {"path": path, "width": image.width, "height": image.height,
                    "src": self._image_url(image, (1600, 1200))}

    def save_editor(self, options, custom, drawing_png, apply=False):
        from PIL import Image, ImageColor
        import layout_editor
        with self._lock:
            cfg = self._options(options)
            size = render.detect_resolution()
            custom = layout_editor.normalize(custom, cfg, size)
            ImageColor.getrgb(custom["pen_color"])
            if not isinstance(drawing_png, str) or not drawing_png.startswith("data:image/png;base64,") or len(drawing_png) > 32_000_000:
                raise ValueError("드로잉 이미지 형식을 확인해 주세요.")
            data = base64.b64decode(drawing_png.split(",", 1)[1], validate=True)
            with Image.open(io.BytesIO(data)) as uploaded:
                if uploaded.width * uploaded.height > 25_000_000:
                    raise ValueError("드로잉 이미지가 너무 커요.")
                drawing = uploaded.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
            custom["_drawing_image"] = drawing
            cfg["custom_wallpaper"] = custom
            cfg["background_image"] = custom["background_image"]
            cfg["configured"] = True
            meals, tt = self._data(cfg)
            if apply:
                if not tt.get("periods"):
                    raise ValueError("선택한 반의 시간표가 없어요. 오늘 화면에서 자료를 확인해 주세요.")
                path = render.render_wallpaper(meals, tt, cfg)
                result = wallpaper.apply_wallpaper(path)
                if not result["ok"]:
                    raise RuntimeError(result.get("detail") or "바탕화면 적용에 실패했어요.")
            if drawing.getchannel("A").getbbox():
                temporary = config.CUSTOM_DRAWING_PATH + ".tmp"
                drawing.save(temporary, format="PNG")
                os.replace(temporary, config.CUSTOM_DRAWING_PATH)
                custom["drawing_overlay"] = config.CUSTOM_DRAWING_PATH
            else:
                custom["drawing_overlay"] = ""
            del custom["_drawing_image"]
            config.save_config(cfg)
            self._saved = True
            if self._on_save:
                self._on_save(cfg)
            try:
                autostart.apply(cfg["autostart"])
            except Exception as exc:
                config.log(f"자동 실행 설정 실패: {exc!r}")
            return {"message": "저장하고 바탕화면에 적용했어요." if apply else "배치를 저장했어요.",
                    "state": {"config": cfg, "meals": meals, "timetable": tt,
                              "quote": quote_for_day(cfg=cfg),
                    "today": datetime.date.today().isoformat(), "preview": self._preview(cfg, meals, tt)}}


def show_editor():
    return show_app(initial_page="editor")


def load_html(initial_page="today"):
    with open(config.resource_path(os.path.join("ui", "index.html")), encoding="utf-8") as source:
        html = source.read()
    html = html.replace("/*THEME_CATALOG*/", json.dumps(theme_catalog(), ensure_ascii=False))
    with open(config.resource_path(os.path.join("ui", "editor.css")), encoding="utf-8") as source:
        html = html.replace("/*EDITOR_STYLE*/", source.read())
    with open(config.resource_path(os.path.join("ui", "editor.js")), encoding="utf-8") as source:
        script = "window.initialPage=" + json.dumps(initial_page) + ";\n" + source.read()
        return html.replace("<!--EDITOR_SCRIPT-->", "<script>" + script + "</script>")


def show_app(on_save=None, initial_page="today"):
    import webview
    api = DesktopApi(on_save)
    html = load_html(initial_page)
    api._window = webview.create_window("Schoolunch · 인천과학고", html=html, js_api=api,
                    width=1180, height=760, min_size=(960, 680), background_color="#F7F8FA")
    webview.start(gui="edgechromium" if sys.platform == "win32" else None)
    return api._saved
