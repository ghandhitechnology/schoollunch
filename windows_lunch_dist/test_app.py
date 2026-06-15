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

from PIL import Image

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
        for theme in ("black_on_white", "white_on_black", "crayon_sketch", "cyber_terminal"):
            for size in ((320, 180), (800, 600), (1710, 1107), (3840, 2160)):
                img = self.render.render_wallpaper_image(
                    self.BIG_MEALS, self.BIG_TT, self._cfg(ui_theme=theme), size=size)
                self.assertEqual(img.size, size, f"{theme} {size}")

    def test_removed_liquid_glass_theme_falls_back(self):
        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"ui_theme": "liquid_glass"}, f)
        self.assertEqual(config.load_config()["ui_theme"], config.DEFAULT_UI_THEME)

    def test_empty_data(self):
        img = self.render.render_wallpaper_image({}, {}, self._cfg(), size=(640, 360))
        self.assertEqual(img.size, (640, 360))

    def test_custom_layout_with_broken_assets(self):
        custom = config.default_custom_wallpaper()
        custom["background_image"] = "/no/such/file.png"
        custom["stickers"] = [{"path": "/missing.png", "rect": [0.1, 0.1, 0.2, 0.2], "angle": 45}]
        custom["layout"]["timetable"] = [0.0, 0.0, 0.04, 0.04]   # 최소 크기
        custom["drawing_overlay"] = config.CUSTOM_DRAWING_PATH
        with open(config.CUSTOM_DRAWING_PATH, "wb") as f:
            f.write(b"this is not a png")
        cfg = self._cfg(custom_wallpaper=custom)
        img = self.render.render_wallpaper_image(self.BIG_MEALS, self.BIG_TT, cfg, size=(960, 540))
        self.assertEqual(img.size, (960, 540))

    def test_sticker_rotation_round_trips_and_renders(self):
        sticker_path = os.path.join(os.path.dirname(config.CONFIG_PATH), "sticker.png")
        Image.new("RGBA", (60, 30), (255, 0, 0, 255)).save(sticker_path)
        merged = config._merge_custom_wallpaper({
            "stickers": [{"path": sticker_path, "rect": [0.2, 0.2, 0.25, 0.25], "angle": 735}]
        })
        self.assertEqual(merged["stickers"][0]["angle"], 15)
        cfg = self._cfg(custom_wallpaper=merged)
        img = self.render.render_wallpaper_image(self.BIG_MEALS, self.BIG_TT, cfg, size=(960, 540))
        self.assertEqual(img.size, (960, 540))

    def test_custom_disabled_when_drawing_is_blank(self):
        """투명한 드로잉 파일만 있을 때는 기본 TUI 레이아웃을 유지해야 한다."""
        from PIL import Image
        Image.new("RGBA", (64, 64), (0, 0, 0, 0)).save(config.CUSTOM_DRAWING_PATH)
        cfg = self._cfg()
        self.assertFalse(self.render._custom_enabled(cfg),
                         "빈 드로잉 파일이 커스텀 모드를 켜 버린다")

    def test_custom_prompt_text_renders(self):
        cfg = self._cfg(prompt_text="TEST {grade}-{class_num} >")
        img = self.render.render_wallpaper_image(self.BIG_MEALS, self.BIG_TT, cfg, size=(960, 540))
        self.assertEqual(img.size, (960, 540))

    def test_invalid_prompt_text_falls_back(self):
        cfg = self._cfg(prompt_text="BAD {unknown}")
        img = self.render.render_wallpaper_image(self.BIG_MEALS, self.BIG_TT, cfg, size=(960, 540))
        self.assertEqual(img.size, (960, 540))


class PromptConfig(IsolatedConfigTest):
    def test_prompt_text_is_sanitized(self):
        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"prompt_text": 123}, f)
        cfg = config.load_config()
        self.assertEqual(cfg["prompt_text"], config.DEFAULT_PROMPT)

    def test_prompt_text_persists(self):
        cfg = config.load_config()
        cfg["prompt_text"] = "CUSTOM {grade}-{class_num}"
        config.save_config(cfg)
        self.assertEqual(config.load_config()["prompt_text"], "CUSTOM {grade}-{class_num}")


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


