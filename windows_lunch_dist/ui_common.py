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
        "theme_name": "black_on_white",
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
        "theme_name": "white_on_black",
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
    "crayon_sketch": {
        "theme_name": "crayon_sketch",
        "bg": "#fdfbf7",
        "panel": "#fdfbf7",
        "panel_alt": "#f5f0e6",
        "fg": "#2c2c2c",
        "dim": "#7c7267",
        "border": "#2c2c2c",
        "accent": "#b27a12",
        "button_fg": "#ffffff",
        "canvas_bg": "#f5f0e6",
    },
    "cyber_terminal": {
        "theme_name": "cyber_terminal",
        "bg": "#0a100d",
        "panel": "#0a100d",
        "panel_alt": "#080c0a",
        "fg": "#00ff66",
        "dim": "#00a84f",
        "border": "#00ff66",
        "accent": "#ffb000",
        "button_fg": "#0a100d",
        "canvas_bg": "#080c0a",
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


class ThemedButton(tk.Frame):
    """모든 OS에서 테마 색이 그대로 적용되는 평면 버튼 (hover/press/disabled 지원)."""

    def __init__(self, parent, text, command, font=None, padx=12, pady=6):
        super().__init__(parent, bd=0, highlightthickness=0)
        self._command = command
        self._palette = None
        self._enabled = True
        self._selected = False
        self._hover = False
        self._pressed = False

        self.label = tk.Label(
            self, text=text, font=font, padx=padx, pady=pady,
            cursor="hand2", borderwidth=0, highlightthickness=0, takefocus=1
        )
        self.label.pack(fill="both", expand=True, padx=1, pady=1)

        self.label.bind("<Enter>", self._on_enter)
        self.label.bind("<Leave>", self._on_leave)
        self.label.bind("<ButtonPress-1>", self._on_press)
        self.label.bind("<ButtonRelease-1>", self._on_release)
        self.label.bind("<Key-Return>", self._on_key_activate)
        self.label.bind("<Key-space>", self._on_key_activate)
        self.label.bind("<FocusIn>", lambda _event: self._refresh())
        self.label.bind("<FocusOut>", lambda _event: self._refresh())

    def cget(self, key):
        if key == "text":
            return self.label.cget("text")
        elif key == "font":
            return self.label.cget("font")
        elif key == "fg" or key == "foreground":
            return self.label.cget("fg")
        elif key == "bg" or key == "background":
            return self.label.cget("bg")
        return super().cget(key)

    def configure(self, cnf=None, **kw):
        if cnf is not None:
            if isinstance(cnf, dict):
                kw.update(cnf)
            else:
                return super().configure(cnf)
        
        label_keys = {"text", "font", "fg", "foreground", "padx", "pady"}
        label_kw = {k: v for k, v in kw.items() if k in label_keys}
        frame_kw = {k: v for k, v in kw.items() if k not in label_keys}
        
        if label_kw:
            self.label.configure(**label_kw)
        if frame_kw:
            super().configure(**frame_kw)

    config = configure

    def set_palette(self, p):
        self._palette = p
        self._refresh()

    def set_enabled(self, enabled):
        self._enabled = bool(enabled)
        self.label.configure(cursor="hand2" if self._enabled else "arrow")
        self._refresh()

    def set_selected(self, selected):
        self._selected = bool(selected)
        self._refresh()

    def _refresh(self):
        p = self._palette
        if not p or not self.winfo_exists():
            return
        if p.get("theme_name") == "cyber_terminal":
            bg = p["panel"]
            if not self._enabled:
                fg = p["dim"]
                border = "#550000"
            elif self._selected or (self._pressed and self._hover):
                fg = "#00ff66"
                border = "#ff0000"
            elif self._hover:
                fg = "#00ff66"
                border = "#ff3333"
            else:
                fg = "#00ff66"
                border = "#ff0000"
            
            super().configure(bg=border)
            self.label.configure(bg=bg, fg=fg)
            return

        if not self._enabled:
            bg, fg = p["panel_alt"], p["dim"]
        elif self._selected or (self._pressed and self._hover):
            bg, fg = p["panel"], p["accent"]
        elif self._hover:
            bg, fg = p["dim"], p["button_fg"]
        else:
            bg, fg = p["accent"], p["button_fg"]
            
        super().configure(bg=p["border"])
        self.label.configure(bg=bg, fg=fg)

    def _on_enter(self, _event):
        self._hover = True
        self._refresh()

    def _on_leave(self, _event):
        self._hover = False
        self._refresh()

    def _on_press(self, _event):
        if self._enabled:
            self.label.focus_set()
            self._pressed = True
            self._refresh()

    def _on_release(self, event):
        was_pressed = self._pressed
        self._pressed = False
        self._refresh()
        if not (self._enabled and was_pressed and self._command):
            return
        if 0 <= event.x <= self.label.winfo_width() and 0 <= event.y <= self.label.winfo_height():
            self._command()

    def _on_key_activate(self, _event):
        if self._enabled and self._command:
            self._command()
        return "break"
