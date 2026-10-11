"""POWER-FINAL-14 persistent sleep and USB diagnostics. Synthetic evidence only."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/platform'))
from y2_platform.common import Context
from y2_platform import sleep_diagnostics as d
from y2_platform.power_journal import PowerJournal, PATH as JOURNAL
from y2_platform.suspend_record import record as suspend_record

FIB_TRIE = """Main:
  +-- 0.0.0.0/0 3 0 5
     +-- 10.42.0.0/24 2 0 2
        |-- 10.42.0.0
           /24 link UNICAST
        |-- 10.42.0.1
           /32 host LOCAL
     +-- 192.168.123.0/24 2 0 2
        |-- 192.168.123.136
           /32 host LOCAL
"""
ROUTE = """Iface\tDestination\tGateway\tFlags\tRefCnt\tUse\tMetric\tMask\tMTU\tWindow\tIRTT
usb0\t00002A0A\t00000000\t0001\t0\t0\t0\t00FFFFFF\t0\t0\t0
wlan0\t007BA8C0\t00000000\t0001\t0\t0\t0\t00FFFFFF\t0\t0\t0
"""
KMSG = """6,100,5000000,-;Y2USB PHY entry savecurrent=1
6,101,5000100,-;random: crng init done
6,102,5000200,-;y2-usb 11200000.usb: resume_noirq restored 11 bytes
 SUBSYSTEM=platform