class TeacherNameResolution(IsolatedConfigTest):
    def setUp(self):
        super().setUp()
        import fetch_timetable
        self.ft = fetch_timetable

    def _tt(self, *teachers):
        return {"periods": [{"period": i + 1, "teacher": t} for i, t in enumerate(teachers)]}

    def test_unique_prefix_match_unmasks(self):
        tt = self.ft._resolve_teachers(self._tt("김완*"), ["김완선", "이현우"])
        self.assertEqual(tt["periods"][0]["teacher"], "김완선")

    def test_ambiguous_prefix_keeps_masked(self):
        tt = self.ft._resolve_teachers(self._tt("김완*"), ["김완선", "김완태"])
        self.assertEqual(tt["periods"][0]["teacher"], "김완*")

    def test_no_roster_or_no_match_unchanged(self):
        tt = self.ft._resolve_teachers(self._tt("김완*", "박지*"), ["이현우"])
        self.assertEqual([p["teacher"] for p in tt["periods"]], ["김완*", "박지*"])
        tt = self.ft._resolve_teachers(self._tt("김완*"), [])
        self.assertEqual(tt["periods"][0]["teacher"], "김완*")

    def test_unmasked_names_left_alone(self):
        tt = self.ft._resolve_teachers(self._tt("이현우", ""), ["이현우식"])
        self.assertEqual(tt["periods"][0]["teacher"], "이현우")

    def test_cached_fallback_applies_roster(self):
        config.save_cache_entry("timetable", {
            "date": "2026-06-12", "weekday_label": "금",
            "periods": [{"period": 1, "time": "08:40", "subject": "수학", "teacher": "김완*"}],
        })
        import requests
        orig = requests.get
        def down(*a, **k):
            raise requests.ConnectionError("down")
        requests.get = down
        try:
            cfg = config.load_config()
            cfg["teacher_names"] = ["김완선"]
            tt = self.ft.fetch_today(cfg)
        finally:
            requests.get = orig
        self.assertEqual(tt["periods"][0]["teacher"], "김완선")
        # 캐시 원본은 마스킹 상태를 유지해야 한다 (명단 수정 시 재매칭 가능)
        self.assertEqual(config.load_cache()["timetable"]["periods"][0]["teacher"], "김완*")

    def test_config_sanitizes_roster(self):
        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"teacher_names": ["  김완선 ", "", 42, None, "이현우"]}, f)
        self.assertEqual(config.load_config()["teacher_names"], ["김완선", "이현우"])


class FontScale(IsolatedConfigTest):
    def test_merge_clamps_and_defaults(self):
        merged = config._merge_custom_wallpaper({"font_scale": 99})
        self.assertEqual(merged["font_scale"], config.FONT_SCALE_MAX)
        merged = config._merge_custom_wallpaper({"font_scale": "abc"})
        self.assertEqual(merged["font_scale"], 1.0)
        merged = config._merge_custom_wallpaper({"font_scale": float("nan")})
        self.assertEqual(merged["font_scale"], 1.0)
        merged = config._merge_custom_wallpaper({})
        self.assertEqual(merged["font_scale"], 1.0)

    def test_render_respects_font_scale(self):
        import render
        cfg = config.load_config()
        cfg["custom_wallpaper"]["background_image"] = ""
        meals = {"중식": ["테스트"]}
        tt = {"date": "2026-06-13", "weekday_label": "토",
              "periods": [{"period": 1, "time": "08:40", "subject": "수학", "teacher": "김"}]}
        # 극단값에서도 두 렌더 경로(TUI/커스텀)가 깨지지 않아야 한다
        for scale in (config.FONT_SCALE_MIN, 1.0, config.FONT_SCALE_MAX):
            cfg["custom_wallpaper"]["font_scale"] = scale
            img = render.render_wallpaper_image(meals, tt, cfg, size=(960, 540))
            self.assertEqual(img.size, (960, 540), f"TUI path scale={scale}")
            cfg["custom_wallpaper"]["stickers"] = [{"path": "/missing.png", "rect": [0.1, 0.1, 0.2, 0.2], "angle": 30}]
            img = render.render_wallpaper_image(meals, tt, cfg, size=(960, 540))
            self.assertEqual(img.size, (960, 540), f"custom path scale={scale}")
            cfg["custom_wallpaper"]["stickers"] = []


class WallpaperPathLogic(IsolatedConfigTest):
    def test_missing_file_returns_false(self):
        import wallpaper
        self.assertFalse(wallpaper.set_wallpaper("/no/such/wallpaper.png"))

    def test_macos_alternating_target(self):
        """macOS 캐시 우회를 위해 적용 때마다 새 파일명이어야 한다."""
        import wallpaper
        if not hasattr(wallpaper, "_macos_live_path"):
            self.skipTest("live path not implemented")
        a = wallpaper._macos_live_path(current=None)
        b = wallpaper._macos_live_path(current=a)
        self.assertNotEqual(a, b)
        self.assertNotEqual(wallpaper._macos_live_path(current=b), a)


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
