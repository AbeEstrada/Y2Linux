"""POWER-FINAL-20: no colour flash at boot, no white/colour screen after the shutdown animation.

Owner report 2026-10-13: the startup sometimes flashes colours; after the shutdown
animation the panel turns white or shows colours.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class QuietDisplayPower(unittest.TestCase):
    def test_drm_never_switches_the_backlight_on(self):
        # Linked, every pipeline enable (e.g. the fbdev restore when Reborn exits
        # at shutdown) called backlight_enable() over a stale buffer.
        panel = (ROOT / 'kernel/platform/panel.c').read_text()
        self.assertNotIn('drm_panel_of_backlight(&ctx->panel)', panel.replace('no drm_panel_of_backlight()', ''))

    def test_backlight_sinks_go_dark_at_power_off(self):
        bl = (ROOT / 'kernel/platform/backlight.c').read_text()
        self.assertIn('.shutdown = y2_bl_shutdown', bl)
        body = bl[bl.index('static void y2_bl_shutdown('):]
        body = body[:body.index('\n}\n')]
        self.assertIn('regmap_update_bits(b->map, 0x356, 15, 0)', body)   # all four ISINKs off
        self.assertIn('platform_set_drvdata(pdev, bl);', bl)

    def test_splash_modeset_is_dark_and_always_relit(self):
        splash = (ROOT / 'tools/graphics/reborn-splash.c').read_text()
        show = splash[splash.index('static int show(Display *d) {'):]
        show = show[:show.index('\n}\n')]
        self.assertLess(show.index('light("4\\n");'), show.index('drmModeSetCrtc('))
        self.assertLess(show.index('drmModeSetCrtc('), show.index('drmWaitVBlank('))
        relit = show.index('light("0\\n");')
        self.assertGreater(relit, show.index('drmWaitVBlank('))
        # Relit unconditionally, before the return: a failed modeset never stays dark.
        self.assertLess(relit, show.index('return ret;'))
        self.assertNotIn('return', show[show.index('drmModeSetCrtc('):relit])


if __name__ == '__main__':
    unittest.main()
