# -*- coding: utf-8 -*-
"""앱 UI와 커스텀 에디터가 함께 쓰는 테마 공통 코드.

macOS의 Aqua tk.Button은 bg/fg 설정을 무시해 테마 색이 깨지므로,
모든 버튼은 Label 기반 ThemedButton으로 그린다.
"""
import os
import sys
import tkinter as tk

import config

PALETTES = {
    "black_on_white": {
        "bg": "#ffffff",
        "panel": "#ffffff",
        "panel_alt": "#f4f4f4",
        "fg": "#000000",
        "dim": "#666666",
        "border": "#000000",
        "accent": "#000000",
        "button_fg": "#ffffff",
        "canvas_bg": "#f2f2f2",
    },
    "white_on_black": {
        "bg": "#000000",
        "panel": "#000000",
        "panel_alt": "#101010",
        "fg": "#ffffff",
        "dim": "#aaaaaa",
        "border": "#ffffff",
        "accent": "#ffffff",
        "button_fg": "#000000",
        "canvas_bg": "#111111",
    },
    "liquid_glass": {
        "bg": "#e8f1fa",
        "panel": "#f7fbff",
        "panel_alt": "#eef5fb",
        "fg": "#142033",
        "dim": "#627183",
        "border": "#9fb7d8",
        "accent": "#245cff",
        "button_fg": "#ffffff",
        "canvas_bg": "#dbeafe",
    },
    "crayon_sketch": {
        "bg": "#fdfbf7",
        "panel": "#fdfbf7",
        "panel_alt": "#f5f0e6",
        "fg": "#2c2c2c",
        "dim": "#7c7267",
        "border": "#2c2c2c",
        "accent": "#e91e63",
        "button_fg": "#ffffff",
        "canvas_bg": "#f5f0e6",
    },
}

_FONT_REGISTERED = False


def _register_windows_font():
    global _FONT_REGISTERED
    if _FONT_REGISTERED or sys.platform != "win32":
        return
    import ctypes
    font_path = config.resource_path(os.path.join("assets", "fonts", "neodgm.ttf"))
    if os.path.exists(font_path):
        ctypes.windll.gdi32.AddFontResourceExW(font_path, 0x10, 0)
        _FONT_REGISTERED = True


def font(size=13, weight="normal"):
    if sys.platform == "win32":
        _register_windows_font()
        return ("NeoDunggeunmo", size, weight)
    if sys.platform == "darwin":
        return ("Menlo", size, weight)
    return ("DejaVu Sans Mono", size, weight)


def theme_key(value):
    return value if value in PALETTES else config.DEFAULT_UI_THEME


def palette(value):
    return PALETTES[theme_key(value)]


class ThemedButton(tk.Label):
    """모든 OS에서 테마 색이 그대로 적용되는 평면 버튼 (hover/press/disabled 지원)."""

    def __init__(self, parent, text, command, font=None, padx=12, pady=6):
        super().__init__(parent, text=text, font=font, padx=padx, pady=pady,
                         cursor="hand2", highlightthickness=1)
        self._command = command
        self._palette = None
        self._enabled = True
        self._selected = False
        self._hover = False
        self._pressed = False
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def set_palette(self, p):
        self._palette = p
        self._refresh()

    def set_enabled(self, enabled):
        self._enabled = bool(enabled)
        self.configure(cursor="hand2" if self._enabled else "arrow")
        self._refresh()

    def set_selected(self, selected):
        self._selected = bool(selected)
        self._refresh()

    def _refresh(self):
        p = self._palette
        if not p or not self.winfo_exists():
            return
        if not self._enabled:
            bg, fg = p["panel_alt"], p["dim"]
        elif self._selected or (self._pressed and self._hover):
            bg, fg = p["panel"], p["accent"]
        elif self._hover:
            bg, fg = p["dim"], p["button_fg"]
        else:
            bg, fg = p["accent"], p["button_fg"]
        self.configure(bg=bg, fg=fg,
                       highlightbackground=p["border"], highlightcolor=p["border"])

    def _on_enter(self, _event):
        self._hover = True
        self._refresh()

    def _on_leave(self, _event):
        self._hover = False
        self._refresh()

    def _on_press(self, _event):
        if self._enabled:
            self._pressed = True
            self._refresh()

    def _on_release(self, event):
        was_pressed = self._pressed
        self._pressed = False
        self._refresh()
        if not (self._enabled and was_pressed and self._command):
            return
        if 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
            self._command()
