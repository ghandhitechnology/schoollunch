# -*- coding: utf-8 -*-
"""로직 레벨 테스트: 설정 손상, 렌더 극단값, fetch 실패 fallback, 커스텀 배경.

실행:  .venv/bin/python test_app.py
(사용자 실제 설정을 건드리지 않도록 모든 경로를 임시 폴더로 바꾼다)
"""
import copy
import json
import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config


class IsolatedConfigTest(unittest.TestCase):
    """config 모듈 경로를 임시 폴더로 바꿔 실제 사용자 데이터를 보호한다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.tmp.name
        self._orig = {
            name: getattr(config, name)
            for name in ("CONFIG_PATH", "CACHE_PATH", "LOG_PATH",
                         "WALLPAPER_PATH", "CUSTOM_DRAWING_PATH")
        }
        self._orig_default_custom = copy.deepcopy(config.DEFAULT_CUSTOM_WALLPAPER)
        config.CONFIG_PATH = os.path.join(d, "config.json")
        config.CACHE_PATH = os.path.join(d, "cache.json")
        config.LOG_PATH = os.path.join(d, "log.txt")
        config.WALLPAPER_PATH = os.path.join(d, "wallpaper.png")
        config.CUSTOM_DRAWING_PATH = os.path.join(d, "custom_drawing.png")
        config.DEFAULT_CUSTOM_WALLPAPER["drawing_overlay"] = config.CUSTOM_DRAWING_PATH
        config.DEFAULTS["custom_wallpaper"] = config.DEFAULT_CUSTOM_WALLPAPER

    def tearDown(self):
        for name, value in self._orig.items():
            setattr(config, name, value)
        config.DEFAULT_CUSTOM_WALLPAPER.clear()
        config.DEFAULT_CUSTOM_WALLPAPER.update(self._orig_default_custom)
        config.DEFAULTS["custom_wallpaper"] = config.DEFAULT_CUSTOM_WALLPAPER
        self.tmp.cleanup()


class ConfigRobustness(IsolatedConfigTest):
    def test_corrupt_json_falls_back_to_defaults(self):
        with open(config.CONFIG_PATH, "w") as f:
            f.write("{ not json !!!")
        cfg = config.load_config()
        self.assertEqual(cfg["grade"], 1)
        self.assertEqual(cfg["class_num"], 1)

    def test_wrong_types_are_sanitized(self):
        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"grade": "abc", "class_num": None, "ui_theme": 42,
                       "background_image": 7, "autostart": "yes"}, f)
        cfg = config.load_config()
        self.assertIsInstance(cfg["grade"], int)
        self.assertIsInstance(cfg["class_num"], int)
        self.assertIn(cfg["ui_theme"], config.UI_THEMES)
        self.assertIsInstance(cfg["background_image"], str)
        self.assertIsInstance(cfg["autostart"], bool)

    def test_nan_and_inf_rects_rejected(self):
        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"custom_wallpaper": {"layout": {
                "timetable": [float("nan"), 0.1, 0.2, 0.2],
                "meal": [0.1, float("inf"), 0.2, 0.2],
            }}}, f)
        cfg = config.load_config()
        for rect in cfg["custom_wallpaper"]["layout"].values():
            for v in rect:
                self.assertTrue(math.isfinite(v), f"non-finite value in {rect}")

    def test_save_is_atomic_against_partial_write(self):
        cfg = config.load_config()
        cfg["grade"] = 1
        config.save_config(cfg)
        # 저장 직후 임시 파일이 남아 있지 않아야 한다
        leftovers = [f for f in os.listdir(os.path.dirname(config.CONFIG_PATH))
                     if f.startswith("config.json.") or f.endswith(".tmp")]
        self.assertEqual(leftovers, [])
        self.assertEqual(config.load_config()["grade"], 1)


class RenderExtremes(IsolatedConfigTest):
    def setUp(self):
        super().setUp()
        import render
        self.render = render

    def _cfg(self, **overrides):
        cfg = config.load_config()
        cfg.update(overrides)
        return cfg

    BIG_MEALS = {
        "조식": [f"아주아주긴메뉴이름{i}와함께나오는반찬" for i in range(15)],
        "중식": ["🍚 이모지밥", "김치찌개 (매움 🔥)", "x" * 80],
        "석식": [],
    }
    BIG_TT = {
        "date": "2026-06-13", "weekday_label": "토",
        "periods": [{"period": i, "time": "08:40",
                     "subject": "아주긴과목이름" * 3, "teacher": "김" * 10}
                    for i in range(1, 16)],
    }

    def test_all_themes_and_sizes(self):
        for theme in ("black_on_white", "white_on_black", "liquid_glass", "crayon_sketch"):
            for size in ((320, 180), (800, 600), (1710, 1107), (3840, 2160)):
                img = self.render.render_wallpaper_image(
                    self.BIG_MEALS, self.BIG_TT, self._cfg(ui_theme=theme), size=size)
                self.assertEqual(img.size, size, f"{theme} {size}")

    def test_empty_data(self):
        img = self.render.render_wallpaper_image({}, {}, self._cfg(), size=(640, 360))
        self.assertEqual(img.size, (640, 360))

    def test_custom_layout_with_broken_assets(self):
        custom = config.default_custom_wallpaper()
        custom["background_image"] = "/no/such/file.png"
        custom["stickers"] = [{"path": "/missing.png", "rect": [0.1, 0.1, 0.2, 0.2]}]
        custom["layout"]["timetable"] = [0.0, 0.0, 0.04, 0.04]   # 최소 크기
        custom["drawing_overlay"] = config.CUSTOM_DRAWING_PATH
        with open(config.CUSTOM_DRAWING_PATH, "wb") as f:
            f.write(b"this is not a png")
        cfg = self._cfg(custom_wallpaper=custom)
        img = self.render.render_wallpaper_image(self.BIG_MEALS, self.BIG_TT, cfg, size=(960, 540))
        self.assertEqual(img.size, (960, 540))

    def test_custom_disabled_when_drawing_is_blank(self):
        """투명한 드로잉 파일만 있을 때는 기본 TUI 레이아웃을 유지해야 한다."""
        from PIL import Image
        Image.new("RGBA", (64, 64), (0, 0, 0, 0)).save(config.CUSTOM_DRAWING_PATH)
        cfg = self._cfg()
        self.assertFalse(self.render._custom_enabled(cfg),
                         "빈 드로잉 파일이 커스텀 모드를 켜 버린다")


class FetchFallbacks(IsolatedConfigTest):
    def setUp(self):
        super().setUp()
        import fetch_meal
        import fetch_timetable
        import requests
        self.fetch_meal = fetch_meal
        self.fetch_timetable = fetch_timetable
        self.requests = requests
        self._orig_get = requests.get

    def tearDown(self):
        self.requests.get = self._orig_get
        super().tearDown()

    def _network_down(self, *a, **k):
        raise self.requests.ConnectionError("network down")

    def test_meal_network_down_uses_cache(self):
        import datetime
        today = datetime.date.today().strftime("%Y%m%d")
        config.save_cache_entry("meal", {"date": today, "data": {"중식": ["캐시밥"]}})
        self.requests.get = self._network_down
        cfg = config.load_config()
        cfg["neis"] = {"atpt": "E10", "code": "7310058"}
        meals = self.fetch_meal.fetch_meals(cfg)
        self.assertTrue(meals["_cached"])
        self.assertEqual(meals["중식"], ["캐시밥"])

    def test_meal_no_cache_returns_empty_marked_cached(self):
        self.requests.get = self._network_down
        meals = self.fetch_meal.fetch_meals(config.load_config())
        self.assertTrue(meals["_cached"])

    def test_timetable_network_down_uses_cache(self):
        config.save_cache_entry("timetable", {
            "date": "2026-06-12", "weekday_label": "금",
            "periods": [{"period": 1, "time": "08:40", "subject": "수학", "teacher": "김"}],
        })
        self.requests.get = self._network_down
        tt = self.fetch_timetable.fetch_today(config.load_config())
        self.assertTrue(tt["_cached"])
        self.assertEqual(tt["periods"][0]["subject"], "수학")

    def test_timetable_garbage_response_survives(self):
        class FakeResp:
            text = "<html>점검 중</html>"
            encoding = ""
            def raise_for_status(self): pass
        self.requests.get = lambda *a, **k: FakeResp()
        tt = self.fetch_timetable.fetch_today(config.load_config())
        self.assertTrue(tt["_cached"])
        self.assertIn("periods", tt)

    def test_string_grade_in_config_does_not_crash_fetch(self):
        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"grade": "2", "class_num": "3"}, f)
        self.requests.get = self._network_down
        tt = self.fetch_timetable.fetch_today(config.load_config())
        self.assertIn("periods", tt)


class WallpaperPathLogic(IsolatedConfigTest):
    def test_missing_file_returns_false(self):
        import wallpaper
        self.assertFalse(wallpaper.set_wallpaper("/no/such/wallpaper.png"))

    def test_macos_alternating_target(self):
        """같은 경로로 덮어쓰면 macOS가 변경을 무시하므로 매번 다른 파일명이어야 한다."""
        import wallpaper
        if not hasattr(wallpaper, "_macos_live_path"):
            self.skipTest("alternating path not implemented")
        a = wallpaper._macos_live_path(current=None)
        b = wallpaper._macos_live_path(current=a)
        self.assertNotEqual(a, b)
        self.assertEqual(wallpaper._macos_live_path(current=b), a)


class UiFormatting(unittest.TestCase):
    def test_format_lines_with_missing_fields(self):
        import app_ui
        lines = app_ui.format_timetable_lines({})
        self.assertEqual(lines, ["시간표 정보 없음"])
        lines = app_ui.format_meal_lines({})
        self.assertIn("[조식]", lines)
        self.assertIn("  - 급식 정보 없음", lines)

    def test_format_lines_with_none_subject(self):
        import app_ui
        tt = {"date": "2026-06-13", "weekday_label": "토",
              "periods": [{"period": 1, "time": None, "subject": None, "teacher": None}]}
        lines = app_ui.format_timetable_lines(tt)
        self.assertEqual(len(lines), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