6,103,5000300,-;mediatek-drm display: vblank
6,104,5000400,-;PM: suspend exit
"""


class Diagnostics(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ctx = Context(self.temp.name)
        files = {'/data/.y2data-schema': '1', '/run/y2-data-device': '/dev/data',
                 '/proc/self/mountinfo': '5 1 179:7 / /data rw - ext4 /dev/data rw',
                 '/proc/sys/kernel/random/boot_id': 'one',
                 '/etc/y2linux/versions.json': json.dumps({'build_id': 'Y2LINUX-PLATFORM-V1-POWER-FINAL-14'}),
                 '/sys/module/pwrap/parameters/vproc_sleep': 'Y',
                 '/sys/module/pwrap/parameters/vproc_sleep_state': 'stage=restored entries=3 restores=3 failures=0',
                 '/sys/firmware/y2_pmic/lp_sel': 'applied=1',
                 '/sys/bus/platform/drivers/y2-usb/11200000.usb/phy_savecurrent': 'enabled=1 saves=3 restores=3 mismatches=0',
                 '/sys/bus/platform/drivers/y2-usb/11200000.usb/status': 'stage=6 error=0 configured=1 polls=9 detached=0\nirqs=5',
                 '/sys/bus/i2c/devices/0-0051/sleep': 'enabled=1 sleeps=3 wakes=3 failures=0',
                 '/sys/firmware/y2_infra/state': 'saves=3 restores=3 last_lost=0x1',
                 '/sys/devices/platform/10006000.power-controller/state': 'entries=3',
                 '/sys/devices/platform/10006000.power-controller/golden': 'captures=3 entry_differences=4',
                 '/sys/class/udc/musb-hdrc.4.auto/state': 'configured',
                 '/sys/class/net/usb0/operstate': 'up', '/sys/class/net/usb0/carrier': '1',
                 '/sys/class/net/usb0/statistics/rx_packets': '0', '/sys/class/net/usb0/statistics/tx_packets': '7',
                 '/proc/net/fib_trie': FIB_TRIE, '/proc/net/route': ROUTE, '/dev/kmsg': KMSG,
                 '/proc/41/comm': 'umtprd'}
        for name, text in files.items():
            self.write(name, text)

    def write(self, name, text):
        path = self.ctx.path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def rows(self):
        path = self.ctx.path(d.PATH)
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_resume_row_keeps_every_13_counter_golden_and_usb_state(self):
        self.assertTrue(d.record(self.ctx, 'kernel_resumed'))
        row = self.rows()[-1]
        features = row['features']
        self.assertEqual(features['vproc_sleep_state'], 'stage=restored entries=3 restores=3 failures=0')
        self.assertEqual(features['phy_savecurrent']['11200000.usb'], 'enabled=1 saves=3 restores=3 mismatches=0')
        self.assertEqual(features['wheel_sleep']['0-0051'], 'enabled=1 sleeps=3 wakes=3 failures=0')
        self.assertEqual(features['infra'], 'saves=3 restores=3 last_lost=0x1')
        self.assertEqual(features['golden'], 'captures=3 entry_differences=4')
        usb = row['usb_net']
        self.assertEqual(usb['udc'], {'musb-hdrc.4.auto': 'configured'})
        self.assertEqual(usb['controller']['11200000.usb']['configured'], '1')
        self.assertEqual(usb['usb0']['ipv4'], ['10.42.0.1'])
        self.assertEqual(usb['usb0']['statistics']['rx_packets'], 0)
        self.assertEqual(usb['processes'], {'umtprd': True, 'dropbear': False})
        self.assertEqual(row['build_id'], 'Y2LINUX-PLATFORM-V1-POWER-FINAL-14')
        self.assertEqual(self.ctx.path(d.PATH).stat().st_mode & 0o777, 0o600)

    def test_golden_is_read_only_after_linux_returned(self):
        d.record(self.ctx, 'kernel_suspend')
        self.assertNotIn('golden', self.rows()[-1]['features'])

    def test_kernel_tail_keeps_usb_and_sleep_lines_only(self):
        tail = d.kernel_tail(self.ctx)
        self.assertEqual([line.split(' ', 1)[1] for line in tail],
                         ['Y2USB PHY entry savecurrent=1',
                          'y2-usb 11200000.usb: resume_noirq restored 11 bytes', 'PM: suspend exit'])

    def test_unverified_data_mount_creates_nothing(self):
        self.write('/run/y2-data-device', '/dev/other')
        self.assertFalse(d.record(self.ctx, 'kernel_resumed'))
        self.assertFalse(self.ctx.path(d.PATH).exists())

    def test_write_failure_is_counted_never_raised(self):
        diagnostics = d.Diagnostics(self.ctx)
        with patch('y2_platform.power_journal._append', side_effect=OSError('full')):
            self.assertFalse(diagnostics.record('kernel_suspend'))
        self.assertEqual(diagnostics.failures, 1)

    def test_oversized_kernel_tail_is_trimmed_not_dropped(self):
        with patch.object(d, 'ROW_LIMIT', 6000), \
                patch.object(d, 'kernel_tail', return_value=['Y2USB ' + 'x' * 200] * 80):
            self.assertTrue(d.record(self.ctx, 'kernel_suspend'))
        row = self.rows()[-1]
        self.assertTrue(0 < len(row['kernel_tail']) < 80)

    def test_usb_change_writes_a_row_and_one_follow_up(self):
        diagnostics = d.Diagnostics(self.ctx)
        self.assertFalse(diagnostics.observe_usb(now=0))
        self.write('/sys/class/udc/musb-hdrc.4.auto/state', 'not attached')
        self.assertTrue(diagnostics.observe_usb(now=1))
        self.assertFalse(diagnostics.observe_usb(now=2))
        self.assertTrue(diagnostics.observe_usb(now=31))
        self.assertFalse(diagnostics.observe_usb(now=62))
        self.assertEqual([row['usb_reason'] for row in self.rows()], ['udc_change', 'udc_follow_up'])

    def test_cable_flapping_is_rate_limited_and_still_followed_up(self):
        diagnostics = d.Diagnostics(self.ctx)
        diagnostics.observe_usb(now=0)
        for now, state in enumerate(['not attached', 'configured'] * 4, start=1):
            self.write('/sys/class/udc/musb-hdrc.4.auto/state', state)
            diagnostics.observe_usb(now=now)
        self.assertEqual(len(self.rows()), 1)
        diagnostics.observe_usb(now=8 + d.FOLLOW_UP_S)
        self.assertEqual([row['usb_reason'] for row in self.rows()], ['udc_change', 'udc_follow_up'])

    def test_follow_up_close_to_another_row_is_postponed_not_lost(self):
        diagnostics = d.Diagnostics(self.ctx)
        diagnostics.observe_usb(now=0)
        self.write('/sys/class/udc/musb-hdrc.4.auto/state', 'not attached')
        diagnostics.observe_usb(now=1)
        diagnostics.record('kernel_suspend', now=30)
        self.assertFalse(diagnostics.observe_usb(now=31))
        self.assertTrue(diagnostics.observe_usb(now=40))
        self.assertEqual([row['usb_reason'] for row in self.rows()], ['udc_change', None, 'udc_follow_up'])

    def test_rotation_keeps_the_previous_file(self):
        with patch.object(d, 'LIMIT', 3000):
            for _ in range(4):
                d.record(self.ctx, 'kernel_suspend')
        self.assertTrue(self.ctx.path(d.PATH).with_suffix('.previous.jsonl').exists())
        self.assertEqual(self.rows()[-1]['stage'], 'kernel_suspend')

    def test_power_journal_rows_carry_the_usb_snapshot(self):
        PowerJournal(self.ctx).observe('Normal', {'status': 'Discharging'}, now=0)
        row = json.loads(self.ctx.path(JOURNAL).read_text().splitlines()[-1])
        self.assertEqual(row['usb_net']['usb0']['statistics']['tx_packets'], 7)
        self.assertLess(len(json.dumps(row)), 16384)

    def test_suspend_stages_write_rows_but_refusals_do_not(self):
        suspend_record(self.ctx, 'refused_charger_active', 2)
        self.assertEqual(self.rows(), [])
        suspend_record(self.ctx, 'quiescing_radios', 0)
        suspend_record(self.ctx, 'kernel_suspend', 0)
        self.assertEqual([row['stage'] for row in self.rows()], ['kernel_suspend'])


if __name__ == '__main__':
    unittest.main()
