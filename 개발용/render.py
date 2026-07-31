# -*- coding: utf-8 -*-
"""레트로 터미널(TUI 목업) 스타일 바탕화면 이미지를 생성한다.

문자 격자(셀) 위에 박스 드로잉 문자로 패널을 그려 진짜 터미널처럼 보이게 한다.
네오둥근모 폰트는 한글이 정확히 ASCII 2칸 폭이라 격자가 어긋나지 않는다.

레이아웃:  [왼쪽 ~23% 빈 공간(바탕화면 아이콘 자리)] [시간표 박스] [급식 박스]
"""
import os
import sys
import unicodedata

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import config

FONT_PATH = config.resource_path(os.path.join("assets", "fonts", "neodgm.ttf"))
HANDWRITTEN_FONT_PATH = config.resource_path(os.path.join("assets", "fonts", "handdrawn.ttf"))

THEMES = {
    "black_on_white": {
        "bg": (255, 255, 255),
        "text": (0, 0, 0),
        "dim": (88, 88, 88),
        "bright": (0, 0, 0),
        "accent": (0, 0, 0),
        "use_background_image": False,
        "scanline_alpha": 0,
    },
    "white_on_black": {
        "bg": (0, 0, 0),
        "text": (255, 255, 255),
        "dim": (170, 170, 170),
        "bright": (255, 255, 255),
        "accent": (255, 255, 255),
        "use_background_image": False,
        "scanline_alpha": 0,
    },
    "crayon_sketch": {
        "bg": (253, 251, 247),
        "text": (44, 44, 44),
        "dim": (124, 114, 103),
        "bright": (44, 44, 44),
        "accent": (233, 30, 99),
        "use_background_image": False,
        "scanline_alpha": 0,
        "handdrawn": True,
    },
    "cyber_terminal": {
        "bg": (10, 16, 13),
        "text": (0, 255, 102),
        "dim": (0, 168, 79),
        "bright": (162, 255, 210),
        "accent": (255, 176, 0),
        "use_background_image": False,
        "scanline_alpha": 24,
        "phosphor_glow": True,
    },
    "bulletin_bold": {
        "bg": (245, 240, 232),
        "panel_fill": (255, 253, 248),
        "text": (17, 17, 17),
        "dim": (85, 85, 85),
        "bright": (17, 17, 17),
        "accent": (255, 230, 0),
        "border": (17, 17, 17),
        "use_background_image": False,
        "scanline_alpha": 0,
        "bulletin": True,
    },
}

BULLETIN_LAYOUT = {
    "prompt": [0.24, 0.03, 0.72, 0.045],
    "timetable": [0.24, 0.08, 0.32, 0.46],
    "meal": [0.58, 0.08, 0.40, 0.52],
}

BULLETIN_FONT_FILES = {
    "hangul": os.path.join("assets", "fonts", "BlackHanSans-Regular.ttf"),
    "impact": os.path.join("assets", "fonts", "Anton-Regular.ttf"),
}

LEFT_RESERVED = 0.23   # 화면 왼쪽 빈 공간 비율 (아이콘 자리)
PREVIEW_MAX_SIZE = (640, 360)


# east_asian_width가 'A'(모호)지만 네오둥근모에서 전각으로 그려지는 문자들
_WIDE_EXTRA = {"■", "█", "▶"}


def _char_width(ch: str) -> int:
    if ch in _WIDE_EXTRA:
        return 2
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def _disp_len(s: str) -> int:
    return sum(_char_width(c) for c in s)


def _truncate(s: str, width: int) -> str:
    out, w = "", 0
    for ch in s:
        cw = _char_width(ch)
        if w + cw > width:
            return out + "…" if w < width else out
        out += ch
        w += cw
    return out


def _font_scale(cfg: dict) -> float:
    custom = cfg.get("custom_wallpaper") or {}
    return config._safe_font_scale(custom.get("font_scale", 1.0))


def _theme_key(value: str) -> str:
    return value if value in THEMES else config.DEFAULT_UI_THEME


def _theme(value: str) -> dict:
    return THEMES[_theme_key(value)]


def _format_prompt(template: str, grade: int, class_num: int) -> str:
    """사용자가 설정한 상단 프롬프트 텍스트에서 {grade}, {class_num} 플레이스홀더를 치환한다.

    잘못된 형식이면 기본 프롬프트로 평박한다.
    """
    if not template or not isinstance(template, str):
        template = config.DEFAULT_PROMPT
    try:
        return template.format(grade=grade, class_num=class_num)
    except (KeyError, ValueError, IndexError) as e:
        config.log(f"프롬프트 형식 오류, 기본값 사용: {e}")
        return config.DEFAULT_PROMPT.format(grade=grade, class_num=class_num)


class TuiCanvas:
    """문자 격자 캔버스. put()으로 글자를 놓고 paint()로 픽셀에 그린다."""

    def __init__(self, rows: int, cols: int, palette: dict):
        self.rows, self.cols = rows, cols
        self.palette = palette
        self.panels = []
        self.hlines = []
        self.grid = [[None] * cols for _ in range(rows)]  # (char, fg, bg|None)

    def put(self, r: int, c: int, text: str, fg=None, bg=None):
        fg = fg or self.palette["text"]
        col = c
        for ch in text:
            w = _char_width(ch)
            if r < 0 or r >= self.rows or col + w > self.cols:
                break
            self.grid[r][col] = (ch, fg, bg)
            for k in range(1, w):
                self.grid[r][col + k] = ("", fg, bg)  # 전각 문자 연속 칸
            col += w
        return col

    def box(self, r0: int, c0: int, h: int, w: int, title: str = "", fg=None, title_fg=None):
        if w < 4 or h < 3:  # 화면이 너무 좁으면 그리지 않는다 (음수 폭 방지)
            return
        fg = fg or self.palette["dim"]
        title_fg = title_fg or self.palette["bright"]
        self.panels.append((r0, c0, h, w))
        self.put(r0, c0, "┌" + "─" * (w - 2) + "┐", fg)
        for r in range(r0 + 1, r0 + h - 1):
            self.put(r, c0, "│", fg)
            self.put(r, c0 + w - 1, "│", fg)
        self.put(r0 + h - 1, c0, "└" + "─" * (w - 2) + "┘", fg)
        if title:
            label = f"[ {title} ]"
            self.put(r0, c0 + 2, label, title_fg)

    def hline(self, r: int, c0: int, w: int, fg=None):
        fg = fg or self.palette["dim"]
        self.hlines.append((r, c0, w, fg))
        self.put(r, c0, "├" + "─" * (w - 2) + "┤", fg)


