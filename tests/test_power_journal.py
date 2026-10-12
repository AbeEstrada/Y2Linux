"""Incident retention has a low write rate and cannot defeat battery safety."""
import json
import fcntl
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/platform'))
from y2_platform.common import Context
from y2_platform.power_journal import PowerJournal, PATH


class Journal(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ctx = Context(self.temp.name)
        for name, text in {'/data/.y2data-schema': '1', '/run/y2-data-device': '/dev/data',
                           '/proc/self/mountinfo': '5 1 179:7 / /data rw - ext4 /dev/data rw',
                           '/proc/sys/kernel/random/boot_id': 'one'}.items():
            path = self.ctx.path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        self.journal = PowerJournal(self.ctx)

    def rows(self):
        return [json.loads(line) for line in self.ctx.path(PATH).read_text().splitlines()]

    def test_steady_state_only_writes_every_five_minutes(self):
        for now in range(901):
            self.journal.observe('Normal', {'voltage_uv': 3900000-now, 'status': 'Discharging'}, now=now)
        self.assertEqual(len(self.rows()), 4)
        self.assertEqual(self.rows()[-1]['monotonic_s'], 900)

    def test_state_storm_is_bounded_but_shutdown_is_immediate(self):
        for now in range(60):
            self.journal.observe('Normal', {'status': 'Charging' if now % 2 else 'Discharging'}, now=now)
        self.assertEqual(len(self.rows()), 1)
        self.journal.observe('ShutdownPending', {'voltage_uv': 3400000}, {'reason': 'low_battery'}, now=60)
        self.assertEqual(self.rows()[-1]['shutdown']['reason'], 'low_battery')
        self.journal.observe('Suspend', {}, event='suspend_kernel_suspend', now=61)
        self.assertEqual(self.rows()[-1]['event'], 'suspend_kernel_suspend')

    def test_rotation_keeps_complete_rows_and_private_permissions(self):
        with patch('y2_platform.power_journal.LIMIT', 200):
            for i in range(10):
                self.journal.append({'i': i, 'detail': 'x'*80})
        self.assertEqual(self.rows()[-1]['i'], 9)
        old = self.ctx.path(PATH).with_suffix('.previous.jsonl')
        self.assertEqual(json.loads(old.read_text().splitlines()[-1])['i'], 7)
        self.assertEqual(self.ctx.path(PATH).stat().st_mode & 0o777, 0o600)

    def test_missing_mount_and_write_failure_do_not_raise(self):
        self.ctx.path('/run/y2-data-device').write_text('/dev/wrong')
        self.assertFalse(self.journal.observe('ShutdownPending', {}, now=0))
        self.assertFalse(self.ctx.path(PATH).exists())
        self.ctx.path('/run/y2-data-device').write_text('/dev/data')
        with patch.object(self.journal, 'append', side_effect=OSError('full')):
            self.assertFalse(self.journal.observe('ShutdownPending', {}, event='shutdown_execute', now=1))
        self.assertEqual(self.journal.failures, 1)

    def test_competing_writer_never_blocks_safety(self):
        self.journal.observe('Normal', {}, now=0)
        lock_path = self.ctx.path(PATH).parent / '.power-journal.lock'
        with lock_path.open('r+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertFalse(self.journal.observe('ShutdownPending', {}, now=1))
        self.assertEqual(self.journal.failures, 1)
        self.assertEqual(len(self.rows()), 1)

    def test_completed_sleep_endpoints_survive_a_later_refusal(self):
        self.journal.observe('Normal', {}, now=0)
        receipt = self.ctx.path('/data/system/platform/suspend-last.json')
        completed = {'mode': 'product', 'stage': 'complete_result_0', 'cycles': 4,
                     'suspended_seconds': 1840.5, 'maintenance_wakes': 3,
                     'first_entry': {'boottime_s': 100, 'voltage_uv': 4000000},
                     'resume': {'boottime_s': 1950, 'voltage_uv': 3980000}}
        receipt.write_text(json.dumps(completed))
        self.journal.observe('Suspend', {}, event='suspend_complete_result_0', now=1)
        receipt.write_text(json.dumps({'stage': 'refused_charger_active'}))
        self.journal.observe('Suspend', {}, event='suspend_refused_charger_active', now=2)
        self.assertEqual(self.rows()[-2]['suspend'], completed)
        self.assertIsNone(self.rows()[-1]['suspend']['first_entry'])

    def test_overnight_retention_at_maximum_row_size_and_real_sleep_receipt(self):
        # An eight-hour night plus eight hours before/after must survive even
        # with the largest permitted row; rotation must not depend on SOC.
        # POWER-FINAL-16: 8 MiB files keep a full day of maximum-size rows.
        for index in range(1153):
            self.journal.append({'sample': index, 'detail': 'x' * 16200})
        old = self.ctx.path(PATH).with_suffix('.previous.jsonl')
        retained = [json.loads(line)['sample'] for path in (old, self.ctx.path(PATH))
                    for line in path.read_text().splitlines()]
        self.assertTrue(set(range(865, 1153)).issubset(retained))
        self.assertLessEqual(sum(p.stat().st_size for p in (old, self.ctx.path(PATH))), 16777216)
        receipt = self.ctx.path('/data/system/platform/suspend-last.json')
        receipt.write_text(json.dumps({'product': {'state': 'sleeping', 'request_boot_id': 'old'}}))
        self.journal.observe('Normal', {}, now=0)
        row = self.rows()[-1]
        self.assertEqual(row['sleep']['state'], 'restore_failed')
        self.assertEqual(row['sleep']['reason'], 'boot_changed_before_restoration')
        self.assertIsNotNone(row['boottime_s'])

    def test_idle_counters_are_cumulative_and_collected_only_for_due_rows(self):
        for name, value in {
                '/sys/devices/system/cpu/online': '0',
                '/sys/devices/system/cpu/cpu0/cpuidle/state2/name': 'DORMANT',
                '/sys/devices/system/cpu/cpu0/cpuidle/state2/usage': '123',
                '/sys/devices/system/cpu/cpu0/cpuidle/state2/time': '4500000',
                '/sys/devices/system/cpu/cpu0/cpuidle/state2/disable': '0',
                '/proc/stat': 'cpu 1 2 3 4\nintr 1500 100 1400\nctxt 2600\nprocesses 12\n',
                '/sys/bus/platform/devices/13010000.gpu/power/runtime_status': 'suspended',
        }.items():
            path = self.ctx.path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value)
        from y2_platform.power_journal import idle_counters
        with patch('y2_platform.power_journal.idle_counters', wraps=idle_counters) as collect:
            for now in range(601):
                self.journal.observe('Normal', {'status': 'Discharging'}, now=now)
            self.assertEqual(collect.call_count, 3)
        row = self.rows()[-1]['idle_counters']
        self.assertEqual(row['cpuidle']['0']['DORMANT']['usage'], 123)
        self.assertIsNone(row['cpuidle']['0']['DORMANT']['rejected'])
        self.assertEqual(row['scheduler'], {'intr': 1500, 'ctxt': 2600, 'processes': 12})
        self.assertEqual(row['runtime_pm']['13010000.gpu'], 'suspended')
        self.assertGreaterEqual(row['collector_cpu_seconds'], 0)
