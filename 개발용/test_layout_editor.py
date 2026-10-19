import base64
import copy
import datetime
import io
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import config
import layout_editor
from modern_ui import DesktopApi
from test_app import IsolatedConfigTest


class LayoutEditing(IsolatedConfigTest):
    def setUp(self):
        super().setUp()
        self.cfg = config.load_config()
        self.cfg['ui_theme'] = 'daily'
        config.save_config(self.cfg)
        import fetch_timetable
        tt = {'date': fetch_timetable._target_date().isoformat(), 'grade': 1, 'class_num': 1,
              'periods': [{'period': 1, 'time': '08:50', 'subject': '고물A',
                           'teacher': '김병*', 'changed': True}]}
        config.save_cache_entry('timetable', tt)
        config.save_cache_entry('meal', {'date': datetime.date.today().strftime('%Y%m%d'), 'data': {'중식': ['밥']}})
        self.api = DesktopApi()
        self.resolution = patch('modern_ui.render.detect_resolution', return_value=(960, 540))
        self.resolution.start()
        self.addCleanup(self.resolution.stop)

    def png(self):
        image = Image.new('RGBA', (960, 540))
        image.putpixel((50, 50), (220, 50, 60, 255))
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()

    def test_opening_editor_does_not_save_or_fetch(self):
        before = Path(config.CONFIG_PATH).read_bytes()
        with patch('modern_ui.fetch_timetable.fetch_today') as timetable, patch('modern_ui.fetch_meal.fetch_meals') as meals:
            result = self.api.editor({})
            self.assertEqual({p['key'] for p in result['panels']}, {'prompt', 'timetable', 'meal', 'quote'})
            self.assertEqual(result['custom']['editor_version'], 2)
            timetable.assert_not_called()
            meals.assert_not_called()
        self.assertEqual(Path(config.CONFIG_PATH).read_bytes(), before)

    def test_save_round_trips_positions_ink_and_hidden_quote(self):
        custom = self.api.editor({})['custom']
        custom['daily_layout']['timetable'][0] = .15
        custom['hidden_panels'] = ['quote']
        cache_before = Path(config.CACHE_PATH).read_bytes()
        with patch('modern_ui.autostart.apply'), patch('modern_ui.wallpaper.apply_wallpaper') as wallpaper:
            self.api.save_editor({}, custom, self.png(), False)
            wallpaper.assert_not_called()
        saved = config.load_config()['custom_wallpaper']
        self.assertEqual(saved['daily_layout']['timetable'][0], .15)
        self.assertEqual(saved['hidden_panels'], ['quote'])
        with Image.open(saved['drawing_overlay']) as image:
            self.assertEqual(image.getpixel((50, 50)), (220, 50, 60, 255))
        self.assertEqual(Path(config.CACHE_PATH).read_bytes(), cache_before)
        self.assertEqual(self.api.editor({})['custom']['daily_layout'], saved['daily_layout'])

    def test_failed_apply_does_not_commit_settings_or_ink(self):
        custom = self.api.editor({})['custom']
        custom['daily_layout']['meal'][1] = .1
        before = Path(config.CONFIG_PATH).read_bytes()
        with patch('modern_ui.wallpaper.apply_wallpaper', return_value={'ok': False, 'detail': 'failed'}):
            with self.assertRaises(RuntimeError):
                self.api.save_editor({}, custom, self.png(), True)
        self.assertEqual(Path(config.CONFIG_PATH).read_bytes(), before)
        self.assertFalse(Path(config.CUSTOM_DRAWING_PATH).exists())

    def test_full_reset_is_preview_only_until_saved_and_preserves_class(self):
        cfg = config.load_config()
        custom = cfg['custom_wallpaper']
        custom.update(background_image='old-photo.png', font_scale=1.6,
                      hidden_panels=['quote'], pen_color='#ff0000')
        custom['daily_layout'] = {'timetable': [.1, .1, .2, .2]}
        custom['stickers'] = [{'path': 'old-sticker.png', 'rect': [.2, .2, .1, .1], 'angle': 45}]
        config.save_config(cfg)
        before = Path(config.CONFIG_PATH).read_bytes()
        result = self.api.editor({}, reset=True)
        self.assertEqual(Path(config.CONFIG_PATH).read_bytes(), before)
        reset = result['custom']
        self.assertEqual(reset['background_image'], '')
        self.assertEqual(reset['stickers'], [])
        self.assertEqual(reset['hidden_panels'], [])
        self.assertEqual(reset['font_scale'], 1)
        with Image.open(io.BytesIO(base64.b64decode(result['drawing'].split(',', 1)[1]))) as image:
            self.assertIsNone(image.getchannel('A').getbbox())
        with patch('modern_ui.autostart.apply'):
            self.api.save_editor({}, reset, result['drawing'], False)
        saved = config.load_config()
        self.assertEqual(saved['class_num'], cfg['class_num'])
        self.assertEqual(saved['autostart'], cfg['autostart'])
        self.assertEqual(saved['custom_wallpaper']['stickers'], [])
        self.assertEqual(saved['custom_wallpaper']['drawing_overlay'], '')

    def test_layout_bounds_and_legacy_themes_are_supported(self):
        custom = copy.deepcopy(self.cfg['custom_wallpaper'])
        custom['daily_layout'] = {'meal': [3, -1, 2, .01], 'quote': [float('nan'), 0, 1, 1]}
        normalized = layout_editor.normalize(custom, self.cfg, (960, 540))
        for x, y, w, h in normalized['daily_layout'].values():
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x+w, 1)
            self.assertLessEqual(y+h, 1)
        cfg = dict(self.cfg, ui_theme='black_on_white')
        self.assertEqual(set(layout_editor.panel_images({}, {'periods': []}, cfg, (960, 540))),
                         {'prompt', 'timetable', 'meal'})
