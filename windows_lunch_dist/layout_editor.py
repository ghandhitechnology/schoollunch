"""Shared layers for the browser editor and final wallpaper composition."""
import copy
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps

import config
import render
from modern_themes import is_modern_theme

LABELS = {"prompt": "날짜와 학급", "timetable": "시간표", "meal": "급식", "quote": "오늘의 명언"}


def regions(cfg, size):
    width, height = size
    if not is_modern_theme(cfg.get("ui_theme")):
        return copy.deepcopy(config.DEFAULT_CUSTOM_WALLPAPER["layout"])
    scale = min(width / 1920, height / 1080)
    px = lambda n: max(1, round(n * scale))
    left, right, top = round(width * .26), width - px(90), px(132)
    section = top + px(196)
    edge = left + round((right - left) * .40)
    meal_left = edge + px(76)
    bottom = min(height - px(110), top + px(745))
    boxes = {"prompt": [left - px(8), top - px(3), right, top + px(156)],
             "timetable": [left - px(3), section - px(4), edge + px(3), bottom + px(4)],
             "meal": [meal_left - px(3), section - px(4), right + px(2), bottom + px(4)],
             "quote": [left, height - px(152), right, height - px(70)]}
    return {key: [x0 / width, y0 / height, (x1 - x0) / width, (y1 - y0) / height]
            for key, (x0, y0, x1, y1) in boxes.items()}


def normalize(custom, cfg, size):
    custom = config._merge_custom_wallpaper(custom)
    key = "daily_layout" if is_modern_theme(cfg.get("ui_theme")) else "layout"
    layout = regions(cfg, size)
    layout.update(custom[key])
    custom[key] = {name: render._clamp_rect(rect) for name, rect in layout.items()}
    for sticker in custom["stickers"]:
        sticker["rect"] = render._clamp_rect(sticker["rect"])
    custom["editor_version"] = 2
    return custom


def panel_images(meals, timetable, cfg, size):
    source_regions = regions(cfg, size)
    if is_modern_theme(cfg.get("ui_theme")):
        transparent = dict(cfg, _transparent_daily=True)
        source = render._render_daily(meals, timetable, transparent, size)
        return {key: source.crop(tuple(render._rect_px(rect, size))) for key, rect in source_regions.items()}
    palette = render._theme(cfg.get("ui_theme"))
    font_size = max(8, round(size[1] / 54 * render._font_scale(cfg)))
    path = render.HANDWRITTEN_FONT_PATH if palette.get("handdrawn") and os.path.exists(render.HANDWRITTEN_FONT_PATH) else render.FONT_PATH
    font = ImageFont.truetype(path, font_size)
    title_font = ImageFont.truetype(path, max(10, round(font_size * 1.15)))
    result = {}
    for key, rect in source_regions.items():
        x0, y0, x1, y1 = render._rect_px(rect, size)
        image = Image.new("RGBA", (x1 - x0, y1 - y0))
        draw = ImageDraw.Draw(image)
        box = (0, 0, image.width, image.height)
        if key == "prompt":
            render._draw_prompt(draw, box, cfg, palette, font)
        elif key == "timetable":
            render._draw_timetable_panel(draw, box, timetable, cfg, palette, font, title_font)
        else:
            render._draw_meal_panel(draw, box, meals, palette, font, title_font)
        result[key] = image
    return result


def background(cfg, size):
    custom = cfg.get("custom_wallpaper", {})
    color = render._theme(cfg.get("ui_theme"))["bg"]
    return render._cover_image(custom.get("background_image", ""), size) or Image.new("RGBA", size, color)


def drawing(cfg, size):
    custom = cfg.get("custom_wallpaper", {})
    image = custom.get("_drawing_image")
    if isinstance(image, Image.Image):
        return image.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
    path = custom.get("drawing_overlay", "")
    if path and os.path.exists(path):
        with Image.open(path) as image:
            return image.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
    return Image.new("RGBA", size)


def compose(meals, timetable, cfg, size):
    custom = normalize(cfg.get("custom_wallpaper"), cfg, size)
    # Preserve the transient drawing passed by the preview/save pipeline.
    if isinstance(cfg.get("custom_wallpaper", {}).get("_drawing_image"), Image.Image):
        custom["_drawing_image"] = cfg["custom_wallpaper"]["_drawing_image"]
    cfg = dict(cfg, custom_wallpaper=custom)
    image = background(cfg, size)
    key = "daily_layout" if is_modern_theme(cfg.get("ui_theme")) else "layout"
    for name, panel in panel_images(meals, timetable, cfg, size).items():
        if name in custom["hidden_panels"]:
            continue
        x0, y0, x1, y1 = render._rect_px(custom[key][name], size)
        image.alpha_composite(panel.resize((x1 - x0, y1 - y0), Image.Resampling.LANCZOS), (x0, y0))
    for sticker in custom["stickers"]:
        if not os.path.isfile(sticker["path"]):
            continue
        with Image.open(sticker["path"]) as original:
            x0, y0, x1, y1 = render._rect_px(sticker["rect"], size)
            overlay = ImageOps.contain(original.convert("RGBA"), (x1 - x0, y1 - y0), Image.Resampling.LANCZOS)
        if sticker["angle"]:
            overlay = overlay.rotate(-sticker["angle"], expand=True, resample=Image.Resampling.BICUBIC)
        image.alpha_composite(overlay, (x0 + (x1 - x0 - overlay.width) // 2, y0 + (y1 - y0 - overlay.height) // 2))
    image.alpha_composite(drawing(cfg, size))
    return image
