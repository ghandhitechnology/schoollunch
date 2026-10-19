import copy
import datetime
from unittest.mock import patch

import config
from modern_ui import DesktopApi
from test_app import IsolatedConfigTest


class DesktopDataFlow(IsolatedConfigTest):
    def setUp(self):
        super().setUp()
        self.cfg = config.load_config()
        config.save_config(self.cfg)
        target = __import__('fetch_timetable')._target_date().isoformat()
        self.tt = {"date": target, "grade": 1, "class_num": 1,
                   "periods": [{"period": 1, "time": "08:50", "subject": "고물A",
                                "teacher": "김병*", "changed": True}], "_cached": False}
        config.save_cache_entry("timetable", self.tt)
        config.save_cache_entry("meal", {"date": datetime.date.today().strftime("%Y%m%d"),
                                        "data": {"중식": ["밥"], "_cached": False}})
        self.api = DesktopApi()

    def test_opening_twice_and_changing_theme_do_not_fetch(self):
        with patch('modern_ui.fetch_timetable.fetch_today') as timetable, \
             patch('modern_ui.fetch_meal.fetch_meals') as meal, \
             patch.object(self.api, '_preview', return_value='image'):
            self.api.state()
            self.api.state()
            from modern_themes import MODERN_THEMES
            for theme in MODERN_THEMES:
                self.api.preview({"ui_theme": theme})
            timetable.assert_not_called()
            meal.assert_not_called()

    def test_preview_for_other_class_does_not_relabel_old_timetable(self):
        cfg = self.api._options({"class_num": 2})
        with patch('modern_ui.fetch_timetable.fetch_today') as fetch:
            _, tt = self.api._data(cfg)
            self.assertEqual(tt['periods'], [])
            fetch.assert_not_called()

    def test_refuses_applying_wrong_class_fallback(self):
        before = copy.deepcopy(config.load_config())
        with patch('modern_ui.fetch_timetable.fetch_today', return_value=self.tt), \
             patch('modern_ui.wallpaper.apply_wallpaper') as apply:
            with self.assertRaises(ValueError):
                self.api.apply({"class_num": 2})
            apply.assert_not_called()
        self.assertEqual(config.load_config(), before)

    def test_appearance_apply_uses_cache(self):
        with patch('modern_ui.fetch_timetable.fetch_today') as fetch, \
             patch('modern_ui.autostart.apply'), \
             patch('modern_ui.render.render_wallpaper', return_value='test.png'), \
             patch('modern_ui.wallpaper.apply_wallpaper', return_value={"ok": True}), \
             patch.object(self.api, '_preview', return_value='image'):
            result = self.api.apply({"ui_theme": "daily"})
            self.assertIn('적용', result['message'])
            self.assertEqual(config.load_config()['ui_theme'], 'daily')
            fetch.assert_not_called()

    def test_background_selection_updates_custom_renderer(self):
        cfg = self.api._options({"background_image": "photo.png"})
        self.assertEqual(cfg['custom_wallpaper']['background_image'], 'photo.png')

    def test_manual_edit_survives_future_fetches_without_network(self):
        with patch.object(self.api, '_preview', return_value='image'):
            self.api.edit_timetable([{"subject": "실험", "teacher": "김병*"}], {})
        import fetch_timetable
        with patch('fetch_timetable._bootstrap') as network:
            tt = fetch_timetable.fetch_today(config.load_config())
            self.assertEqual(tt['periods'][0]['subject'], '실험')
            self.assertTrue(tt['periods'][0]['changed'])
            network.assert_not_called()
