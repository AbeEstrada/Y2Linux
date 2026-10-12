import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/platform'))
from y2_platform.battery import Soc, load_profile, sample
from y2_platform.common import Context
from y2_platform.power import LowBattery, load_policy

ROOT = Path(__file__).resolve().parents[1]
ETC = ROOT / 'buildroot/board/y2/production-overlay/etc/y2linux'


class BatterySoc(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ctx = Context(self.temp.name)
        self.put('/etc/y2linux/battery-profile.json', (ETC / 'battery-profile.json').read_text())

    def put(self, path, text):
        dest = self.ctx.path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)

    def test_invalid_override_fails_closed_and_real_fg_has_priority(self):
        self.put('/data/system/platform/battery-profile.json', '{"schema":1,"voltage_soc":[]}')
        self.assertIsNone(load_profile(self.ctx))
        soc = Soc(None)
        self.assertIsNone(soc.observe(0, 3800000, 1, 'Discharging')['percent'])
        value = soc.observe(1, 3800000, 1, 'Discharging', 71)
        self.assertEqual((value['percent'], value['source'], value['confidence']), (71, 'fuel_gauge', 'hardware'))

    def test_no_fake_sensors_charge_limit_or_die_temperature(self):
        self.put('/sys/class/power_supply/BAT0/present', '1')
        self.put('/sys/class/power_supply/BAT0/status', 'Charging')
        self.put('/sys/class/power_supply/BAT0/voltage_now', '3800000')
        self.put('/sys/class/power_supply/USB/constant_charge_current', '450000')
        self.put('/sys/class/thermal/thermal_zone0/temp', '50000')
        value = sample(self.ctx, Soc(load_profile(self.ctx)), 0)
        self.assertEqual(value['source'], 'voltage_estimate')
        self.assertIsNone(value['current_ua'])
        self.assertIsNone(value['temperature_millicelsius'])
        self.assertIsNone(value['charge_counter_uah'])

    def test_sag_rebound_is_monotonic_and_charging_smoothing_bounded(self):
        soc = Soc(load_profile(self.ctx))
        first = soc.observe(0, 3900000, 1, 'Discharging')['percent']
        low = soc.observe(60, 3700000, 1, 'Discharging')['percent']
        rebound = soc.observe(120, 3950000, 1, 'Discharging')['percent']
        self.assertLessEqual(rebound, low)
        self.assertGreaterEqual(low, first - 1)
        charging = soc.observe(180, 4175000, 1, 'Charging')['percent']
        self.assertLessEqual(charging, rebound + 1)
        self.assertEqual(soc.observe(181, 4175000, 1, 'Full')['percent'], 100)
        # Resting full pack of this charger (measured 4.09 V) is 100%, not 94%.
        self.assertEqual(soc.observe(182, 4090000, 1, 'Full')['percent'], 100)
        # An implausible Full at a low voltage never forces 100%.
        self.assertLess(Soc(load_profile(self.ctx)).observe(0, 3900000, 1, 'Full')['percent'], 100)
        self.assertLessEqual(soc.observe(183, 3390000, 1, 'Discharging')['percent'], 1)
        self.assertIsNone(soc.observe(184, 3390000, 0, 'Unknown')['percent'])
        self.assertEqual(soc.observe(185, 3800000, 1, 'Discharging')['percent'], 54)

    def test_rest_and_hybrid_require_actual_calibration(self):
        p = load_profile(self.ctx)
        p['calibrated_resistance_milliohm'] = 100
        soc = Soc(p)
        value = None
        for now in range(121):
            value = soc.observe(now, 3800000, 1, 'Discharging', current=-100000)
        self.assertTrue(value['resting'])
        self.assertEqual(value['source'], 'hybrid')

    def test_sleep_gap_exposes_voltage_loss_without_changing_curve_or_rate(self):
        self.put('/sys/class/power_supply/BAT0/present', '1')
        self.put('/sys/class/power_supply/BAT0/status', 'Discharging')
        self.put('/sys/class/power_supply/BAT0/voltage_now', '4000000')
        soc = Soc(load_profile(self.ctx))
        physical_time = iter([100., 700., 7900.])
        def clock(clock_id):
            return next(physical_time) if clock_id == time.CLOCK_BOOTTIME else 100.
        with patch('y2_platform.battery.time.clock_gettime', side_effect=clock):
            self.assertEqual(sample(self.ctx, soc)['percent'], 87)
            self.put('/sys/class/power_supply/BAT0/voltage_now', '3800000')
            after_ten_minutes = sample(self.ctx, soc)
            # The existing one-point-per-minute limit gets ten real minutes,
            # not zero suspended minutes or an artificial one-minute ceiling.
            self.assertEqual(after_ten_minutes['percent'], 77)
            self.assertLess(after_ten_minutes['filtered_voltage_uv'], 3810000)
            after_two_hours = sample(self.ctx, soc)
            self.assertEqual(after_two_hours['percent'], 54)
            self.assertFalse(after_two_hours['resting'])
            self.assertFalse(after_two_hours['provisional'])
            self.assertIsNone(after_two_hours['current_ua'])

    def test_sleep_time_alone_never_changes_soc_and_rebound_is_not_charge(self):
        soc = Soc(load_profile(self.ctx))
        self.assertEqual(soc.observe(0, 3800000, 1, 'Discharging')['percent'], 54)
        self.assertEqual(soc.observe(28800, 3800000, 1, 'Discharging')['percent'], 54)
        self.assertEqual(soc.observe(57600, 4000000, 1, 'Discharging')['percent'], 54)

    def test_low_soc_estimate_warns_but_shutdown_requires_trust_or_hard_floor(self):
        self.put('/etc/y2linux/power-policy.json', (ETC / 'power-policy.json').read_text())
        policy, reason = load_policy(self.ctx)
        self.assertIsNone(reason)
        guard = LowBattery()
        estimate = {'percent': 1, 'confidence': 'provisional'}
        for _ in range(10):
            self.assertEqual(guard.observe(policy, 3800000, 1, estimate), 'Critical')
        for _ in range(4):
            self.assertEqual(guard.observe(policy, 3300000, 1, estimate), 'Critical')
        self.assertEqual(guard.observe(policy, 3300000, 1, estimate), 'ShutdownPending')
        guard = LowBattery()
        for _ in range(5):
            state = guard.observe(policy, 3800000, 1, {'percent': 1, 'confidence': 'hardware'})
        self.assertEqual(state, 'ShutdownPending')


    def test_stock_profile_is_the_fm_kernel_table(self):
        """POWER-FINAL-16: fgauge_get_profile(25 C) and r_profile from the Y2 FM kernel."""
        p = load_profile(self.ctx)
        self.assertFalse(p['provisional'])
        self.assertEqual(p['design_capacity_uah'], 1300000)
        self.assertEqual(p['voltage_soc'][0], [3400000, 0])
        self.assertEqual(p['voltage_soc'][-1], [4175000, 100])
        self.assertEqual(len(p['voltage_soc']), 95)
        self.assertIn([3779000, 50], p['voltage_soc'])  # stock DOD 50 at 3779 mV
        self.assertEqual(len(p['voltage_resistance_milliohm']), 95)
        self.assertTrue(all(190 <= r <= 330 for _, r in p['voltage_resistance_milliohm']))
        value = Soc(p).observe(0, 3779000, 1, 'Discharging')
        self.assertEqual((value['percent'], value['confidence']), (50, 'calibrated_estimate'))
        self.assertEqual(value['remaining_uah_estimate'], 650000)

    def test_charging_uses_stock_oam_resistance_times_sense_current(self):
        p = load_profile(self.ctx)
        soc = Soc(p)
        # 450 mA * ~0.2 ohm ~= 90 mV: 3.89 V under charge reads as ~3.80 V OCV.
        value = soc.observe(0, 3890000, 1, 'Charging', charge_current=450000)
        self.assertEqual(value['source'], 'stock_oam')
        self.assertTrue(53 <= value['percent'] <= 57, value)
        # Without a sense current the fixed charging offset still applies.
        fallback = Soc(p).observe(0, 3890000, 1, 'Charging')
        self.assertEqual(fallback['source'], 'voltage_estimate')
        # An absurd current never moves the estimate by more than 300 mV.
        clipped = Soc(p).observe(0, 4100000, 1, 'Charging', charge_current=1200000)
        self.assertGreaterEqual(clipped['percent'], 49)
        # Discharging never uses the charger-path current.
        self.assertEqual(Soc(p).observe(0, 3800000, 1, 'Discharging', charge_current=450000)['source'],
                         'voltage_estimate')

if __name__ == '__main__':
    unittest.main()