def _liquid_background(size) -> Image.Image:
    W, H = size
    small = Image.new("RGB", (320, 180), (230, 239, 248))
    d = ImageDraw.Draw(small, "RGBA")
    d.rectangle([0, 0, 320, 180], fill=(230, 239, 248, 255))
    d.polygon([(-40, 0), (140, 0), (40, 180), (-80, 180)], fill=(177, 219, 255, 210))
    d.polygon([(110, -20), (340, -20), (250, 210), (30, 210)], fill=(255, 255, 255, 190))
    d.polygon([(210, 0), (360, 0), (340, 180), (160, 180)], fill=(201, 229, 216, 170))
    d.rectangle([0, 118, 320, 180], fill=(244, 247, 251, 170))
    small = small.filter(ImageFilter.GaussianBlur(12))
    return small.resize((W, H), Image.Resampling.BICUBIC)


def _load_background(path: str, size, palette: dict) -> Image.Image:
    """테마에 맞는 배경을 만든다."""
    img = _liquid_background(size) if palette.get("glass") else Image.new("RGB", size, palette["bg"])
    if palette.get("use_background_image") and path and os.path.exists(path):
        try:
            user = Image.open(path).convert("RGB")
            # cover 크롭
            tw, th = size
            scale = max(tw / user.width, th / user.height)
            user = user.resize((round(user.width * scale), round(user.height * scale)))
            x = (user.width - tw) // 2
            y = (user.height - th) // 2
            user = user.crop((x, y, x + tw, y + th))
            img = Image.blend(user, img, 0.58 if palette.get("glass") else 0.82)
        except Exception as e:
            config.log(f"배경 이미지 로드 실패 ({e}), 단색 배경 사용")
    return img


def _cover_image(path: str, size) -> Image.Image | None:
    if not path or not os.path.exists(path):
        return None
    try:
        user = Image.open(path).convert("RGBA")
        tw, th = size
        scale = max(tw / user.width, th / user.height)
        user = user.resize((round(user.width * scale), round(user.height * scale)), Image.Resampling.LANCZOS)
        x = (user.width - tw) // 2
        y = (user.height - th) // 2
        return user.crop((x, y, x + tw, y + th))
    except Exception as e:
        config.log(f"커스텀 이미지 로드 실패 ({e}): {path}")
        return None


def _clamp01(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, float(value)))


def _clamp_rect(rect, min_w=0.04, min_h=0.04):
    x, y, w, h = [float(v) for v in rect]
    w = _clamp01(w, min_w, 1.0)
    h = _clamp01(h, min_h, 1.0)
    x = _clamp01(x, 0.0, 1.0 - w)
    y = _clamp01(y, 0.0, 1.0 - h)
    return [x, y, w, h]


def _rect_px(rect, size):
    W, H = size
    x, y, w, h = _clamp_rect(rect)
    return [round(x * W), round(y * H), round((x + w) * W), round((y + h) * H)]


def _has_visible_drawing(path: str) -> bool:
    """드로잉 파일에 실제로 보이는(불투명) 픽셀이 있는지 확인한다."""
    if not path or not os.path.exists(path):
        return False
    try:
        with Image.open(path) as img:
            return img.convert("RGBA").getchannel("A").getbbox() is not None
    except Exception:
        return False


def _custom_enabled(cfg: dict) -> bool:
    custom = cfg.get("custom_wallpaper") or {}
    default = config.default_custom_wallpaper()
    if isinstance(custom.get("_drawing_image"), Image.Image):
        return True
    if custom.get("background_image"):
        return True
    if _has_visible_drawing(custom.get("drawing_overlay")):
        return True
    if custom.get("stickers"):
        return True
    return custom.get("layout") != default["layout"]


def _truncate_px(text: str, font, max_width: int) -> str:
    if max_width <= 0:
        return ""
    if font.getlength(text) <= max_width:
        return text
    out = ""
    for ch in text:
        if font.getlength(out + ch + "…") > max_width:
            return out + "…"
        out += ch
    return out


def _line_height(font) -> int:
    box = font.getbbox("Ag")
    return max(1, box[3] - box[1] + 4)


def _draw_text(draw: ImageDraw.ImageDraw, xy, text: str, font, fill, palette: dict) -> None:
    x, y = xy
    if palette.get("phosphor_glow"):
        if len(fill) == 3:
            fill_rgba = (fill[0], fill[1], fill[2], 255)
        else:
            fill_rgba = fill
        # Draw offset glows
        glow_fill = (fill_rgba[0], fill_rgba[1], fill_rgba[2], 64)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1)]:
            draw.text((x + dx, y + dy), text, font=font, fill=glow_fill)
    draw.text(xy, text, font=font, fill=fill)


def _apply_crt_vignette(img: Image.Image) -> None:
    W, H = img.size
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # Simple vignette by drawing concentric rectangles with soft black opacity
    for i in range(40):
        alpha = int(50 * (1 - i / 40))
        draw.rectangle([i, i, W - 1 - i, H - 1 - i], outline=(0, 0, 0, alpha))
    img.alpha_composite(overlay)


def _bulletin_system_font_paths(role: str) -> list[str]:
    paths = []
    if role == "impact":
        if sys.platform == "win32":
            windir = os.environ.get("WINDIR", r"C:\Windows")
            fonts = os.path.join(windir, "Fonts")
            paths.extend([
                os.path.join(fonts, "impact.ttf"),
                os.path.join(fonts, "arialbd.ttf"),
            ])
        elif sys.platform == "darwin":
            paths.extend([
                "/System/Library/Fonts/Supplemental/Impact.ttf",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            ])
    elif role == "hangul":
        if sys.platform == "win32":
            windir = os.environ.get("WINDIR", r"C:\Windows")
            fonts = os.path.join(windir, "Fonts")
            paths.extend([
                os.path.join(fonts, "malgunbd.ttf"),
                os.path.join(fonts, "malgun.ttf"),
            ])
        elif sys.platform == "darwin":
            paths.extend([
                "/System/Library/Fonts/AppleSDGothicNeo.ttc",
                "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            ])
        else:
            paths.extend([
                "/usr/share/fonts/truetype/nanum/NanumSquareEB.ttf",
                "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
            ])
    paths.append(FONT_PATH)
    return paths


def _load_bulletin_font(role: str, size: int):
    """hangul=Black Han Sans, impact=Anton/Impact(Latin·숫자)."""
    size = max(10, int(size))
    candidates = [config.resource_path(BULLETIN_FONT_FILES[role])] if role in BULLETIN_FONT_FILES else []
    candidates.extend(_bulletin_system_font_paths(role))
    for path in candidates:
        if not path or not os.path.exists(path):
            continue
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()


def _bulletin_hrule(draw: ImageDraw.ImageDraw, x0: int, x1: int, y: int, palette: dict, width: int = 3):
    draw.line([(x0, y), (x1, y)], fill=palette.get("border", palette["dim"]), width=width)


def _wrap_text_lines(text: str, font, max_width: int) -> list[str]:
    if max_width <= 0 or not text:
        return [""]
    words = text.replace(" · ", " · ").split(" ")
    lines, current = [], ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if font.getlength(candidate) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        if font.getlength(word) <= max_width:
            current = word
        else:
            chunk = ""
            for ch in word:
                if font.getlength(chunk + ch) > max_width:
                    if chunk:
                        lines.append(chunk)
                    chunk = ch
                else:
                    chunk += ch
            current = chunk
    if current:
        lines.append(current)
    return lines or [""]


def _bulletin_meal_sections(meals: dict, per_section_limit: int | None = None) -> list[tuple[str, list[str]]]:
    sections = []
    for key in ("조식", "중식", "석식"):
        items = list(meals.get(key, []) or [])
        if per_section_limit is not None and len(items) > per_section_limit:
            hidden = len(items) - per_section_limit
            items = items[:per_section_limit] + [f"외 {hidden}품"]
        sections.append((key, items))
    return sections


def _bulletin_period_row_h(lh: int) -> int:
    return lh + 8


def _bulletin_measure_meal_height(sections, hangul_font, impact_font, content_w: int, badge_size: int, lh: int) -> int:
    total = 0
    gap = 10
    text_x_pad = badge_size + 14
    text_w = max(40, content_w - text_x_pad)
    for _label, items in sections:
        if not items:
            block_h = max(badge_size, lh)
        else:
            joined = " · ".join(items)
            lines = _wrap_text_lines(joined, hangul_font, text_w)
            block_h = max(badge_size, len(lines) * lh + 4)
        total += block_h + gap
    return max(lh, total - gap)


def _bulletin_measure_tt_height(periods, title_h: int, lh: int, pad: int) -> int:
    rows = 1 + max(len(periods), 1)  # date + periods
    return title_h + pad + rows * _bulletin_period_row_h(lh) + pad


def _bulletin_fit_fonts(H: int, cfg: dict, periods: list, meal_sections: list):
    scale = _font_scale(cfg)
    tt_panel_h = round(H * BULLETIN_LAYOUT["timetable"][3])
    meal_panel_h = round(H * BULLETIN_LAYOUT["meal"][3])
    tt_panel_w = round(H * 16 / 9 * BULLETIN_LAYOUT["timetable"][2])  # approx; refined below
    meal_panel_w = round(H * 16 / 9 * BULLETIN_LAYOUT["meal"][2])
    pad = 16
    start = max(14, round(H / 52 * scale))
    min_size = max(11, round(H / 96))

    for body_size in range(start, min_size - 1, -1):
        hangul = _load_bulletin_font("hangul", body_size)
        title = _load_bulletin_font("hangul", max(body_size + 4, round(body_size * 1.35)))
        impact = _load_bulletin_font("impact", max(body_size + 2, round(body_size * 1.15)))
        lh = _line_height(hangul)
        title_h = _line_height(title) + 8
        badge = lh + 10
        tt_need = _bulletin_measure_tt_height(periods, title_h, lh, pad)
        meal_need = title_h + pad + _bulletin_measure_meal_height(
            meal_sections, hangul, impact, meal_panel_w - pad * 2, badge, lh)
        if tt_need <= tt_panel_h and meal_need <= meal_panel_h:
            return hangul, title, impact, lh, badge
    hangul = _load_bulletin_font("hangul", min_size)
    title = _load_bulletin_font("hangul", min_size + 3)
    impact = _load_bulletin_font("impact", min_size + 1)
    lh = _line_height(hangul)
    return hangul, title, impact, lh, lh + 8


def _bulletin_meal_sections_for_panel(meals: dict, H: int, cfg: dict, periods: list, panel_w: int):
    for limit in (None, 8, 6, 5, 4, 3, 2, 1):
        sections = _bulletin_meal_sections(meals, per_section_limit=limit)
        hangul, title, impact, lh, badge = _bulletin_fit_fonts(H, cfg, periods, sections)
        title_h = _line_height(title) + 8
        meal_panel_h = round(H * BULLETIN_LAYOUT["meal"][3])
        meal_need = title_h + 16 + _bulletin_measure_meal_height(
            sections, hangul, impact, panel_w - 32, badge, lh)
        if meal_need <= meal_panel_h:
            return sections
    return _bulletin_meal_sections(meals, per_section_limit=1)


def _draw_bulletin_panel_header(draw, rect_px, title: str, palette: dict, title_font) -> int:
    x0, y0, x1, _ = rect_px
    fill = palette.get("panel_fill", palette["bg"])
    border = palette.get("border", palette["dim"])
    draw.rectangle(rect_px, fill=fill, outline=border, width=4)
    pad = 14
    y = y0 + pad
    _draw_text(draw, (x0 + pad, y), title, title_font, palette["bright"], palette)
    y += _line_height(title_font) + 6
    _bulletin_hrule(draw, x0 + pad, x1 - pad, y, palette)
    return y + 10


def _draw_period_badge(draw, x: int, y: int, period_num: int, hangul_font, impact_font, lh: int, palette: dict) -> tuple[int, int]:
    label = f"{period_num}교시"
    pad_x, pad_y = 8, 4
    w = int(max(hangul_font.getlength(label), impact_font.getlength(label))) + pad_x * 2
    h = lh + pad_y * 2
    draw.rectangle([x, y, x + w, y + h], fill=palette.get("border", (17, 17, 17)))
    _draw_text(draw, (x + pad_x, y + pad_y - 1), label, hangul_font, (255, 255, 255), palette)
    return w, h


def _draw_meal_badge(draw, x: int, y: int, label: str, hangul_font, size: int, palette: dict) -> int:
    sq = size
    draw.rectangle([x, y, x + sq, y + sq], fill=palette["accent"], outline=palette.get("border", (17, 17, 17)), width=2)
    tw = hangul_font.getlength(label)
    th = _line_height(hangul_font)
    tx = x + (sq - tw) / 2
    ty = y + (sq - th) / 2 - 1
    _draw_text(draw, (tx, ty), label, hangul_font, palette.get("border", palette["text"]), palette)
    return sq


def _draw_bulletin_timetable(draw, rect_px, timetable, cfg, palette, hangul_font, title_font, impact_font, lh, badge_h):
    grade, cls = cfg.get("grade", 1), cfg.get("class_num", 1)
    x0, _, x1, y1 = rect_px
    pad = 14
    y = _draw_bulletin_panel_header(draw, rect_px, f"시간표 {grade}-{cls}", palette, title_font)
    max_w = x1 - x0 - pad * 2
    date_label = f"{timetable.get('date', '')} ({timetable.get('weekday_label', '')})"
    if timetable.get("_cached"):
        date_label += "  [캐시]"
    _draw_text(draw, (x0 + pad, y), _truncate_px(date_label, hangul_font, max_w),
               hangul_font, palette["dim"], palette)
    y += _bulletin_period_row_h(lh)
    _bulletin_hrule(draw, x0 + pad, x1 - pad, y - 4, palette, width=2)
    y += 6
    periods = timetable.get("periods", [])
    if not periods:
        _draw_text(draw, (x0 + pad, y), "시간표 정보 없음", hangul_font, palette["dim"], palette)
        return
    badge_font = _load_bulletin_font("hangul", max(10, lh))
    for p in periods:
        row_h = _bulletin_period_row_h(lh)
        if y + row_h > y1 - pad:
            break
        badge_w, badge_box_h = _draw_period_badge(
            draw, x0 + pad, y, p["period"], badge_font, impact_font, lh, palette)
        time_str = p.get("time") or ""
        subj = p.get("subject") or "-"
        teacher = p.get("teacher") or ""
        detail = f"{time_str}  |  {subj}"
        if teacher:
            detail += f"  {teacher}"
        detail_x = x0 + pad + badge_w + 12
        _draw_text(draw, (detail_x, y + max(0, (badge_box_h - lh) // 2)),
                   _truncate_px(detail, hangul_font, x1 - pad - detail_x),
                   hangul_font, palette["text"], palette)
        y += row_h


def _draw_bulletin_meals(draw, rect_px, meals, palette, hangul_font, title_font, lh, badge_size, sections):
    x0, _, x1, y1 = rect_px
    pad = 14
    title = "오늘의 급식"
    if meals.get("_cached"):
        title += " [캐시]"
    y = _draw_bulletin_panel_header(draw, rect_px, title, palette, title_font)
    badge_font = _load_bulletin_font("hangul", max(10, int(badge_size * 0.55)))
    text_x = pad + badge_size + 14
    text_w = max(40, (x1 - x0) - text_x - pad)
    gap = 10
    for label, items in sections:
        if y + badge_size > y1 - pad:
            break
        _draw_meal_badge(draw, x0 + pad, y, label, badge_font, badge_size, palette)
        if not items:
            _draw_text(draw, (x0 + text_x, y + 2), "급식 정보 없음", hangul_font, palette["dim"], palette)
            block_h = max(badge_size, lh)
        else:
            joined = " · ".join(items)
            lines = _wrap_text_lines(joined, hangul_font, text_w)
            for i, line in enumerate(lines):
                if y + i * lh > y1 - pad:
                    break
                _draw_text(draw, (x0 + text_x, y + i * lh), line, hangul_font, palette["text"], palette)
            block_h = max(badge_size, len(lines) * lh + 2)
        y += block_h + gap


def _render_bulletin_wallpaper(meals: dict, timetable: dict, cfg: dict, size) -> Image.Image:
    W, H = size
    palette = _theme(cfg.get("ui_theme", config.DEFAULT_UI_THEME))
    img = _load_background(cfg.get("background_image", ""), (W, H), palette).convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")

    periods = timetable.get("periods", [])
    meal_rect = _rect_px(BULLETIN_LAYOUT["meal"], (W, H))
    meal_w = meal_rect[2] - meal_rect[0]
    meal_sections = _bulletin_meal_sections_for_panel(meals, H, cfg, periods, meal_w)
    hangul_font, title_font, impact_font, lh, badge_size = _bulletin_fit_fonts(
        H, cfg, periods, meal_sections)
    prompt_font = _load_bulletin_font("impact", max(12, round(lh * 0.95)))

    grade, cls = cfg.get("grade", 1), cfg.get("class_num", 1)
    prompt = _format_prompt(cfg.get("prompt_text"), grade, cls) + " █"
    prompt_rect = _rect_px(BULLETIN_LAYOUT["prompt"], (W, H))
    _draw_text(draw, (prompt_rect[0], prompt_rect[1]),
               _truncate_px(prompt, prompt_font, prompt_rect[2] - prompt_rect[0]),
               prompt_font, palette.get("border", palette["text"]), palette)

    tt_rect = _rect_px(BULLETIN_LAYOUT["timetable"], (W, H))
    _draw_bulletin_timetable(draw, tt_rect, timetable, cfg, palette,
                             hangul_font, title_font, impact_font, lh, badge_size)
    _draw_bulletin_meals(draw, meal_rect, meals, palette, hangul_font, title_font, lh, badge_size, meal_sections)

    bottom = max(tt_rect[3], meal_rect[3]) + round(H * 0.02)
    if bottom < H - lh and (meals.get("_cached") or timetable.get("_cached")):
        _draw_text(draw, (tt_rect[0], bottom),
                   "오프라인 — 마지막으로 받은 정보를 표시 중",
                   hangul_font, palette["dim"], palette)
    return img


def _draw_panel(draw: ImageDraw.ImageDraw, rect_px, title: str, palette: dict, font, title_font):
    x0, y0, x1, y1 = rect_px
    if palette.get("bulletin"):
        return _draw_bulletin_panel_header(
            draw, rect_px, title.replace("[ ", "").replace(" ]", ""), palette, title_font)
    if palette.get("handdrawn"):
        _draw_wobbly_line(draw, x0, y0, x1, y0, palette["dim"], width=3)
        _draw_wobbly_line(draw, x1, y0, x1, y1, palette["dim"], width=3)
        _draw_wobbly_line(draw, x1, y1, x0, y1, palette["dim"], width=3)
        _draw_wobbly_line(draw, x0, y1, x0, y0, palette["dim"], width=3)
    elif palette.get("glass"):
        shadow = palette.get("panel_shadow", (20, 35, 60, 42))
        fill = palette.get("panel_fill", (255, 255, 255, 118))
        outline = palette.get("panel_outline", (255, 255, 255, 210))
        draw.rounded_rectangle([x0 + 6, y0 + 8, x1 + 6, y1 + 8], radius=18, fill=shadow)
        draw.rounded_rectangle([x0, y0, x1, y1], radius=18, fill=fill, outline=outline, width=2)
    else:
        draw.rectangle([x0, y0, x1, y1], outline=palette["dim"], width=2)
    _draw_text(draw, (x0 + 12, y0 + 8), f"[ {title} ]", title_font, palette["bright"], palette)
    return y0 + 12 + _line_height(title_font)


def _draw_prompt(draw: ImageDraw.ImageDraw, rect_px, cfg: dict, palette: dict, font):
    x0, y0, x1, _ = rect_px
    grade, cls = cfg.get("grade", 1), cfg.get("class_num", 1)
    prompt = _format_prompt(cfg.get("prompt_text"), grade, cls) + " █"
    _draw_text(draw, (x0, y0), _truncate_px(prompt, font, x1 - x0), font, palette["text"], palette)


def _draw_timetable_panel(draw: ImageDraw.ImageDraw, rect_px, timetable: dict, cfg: dict, palette: dict, font, title_font):
    grade, cls = cfg.get("grade", 1), cfg.get("class_num", 1)
    y = _draw_panel(draw, rect_px, f"시간표 {grade}-{cls}", palette, font, title_font)
    x0, _, x1, y1 = rect_px
    pad = 12
    line_h = _line_height(font)
    max_w = x1 - x0 - pad * 2
    date_label = f"{timetable.get('date', '')} ({timetable.get('weekday_label', '')})"
    if timetable.get("_cached"):
        date_label += "  [캐시]"
    lines = [date_label]
    periods = timetable.get("periods", [])
    if periods:
        for p in periods:
            lines.append(f"{p['period']}교시 {p.get('time', ''):<5}  {p.get('subject') or '-'}  {p.get('teacher', '')}")
    else:
        lines.append("시간표 정보 없음")
    for line in lines:
        if y + line_h > y1 - pad:
            break
        _draw_text(draw, (x0 + pad, y), _truncate_px(line, font, max_w), font, palette["text"], palette)
        y += line_h


def _draw_meal_panel(draw: ImageDraw.ImageDraw, rect_px, meals: dict, palette: dict, font, title_font):
    title = "오늘의 급식"
    if meals.get("_cached"):
        title += " [캐시]"
    y = _draw_panel(draw, rect_px, title, palette, font, title_font)
    x0, _, x1, y1 = rect_px
    pad = 12
    line_h = _line_height(font)
    max_w = x1 - x0 - pad * 2
    lines = []
    for label, key in (("아침", "조식"), ("점심", "중식"), ("저녁", "석식")):
        lines.append(f"■ {label}")
        items = meals.get(key, [])
        if not items:
            lines.append("  급식 정보 없음")
        else:
            lines.extend(f"  · {item}" for item in items)
    for line in lines:
        if y + line_h > y1 - pad:
            break
        fill = palette["accent"] if line.startswith("■") else palette["text"]
        _draw_text(draw, (x0 + pad, y), _truncate_px(line, font, max_w), font, fill, palette)
        y += line_h


def _apply_custom_layers(img: Image.Image, cfg: dict, size):
    custom = cfg.get("custom_wallpaper") or config.default_custom_wallpaper()
    custom_bg = _cover_image(custom.get("background_image", ""), size)
    if custom_bg:
        img.alpha_composite(custom_bg)
    drawing_image = custom.get("_drawing_image")
    if isinstance(drawing_image, Image.Image):
        try:
            overlay = drawing_image.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
            img.alpha_composite(overlay)
        except Exception as e:
            config.log(f"드로잉 오버레이 미리보기 실패 ({e})")
    else:
        drawing_path = custom.get("drawing_overlay", "")
        try:
            if drawing_path and os.path.exists(drawing_path):
                overlay = Image.open(drawing_path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
                img.alpha_composite(overlay)
        except Exception as e:
            config.log(f"드로잉 오버레이 로드 실패 ({e}): {drawing_path}")
    for sticker in custom.get("stickers", []):
        sticker_path = sticker.get("path", "")
        if not sticker_path or not os.path.exists(sticker_path):
            continue
        x0, y0, x1, y1 = _rect_px(sticker.get("rect", [0, 0, 0.1, 0.1]), size)
        if x1 <= x0 or y1 <= y0:
            continue
        try:
            original = Image.open(sticker_path).convert("RGBA")
            original.thumbnail((x1 - x0, y1 - y0), Image.Resampling.LANCZOS)
            angle = config._safe_angle(sticker.get("angle", 0))
            if angle:
                original = original.rotate(-angle, expand=True, resample=Image.Resampling.BICUBIC)
            paste_x = x0 + ((x1 - x0) - original.width) // 2
            paste_y = y0 + ((y1 - y0) - original.height) // 2
            img.alpha_composite(original, (paste_x, paste_y))
        except Exception as e:
            config.log(f"스티커 렌더 실패 ({e}): {sticker_path}")


def _render_custom_wallpaper(meals: dict, timetable: dict, cfg: dict, size, palette: dict) -> Image.Image:
    W, H = size
    img = _load_background("", (W, H), palette).convert("RGBA")
    _apply_custom_layers(img, cfg, size)
    draw = ImageDraw.Draw(img, "RGBA")
    font_size = max(8, round(H / 54 * _font_scale(cfg)))
    title_size = max(10, round(font_size * 1.15))
    custom = cfg.get("custom_wallpaper") or config.default_custom_wallpaper()
    layout = custom.get("layout", config.default_custom_wallpaper()["layout"])

    if palette.get("bulletin"):
        periods = timetable.get("periods", [])
        meal_rect = _rect_px(layout.get("meal", BULLETIN_LAYOUT["meal"]), size)
        meal_w = meal_rect[2] - meal_rect[0]
        meal_sections = _bulletin_meal_sections_for_panel(meals, H, cfg, periods, meal_w)
        hangul_font, title_font, impact_font, lh, badge_size = _bulletin_fit_fonts(
            H, cfg, periods, meal_sections)
        prompt_font = _load_bulletin_font("impact", max(12, round(lh * 0.95)))
        grade, cls = cfg.get("grade", 1), cfg.get("class_num", 1)
        prompt = _format_prompt(cfg.get("prompt_text"), grade, cls) + " █"
        prompt_rect = _rect_px(layout.get("prompt", BULLETIN_LAYOUT["prompt"]), size)
        _draw_text(draw, (prompt_rect[0], prompt_rect[1]),
                   _truncate_px(prompt, prompt_font, prompt_rect[2] - prompt_rect[0]),
                   prompt_font, palette.get("border", palette["text"]), palette)
        _draw_bulletin_timetable(draw, _rect_px(layout.get("timetable", BULLETIN_LAYOUT["timetable"]), size),
                                 timetable, cfg, palette, hangul_font, title_font, impact_font, lh, badge_size)
        _draw_bulletin_meals(draw, meal_rect, meals, palette, hangul_font, title_font, lh, badge_size, meal_sections)
        return img

    font_path = HANDWRITTEN_FONT_PATH if palette.get("handdrawn") and os.path.exists(HANDWRITTEN_FONT_PATH) else FONT_PATH
    font = ImageFont.truetype(font_path, font_size)
    title_font = ImageFont.truetype(font_path, title_size)
    _draw_prompt(draw, _rect_px(layout.get("prompt", config.DEFAULT_CUSTOM_WALLPAPER["layout"]["prompt"]), size),
                 cfg, palette, font)
    _draw_timetable_panel(draw, _rect_px(layout.get("timetable", config.DEFAULT_CUSTOM_WALLPAPER["layout"]["timetable"]), size),
                          timetable, cfg, palette, font, title_font)
    _draw_meal_panel(draw, _rect_px(layout.get("meal", config.DEFAULT_CUSTOM_WALLPAPER["layout"]["meal"]), size),
                     meals, palette, font, title_font)
    return img


def _build_screen(canvas: TuiCanvas, meals: dict, timetable: dict, cfg: dict, content_c0: int):
    """캔버스에 전체 화면 내용을 배치한다."""
    palette = canvas.palette
    grade, cls = cfg.get("grade", 1), cfg.get("class_num", 1)
    c0 = content_c0

    # ── 가짜 프롬프트 ───────────────────────────────────
    prompt = _format_prompt(cfg.get("prompt_text"), grade, cls)
    end = canvas.put(0, c0, prompt, palette["text"])
    canvas.put(0, end + 1, "█", palette["text"])

    top = 2  # 박스 시작 행

    # ── 시간표 박스 (왼쪽) ───────────────────────────────
    tt_w = 38
    periods = timetable.get("periods", [])
    tt_h = max(len(periods), 1) + 5
    canvas.box(top, c0, tt_h, tt_w, f"시간표 {grade}-{cls}")
    date_label = f"{timetable.get('date', '')} ({timetable.get('weekday_label', '')})"
    if timetable.get("_cached"):
        date_label += "  [캐시]"
    canvas.put(top + 1, c0 + 2, date_label, palette["bright"])
    canvas.hline(top + 2, c0, tt_w)
    if periods:
        for i, p in enumerate(periods):
            subj = p["subject"] or "─"
            canvas.put(top + 3 + i, c0 + 2, f"{p['period']}교시", palette["accent"])
            canvas.put(top + 3 + i, c0 + 8, p["time"], palette["dim"])
            canvas.put(top + 3 + i, c0 + 15, _truncate(subj, 14), palette["text"] if p["subject"] else palette["dim"])
            canvas.put(top + 3 + i, c0 + 30, _truncate(p["teacher"], 6), palette["dim"])
    else:
        canvas.put(top + 3, c0 + 2, "시간표 정보 없음", palette["dim"])

    # ── 급식 박스 (오른쪽) ───────────────────────────────
    ml_c0 = c0 + tt_w + 3
    ml_w = canvas.cols - ml_c0 - 2
    sections = [("아침", "조식"), ("점심", "중식"), ("저녁", "석식")]

    # 높이 계산: 섹션마다 헤더 1줄 + 메뉴 줄들
    lines = 0
    for _, key in sections:
        lines += 1 + max(len(meals.get(key, [])), 1)
    ml_h = lines + 2 + 2  # 테두리 2 + 구분선 2

    title = "오늘의 급식"
    if meals.get("_cached"):
        title += " [캐시]"
    canvas.box(top, ml_c0, ml_h, ml_w, title)

    r = top + 1
    for idx, (label, key) in enumerate(sections):
        if idx > 0:
            canvas.hline(r, ml_c0, ml_w)
            r += 1
        canvas.put(r, ml_c0 + 2, f"■ {label}", palette["accent"])
        r += 1
        items = meals.get(key, [])
        if not items:
            canvas.put(r, ml_c0 + 4, "급식 정보 없음", palette["dim"])
            r += 1
        for item in items:
            canvas.put(r, ml_c0 + 4, "· " + _truncate(item, ml_w - 8), palette["text"])
            r += 1

    # ── 하단 상태줄 ─────────────────────────────────────
    bottom = max(top + tt_h, top + ml_h) + 1
    if bottom < canvas.rows and (meals.get("_cached") or timetable.get("_cached")):
        canvas.put(bottom, c0, "─ ! 오프라인: 마지막으로 받은 정보를 표시 중 ─", palette["dim"])


def _draw_wobbly_line(draw: ImageDraw.ImageDraw, x0: float, y0: float, x1: float, y1: float, fill, width=3, jitter=1.5):
    import random
    if len(fill) == 3:
        fill = (fill[0], fill[1], fill[2], 255)
    
    # We draw 3 sketchy paths overlapping slightly
    for offset_scale in [0.4, 0.7, 1.0]:
        alpha = int(100 + 100 * offset_scale)
        stroke_color = (fill[0], fill[1], fill[2], alpha)
        
        length = ((x1 - x0)**2 + (y1 - y0)**2)**0.5
        if length < 2:
            continue
        
        num_segments = max(1, int(length / 10))
        dx = (x1 - x0) / num_segments
        dy = (y1 - y0) / num_segments
        
        points = [(x0, y0)]
        for i in range(1, num_segments):
            px = x0 + i * dx + random.uniform(-jitter, jitter) * offset_scale
            py = y0 + i * dy + random.uniform(-jitter, jitter) * offset_scale
            points.append((px, py))
        points.append((x1, y1))
        
        for j in range(len(points) - 1):
            draw.line([points[j], points[j+1]], fill=stroke_color, width=width)


def _paint_handdrawn_panels(img: Image.Image, canvas: TuiCanvas, x_off: int, y_off: int,
                            cell_w: int, cell_h: int) -> None:
    draw = ImageDraw.Draw(img, "RGBA")
    
    # Draw wobbly box borders
    for r0, c0, h, w in canvas.panels:
        x0 = x_off + c0 * cell_w + cell_w // 2
        y0 = y_off + r0 * cell_h + cell_h // 2
        x1 = x_off + (c0 + w - 1) * cell_w + cell_w // 2
        y1 = y_off + (r0 + h - 1) * cell_h + cell_h // 2
        
        # Top line
        _draw_wobbly_line(draw, x0, y0, x1, y0, canvas.palette["dim"], width=3)
        # Right line
        _draw_wobbly_line(draw, x1, y0, x1, y1, canvas.palette["dim"], width=3)
        # Bottom line
        _draw_wobbly_line(draw, x1, y1, x0, y1, canvas.palette["dim"], width=3)
        # Left line
        _draw_wobbly_line(draw, x0, y1, x0, y0, canvas.palette["dim"], width=3)

    # Draw wobbly horizontal lines
    for r, c0, w, fg in canvas.hlines:
        x0 = x_off + c0 * cell_w + cell_w // 2
        y0 = y_off + r * cell_h + cell_h // 2
        x1 = x_off + (c0 + w - 1) * cell_w + cell_w // 2
        y1 = y0
        _draw_wobbly_line(draw, x0, y0, x1, y1, fg, width=2)


def _paint_glass_panels(img: Image.Image, canvas: TuiCanvas, x_off: int, y_off: int,
                        cell_w: int, cell_h: int) -> None:
    palette = canvas.palette
    if not palette.get("glass"):
        return

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay, "RGBA")
    for r0, c0, h, w in canvas.panels:
        x0 = x_off + c0 * cell_w - 10
        y0 = y_off + r0 * cell_h - 8
        x1 = x_off + (c0 + w) * cell_w + 10
        y1 = y_off + (r0 + h) * cell_h + 8
        if x1 <= x0 or y1 <= y0:
            continue
        radius = min(18, (x1 - x0) // 2, (y1 - y0) // 2)
        d.rounded_rectangle([x0 + 5, y0 + 8, x1 + 5, y1 + 8],
                            radius=radius, fill=palette["panel_shadow"])
        d.rounded_rectangle([x0, y0, x1, y1],
                            radius=radius, fill=palette["panel_fill"],
                            outline=palette["panel_outline"], width=1)
        d.arc([x0 + 8, y0 + 8, x1 - 8, y1 - 8], 205, 300,
              fill=(255, 255, 255, 155), width=2)
    img.alpha_composite(overlay)


def render_wallpaper_image(meals: dict, timetable: dict, cfg: dict, size=None) -> Image.Image:
    if size is None:
        size = detect_resolution()
    W, H = size
    palette = _theme(cfg.get("ui_theme", config.DEFAULT_UI_THEME))
    if palette.get("bulletin") and not _custom_enabled(cfg):
        return _render_bulletin_wallpaper(meals, timetable, cfg, (W, H))
    if _custom_enabled(cfg):
        return _render_custom_wallpaper(meals, timetable, cfg, (W, H), palette)

    # 픽셀 폰트는 16px 배수에서 또렷하다 (글자 크기 설정으로 추가 보정)
    font_size = max(8, round(16 * max(1, round(H / 1080 * 2)) * _font_scale(cfg)))
    font_path = HANDWRITTEN_FONT_PATH if palette.get("handdrawn") and os.path.exists(HANDWRITTEN_FONT_PATH) else FONT_PATH
    font = ImageFont.truetype(font_path, font_size)
    cell_w = round(font.getlength("A"))
    cell_h = font_size + 2

    img = _load_background(cfg.get("background_image", ""), (W, H), palette).convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")

    cols, rows = W // cell_w, (H - cell_h) // cell_h
    canvas = TuiCanvas(rows, cols, palette)
    content_c0 = int(cols * LEFT_RESERVED) + 1
    _build_screen(canvas, meals, timetable, cfg, content_c0)

    # 격자 → 픽셀 (배경을 모두 먼저 칠하고 글자를 그려야 전각 글자가 안 잘린다)
    x_off = (W - cols * cell_w) // 2
    y_off = cell_h // 2
    if palette.get("handdrawn"):
        _paint_handdrawn_panels(img, canvas, x_off, y_off, cell_w, cell_h)
    else:
        _paint_glass_panels(img, canvas, x_off, y_off, cell_w, cell_h)
    for r in range(rows):
        for c in range(cols):
            cell = canvas.grid[r][c]
            if cell and cell[2]:
                x, y = x_off + c * cell_w, y_off + r * cell_h
                draw.rectangle([x, y, x + cell_w - 1, y + cell_h - 1], fill=cell[2])
    BOX_CHARS = {"┌", "─", "┐", "│", "└", "┘", "├", "┤"}
    for r in range(rows):
        for c in range(cols):
            cell = canvas.grid[r][c]
            if cell and cell[0] and cell[0] != " ":
                if palette.get("handdrawn") and cell[0] in BOX_CHARS:
                    continue
                _draw_text(draw, (x_off + c * cell_w, y_off + r * cell_h),
                           cell[0], font, cell[1], palette)

    scanline_alpha = palette.get("scanline_alpha", 0)
    if scanline_alpha:
        for y in range(0, H, 3):
            draw.line([(0, y), (W, y)], fill=(0, 0, 0, scanline_alpha))

    if palette.get("phosphor_glow"):
        _apply_crt_vignette(img)

    return img


def render_preview_image(meals: dict, timetable: dict, cfg: dict, size) -> Image.Image:
    """낮은 해상도에서 렌더한 뒤 UI 크기로 확대해 라이브 미리보기 부하를 제한한다."""
    width, height = max(1, int(size[0])), max(1, int(size[1]))
    max_width, max_height = PREVIEW_MAX_SIZE
    scale = min(1.0, max_width / width, max_height / height)
    render_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    img = render_wallpaper_image(meals, timetable, cfg, size=render_size).convert("RGB")
    if render_size != (width, height):
        img = img.resize((width, height), Image.Resampling.BILINEAR)
    return img


def render_wallpaper(meals: dict, timetable: dict, cfg: dict,
                     size=None, out_path=None) -> str:
    img = render_wallpaper_image(meals, timetable, cfg, size=size)
    out_path = out_path or config.WALLPAPER_PATH
    img.convert("RGB").save(out_path)
    return out_path


def detect_resolution() -> tuple:
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    if sys.platform == "darwin":
        # tkinter로 측정하면 두 번째 Tk 루트가 생기고, 백그라운드 스레드에서
        # 불리면 UI 전체가 회색으로 멈춘다. CoreGraphics는 스레드 안전하다.
        try:
            import ctypes
            cg = ctypes.CDLL(
                "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
            cg.CGMainDisplayID.restype = ctypes.c_uint32
            cg.CGDisplayPixelsWide.restype = ctypes.c_size_t
            cg.CGDisplayPixelsWide.argtypes = [ctypes.c_uint32]
            cg.CGDisplayPixelsHigh.restype = ctypes.c_size_t
            cg.CGDisplayPixelsHigh.argtypes = [ctypes.c_uint32]
            display = cg.CGMainDisplayID()
            width = int(cg.CGDisplayPixelsWide(display))
            height = int(cg.CGDisplayPixelsHigh(display))
            if width > 0 and height > 0:
                return width, height
        except Exception as e:
            config.log(f"macOS 해상도 감지 실패, 기본값 사용: {e!r}")
    return 1920, 1080  # 개발 환경 기본값


if __name__ == "__main__":
    import fetch_meal
    import fetch_timetable

    cfg = config.load_config()
    meals = fetch_meal.fetch_meals(cfg)
    tt = fetch_timetable.fetch_today(cfg)
    out = render_wallpaper(meals, tt, cfg, size=(1920, 1080),
                           out_path=os.path.join(os.path.dirname(__file__), "preview.png"))
    print("저장:", out)
