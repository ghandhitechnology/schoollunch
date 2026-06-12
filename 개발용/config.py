# -*- coding: utf-8 -*-
"""설정/캐시/로그 관리. 모든 데이터는 %APPDATA%\\하태욱프로그램 아래에 저장된다."""
import json
import math
import os
import sys
import datetime
import copy

APP_NAME = "하태욱프로그램"

UI_THEMES = {
    "black_on_white": "흑백",
    "white_on_black": "백흑",
    "crayon_sketch": "감성",
    "cyber_terminal": "컴퓨터",
}
DEFAULT_UI_THEME = "black_on_white"
VALID_GRADES = (1,)
VALID_CLASSES = (1, 2, 3, 4)


def app_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:  # 개발/테스트용 (macOS, Linux)
        base = os.path.expanduser("~/.config")
    d = os.path.join(base, APP_NAME)
    os.makedirs(d, exist_ok=True)
    return d


def resource_path(rel: str) -> str:
    """PyInstaller onefile 실행 시 임시 해제 폴더(_MEIPASS) 기준 경로."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


CONFIG_PATH = os.path.join(app_dir(), "config.json")
CACHE_PATH = os.path.join(app_dir(), "cache.json")
LOG_PATH = os.path.join(app_dir(), "log.txt")
WALLPAPER_PATH = os.path.join(app_dir(), "wallpaper.png")
CUSTOM_DRAWING_PATH = os.path.join(app_dir(), "custom_drawing.png")

FONT_SCALE_MIN, FONT_SCALE_MAX = 0.5, 2.5

DEFAULT_CUSTOM_WALLPAPER = {
    "background_image": "",
    "drawing_overlay": CUSTOM_DRAWING_PATH,
    "pen_color": "#245cff",
    "font_scale": 1.0,
    "layout": {
        "prompt": [0.24, 0.035, 0.50, 0.045],
        "timetable": [0.24, 0.095, 0.28, 0.24],
        "meal": [0.55, 0.095, 0.42, 0.36],
    },
    "stickers": [],
}

DEFAULTS = {
    "grade": 1,
    "class_num": 1,           # 1~4
    "background_image": "",   # 비우면 레트로 단색 배경
    "ui_theme": DEFAULT_UI_THEME,
    "autostart": True,
    "configured": False,      # 최초 설정창을 거쳤는지
    "neis": {},               # {"atpt": "E10", "code": "7310058"} 캐시
    "comcigan_code": 0,       # 컴시간알리미 학교 코드 캐시
    "teacher_names": [],      # 교사 전체 이름 명단 (컴시간 마스킹 해제 매칭용)
    "custom_wallpaper": DEFAULT_CUSTOM_WALLPAPER,
}


def default_custom_wallpaper() -> dict:
    return copy.deepcopy(DEFAULT_CUSTOM_WALLPAPER)


def _merge_custom_wallpaper(value) -> dict:
    custom = default_custom_wallpaper()
    if not isinstance(value, dict):
        return custom
    for key in ("background_image", "drawing_overlay", "pen_color"):
        if isinstance(value.get(key), str):
            custom[key] = value[key]
    custom["font_scale"] = _safe_font_scale(value.get("font_scale"))
    if isinstance(value.get("layout"), dict):
        for name, default_rect in custom["layout"].items():
            rect = _safe_rect(value["layout"].get(name))
            custom["layout"][name] = rect if rect is not None else default_rect
    if isinstance(value.get("stickers"), list):
        stickers = []
        for sticker in value["stickers"]:
            if not isinstance(sticker, dict):
                continue
            path = sticker.get("path")
            rect = _safe_rect(sticker.get("rect"))
            if isinstance(path, str) and rect is not None:
                stickers.append({
                    "path": path,
                    "rect": rect,
                    "angle": _safe_angle(sticker.get("angle", 0)),
                })
        custom["stickers"] = stickers
    return custom


def _safe_rect(rect):
    """4개의 유한한 float 리스트만 통과시킨다 (NaN/Inf/타입 오류 차단)."""
    if not isinstance(rect, list) or len(rect) != 4:
        return None
    try:
        values = [float(x) for x in rect]
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(v) for v in values):
        return None
    return values


def _safe_angle(value) -> float:
    try:
        angle = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(angle):
        return 0.0
    return angle % 360


def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_choice(value, choices, default):
    value = _safe_int(value, default)
    return value if value in choices else default


def _safe_font_scale(value) -> float:
    try:
        scale = float(value)
    except (TypeError, ValueError):
        return 1.0
    if not math.isfinite(scale):
        return 1.0
    return min(FONT_SCALE_MAX, max(FONT_SCALE_MIN, scale))


def load_config() -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            cfg.update(loaded)
    except (OSError, ValueError):
        pass
    # 손으로 고치거나 깨진 설정 파일이 백그라운드 갱신을 죽이지 않도록 정규화
    cfg["grade"] = _safe_choice(cfg.get("grade"), VALID_GRADES, DEFAULTS["grade"])
    cfg["class_num"] = _safe_choice(cfg.get("class_num"), VALID_CLASSES, DEFAULTS["class_num"])
    if cfg.get("ui_theme") not in UI_THEMES:
        cfg["ui_theme"] = DEFAULT_UI_THEME
    if not isinstance(cfg.get("background_image"), str):
        cfg["background_image"] = ""
    cfg["autostart"] = bool(cfg.get("autostart", True))
    names = cfg.get("teacher_names")
    cfg["teacher_names"] = [n.strip() for n in names
                            if isinstance(n, str) and n.strip()] if isinstance(names, list) else []
    cfg["custom_wallpaper"] = _merge_custom_wallpaper(cfg.get("custom_wallpaper"))
    return cfg


def _atomic_write_json(path: str, data) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def save_config(cfg: dict) -> None:
    _atomic_write_json(CONFIG_PATH, cfg)


def load_cache() -> dict:
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_cache_entry(key: str, value) -> None:
    cache = load_cache()
    cache[key] = value
    _atomic_write_json(CACHE_PATH, cache)


def log(msg: str) -> None:
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n"
    try:
        # 200KB 넘으면 새로 시작
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 200_000:
            os.remove(LOG_PATH)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass
