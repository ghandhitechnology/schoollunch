# -*- coding: utf-8 -*-
"""앱 UI 디자인 토큰.

앱 창의 외관은 바탕화면 테마(흑백/백흑/감성/컴퓨터)와 분리되어 있다.
바탕화면은 레트로 터미널 그대로 두고, 앱 창은 시스템 라이트/다크를 따르는
중립적인 모습 하나만 쓴다. 바탕화면 테마 색은 render.THEMES 가 갖고 있다.

색은 모두 (라이트, 다크) 튜플이다 — CustomTkinter 가 그대로 받는 형식.
"""
import os
import sys

import customtkinter as ctk

import config

# ── 간격 / 반경 / 타이포 ──
SPACE = {"xs": 4, "sm": 8, "md": 14, "lg": 20, "xl": 28}
RADIUS = {"sm": 6, "md": 10, "lg": 14}
TYPE = {"display": 22, "title": 15, "body": 13, "caption": 11, "mono": 12}

# ── 색 ── (라이트, 다크)
COLORS = {
    "surface":      ("#ffffff", "#1c1c1e"),
    "surface_alt":  ("#f4f4f7", "#2a2a2d"),
    "sidebar":      ("#f0f0f4", "#151517"),
    "border":       ("#dcdce2", "#3a3a3d"),
    "text":         ("#111114", "#f2f2f7"),
    "text_dim":     ("#6b6b73", "#9a9aa2"),
    "accent":       ("#2563eb", "#3b82f6"),
    "accent_hover": ("#1d4ed8", "#60a5fa"),
    "nav_active":   ("#e2e8f8", "#2e3440"),
    "nav_hover":    ("#e8e8ee", "#232326"),
    "canvas":       ("#e6e6ec", "#242427"),
    "ok":           ("#15803d", "#4ade80"),
    "warn":         ("#b45309", "#fbbf24"),
    "error":        ("#b91c1c", "#f87171"),
}

_FONT_REGISTERED = False


def _register_windows_font():
    """번들된 픽셀 폰트를 Windows 에 런타임 등록 (데이터 표시용 mono 폰트)."""
    global _FONT_REGISTERED
    if _FONT_REGISTERED or sys.platform != "win32":
        return
    import ctypes
    font_path = config.resource_path(os.path.join("assets", "fonts", "neodgm.ttf"))
    if os.path.exists(font_path):
        ctypes.windll.gdi32.AddFontResourceExW(font_path, 0x10, 0)
        _FONT_REGISTERED = True


def font(size=TYPE["body"], weight="normal"):
    """앱 크롬용 시스템 UI 폰트. 한글 자소가 온전한 것으로 고른다."""
    if sys.platform == "win32":
        return ("Malgun Gothic", size, weight)
    if sys.platform == "darwin":
        return ("Apple SD Gothic Neo", size, weight)
    return ("Noto Sans CJK KR", size, weight)


def mono_font(size=TYPE["mono"], weight="normal"):
    """시간표·급식 표시용 고정폭 폰트. 줄 맞춤이 필요하고 레트로 정체성이 남는 곳."""
    if sys.platform == "win32":
        _register_windows_font()
        return ("NeoDunggeunmo", size, weight)
    if sys.platform == "darwin":
        return ("Menlo", size, weight)
    return ("DejaVu Sans Mono", size, weight)


def resolve(token):
    """(라이트, 다크) 색 튜플을 현재 모드의 hex 하나로 푼다.

    tk.Canvas 처럼 CTk 색 튜플을 못 받는 곳에서 쓴다 (커스텀 에디터의 오버레이).
    """
    value = COLORS.get(token, token)
    if isinstance(value, (tuple, list)):
        return value[1] if ctk.get_appearance_mode().lower() == "dark" else value[0]
    return value


def theme_key(value):
    """바탕화면 테마 키를 유효한 값으로 정규화한다."""
    return value if value in config.UI_THEMES else config.DEFAULT_UI_THEME


def init_appearance():
    """앱 창 외관을 시스템 라이트/다크에 맞춘다. 창을 만들기 전에 호출한다."""
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")


def card(parent, **kw):
    """테두리가 있는 패널. 창 안의 모든 구획은 이걸로 만든다."""
    opts = dict(fg_color=COLORS["surface"], border_color=COLORS["border"],
                border_width=1, corner_radius=RADIUS["md"])
    opts.update(kw)
    return ctk.CTkFrame(parent, **opts)


def section_label(parent, text, **kw):
    opts = dict(text=text, font=font(TYPE["caption"], "bold"),
                text_color=COLORS["text_dim"], anchor="w")
    opts.update(kw)
    return ctk.CTkLabel(parent, **opts)
