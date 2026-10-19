import copy
import unittest
from unittest.mock import patch

from PIL import ImageChops
import config
import render
import layout_editor
from modern_themes import MODERN_THEMES


class ModernThemeRendering(unittest.TestCase):
    def setUp(self):
        self.cfg=copy.deepcopy(config.DEFAULTS)
        self.cfg['custom_wallpaper']['drawing_overlay']=''
        self.meals={'중식':['밥','국'],'석식':['볶음밥']}
        self.tt={'date':'2026-10-19','weekday_label':'월',
                 'periods':[{'period':1,'time':'08:50','subject':'고물A','teacher':'김병*','changed':True}]}

    def test_monochrome_themes_are_truly_monochrome(self):
        for theme in ['modern_light','modern_dark']:
            with self.subTest(theme=theme):
                cfg=dict(self.cfg,ui_theme=theme)
                image=render.render_wallpaper_image(self.meals,self.tt,cfg,size=(960,540)).convert('RGB')
                r,g,b=image.split()
                self.assertIsNone(ImageChops.difference(r,g).getbbox())
                self.assertIsNone(ImageChops.difference(g,b).getbbox())

    def test_all_modern_themes_keep_custom_layout_and_study_panel(self):
        layouts=[]
        for theme in MODERN_THEMES:
            with self.subTest(theme=theme):
                cfg=copy.deepcopy(self.cfg);cfg['ui_theme']=theme
                custom=layout_editor.normalize(cfg['custom_wallpaper'],cfg,(960,540))
                custom['daily_layout']['timetable'][0]=.1
                cfg['custom_wallpaper']=custom
                layouts.append(custom['daily_layout'])
                panels=layout_editor.panel_images(self.meals,self.tt,cfg,(960,540))
                self.assertIn('quote',panels)
                with patch.object(render,'_render_custom_wallpaper',side_effect=AssertionError('Unexpected retro layout')):
                    image=render.render_wallpaper_image(self.meals,self.tt,cfg,size=(960,540))
                self.assertEqual(image.size,(960,540))
        self.assertTrue(all(layout==layouts[0] for layout in layouts))
