import sys, datetime, copy
from unittest.mock import patch
import unittest, config, render
from daily_quote import quote_for_day, ALL_QUOTES
from test_modern_ui import DesktopDataFlow

class QuoteControls(DesktopDataFlow):
    def test_change_is_local_preview_and_persists_on_save(self):
        before=config.load_config()
        with patch('modern_ui.fetch_timetable.fetch_today') as tt, patch('modern_ui.fetch_meal.fetch_meals') as meal, patch.object(self.api,'_preview',return_value='preview'), patch('modern_ui.autostart.apply'):
            r=self.api.change_quote(before)
            self.assertNotEqual(r['quote']['text'],quote_for_day(cfg=before)['text'])
            self.assertEqual(config.load_config(),before)
            opts=dict(before,quote_index=r['quote_index'],quote_date=r['quote_date'],quote_enabled=False)
            self.api.save(opts)
            self.assertFalse(config.load_config()['quote_enabled'])
            self.assertEqual(quote_for_day(cfg=config.load_config()),r['quote'])
            tomorrow=datetime.date.today()+datetime.timedelta(days=1)
            self.assertEqual(quote_for_day(tomorrow,cfg=opts),quote_for_day(tomorrow))
            reset=self.api.change_quote(opts,True)
            self.assertEqual(reset['quote'],quote_for_day())
            tt.assert_not_called();meal.assert_not_called()

    def test_off_removes_quote_pixels_and_on_restores(self):
        cfg=copy.deepcopy(self.cfg);cfg['ui_theme']='modern_dark'
        meals={'중식':['밥']}
        on=render.render_wallpaper_image(meals,self.tt,cfg,size=(960,540)).convert('RGB')
        cfg['quote_enabled']=False
        off=render.render_wallpaper_image(meals,self.tt,cfg,size=(960,540)).convert('RGB')
        from PIL import ImageChops
        box=ImageChops.difference(on,off).getbbox()
        self.assertIsNotNone(box)
        self.assertGreaterEqual(box[1],460)
        self.assertIsNone(ImageChops.difference(on.crop((0,0,960,460)),off.crop((0,0,960,460))).getbbox())

if __name__=='__main__':unittest.main()
