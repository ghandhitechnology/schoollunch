"""Shared wallpaper palettes and labels for the modern layout and its editor."""
MODERN_THEMES = {
    "modern_light": {
        "name": "모던 화이트", "description": "밝은 흑백 · 또렷하고 단정하게",
        "bg": "#fafafa", "text": "#161616", "dim": "#747474", "border": "#dddddd",
        "change": "#161616", "change_bg": "#eaeaea", "change_mark": "#444444", "quote": "#5e5e5e",
    },
    "modern_dark": {
        "name": "모던 블랙", "description": "어두운 흑백 · 은은한 대비",
        "bg": "#171717", "text": "#ededed", "dim": "#a1a1a1", "border": "#373737",
        "change": "#ffffff", "change_bg": "#333333", "change_mark": "#c5c5c5", "quote": "#b7b7b7",
    },
    "paper": {
        "name": "페이퍼", "description": "따뜻한 종이색 · 편안한 분위기",
        "bg": "#f4eee2", "text": "#443a2f", "dim": "#827361", "border": "#d9cfbf",
        "change": "#895d25", "change_bg": "#eadcc1", "change_mark": "#b58a4d", "quote": "#786652",
    },
    "midnight": {
        "name": "미드나잇", "description": "짙은 네이비 · 차분한 분위기",
        "bg": "#121d2c", "text": "#e5edf7", "dim": "#98aac0", "border": "#304157",
        "change": "#edd39e", "change_bg": "#2e3540", "change_mark": "#cfb074", "quote": "#b2c1d2",
    },
    "daily": {
        "name": "데일리", "description": "뉴트럴 그레이 · 기존 기본 디자인",
        "bg": "#f5f6f3", "text": "#2b302c", "dim": "#828981", "border": "#dce1d9",
        "change": "#8b671f", "change_bg": "#f2e9cf", "change_mark": "#b49245", "quote": "#626c62",
    },
}


def is_modern_theme(value):
    return isinstance(value, str) and value in MODERN_THEMES


def renderer_palette(value):
    palette = MODERN_THEMES.get(value, MODERN_THEMES['daily'])
    rgb = lambda color: tuple(bytes.fromhex(color.lstrip('#')))
    return {'bg': rgb(palette['bg']), 'text': rgb(palette['text']), 'dim': rgb(palette['dim']),
            'bright': rgb(palette['text']), 'accent': rgb(palette['change_mark']),
            'use_background_image': False, 'scanline_alpha': 0}


def theme_catalog():
    modern = [[key, value['name'], value['bg'], value['text'], value['description'], 'modern']
              for key, value in MODERN_THEMES.items()]
    return modern + [
        ['black_on_white', '레트로 흑백', '#ffffff', '#000000', '픽셀 터미널', 'legacy'],
        ['white_on_black', '레트로 백흑', '#000000', '#ffffff', '픽셀 터미널', 'legacy'],
        ['crayon_sketch', '크레용', '#fdf7ed', '#cd7680', '스케치 스타일', 'legacy'],
        ['cyber_terminal', '터미널', '#101c14', '#61d088', '녹색 픽셀 화면', 'legacy'],
    ]
