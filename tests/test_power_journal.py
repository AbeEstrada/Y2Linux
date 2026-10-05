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
