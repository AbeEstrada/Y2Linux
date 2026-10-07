"""Retained panic bytes survive boot capture, bounds and rotation unchanged."""
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/platform'))
from y2_platform.common import Context
from y2_platform.boot_retained import capture


class Retained(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.ctx = Context(temporary.name)
        self.put('/proc/self/mountinfo', b'1 0 0:1 / /sys/fs/pstore rw - pstore pstore rw\n')
        self.panic = self.put('/sys/fs/pstore/dmesg-ramoops-0', b'Panic#1\n\xff\x00unaltered bytes\n')
        self.put('/sys/firmware/y2_pm/previous', b'valid=1 stage=TASKS_THAWED\n')

    def put(self, name, value):
        path = self.ctx.path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
        return path

    def test_exact_bytes_private_archive_and_kernel_entries_preserved(self):
        result = capture(self.ctx, 'one', 'previous')
        self.assertTrue(result['pstore_mounted'])
        self.assertEqual(result['errors'], [])
        path = self.ctx.path(result['archive'])
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        with tarfile.open(path) as archive:
            self.assertEqual(archive.extractfile('pstore/dmesg-ramoops-0').read(), self.panic.read_bytes())
            self.assertIn(b'TASKS_THAWED', archive.extractfile('pm/previous').read())
            manifest = json.load(archive.extractfile('manifest.json'))
            self.assertEqual(manifest['previous_boot_id'], 'previous')
        self.assertTrue(self.panic.exists())

    def test_unmounted_is_distinct_and_symlink_is_never_archived(self):
        self.ctx.path('/proc/self/mountinfo').write_text('')
        result = capture(self.ctx, 'one', None)
        self.assertFalse(result['pstore_mounted'])
        self.assertFalse(any(f['name'].startswith('pstore/') for f in result['files']))
        self.ctx.path('/proc/self/mountinfo').write_text('1 0 0:1 / /sys/fs/pstore rw - pstore pstore rw\n')
        self.panic.unlink()
        self.panic.symlink_to(self.ctx.path('/proc/self/mountinfo'))
        result = capture(self.ctx, 'two', 'one')
        self.assertEqual(result['errors'][0]['source'], 'pstore/dmesg-ramoops-0')

    def test_bounds_are_explicit_and_only_old_private_archives_rotate(self):
        self.panic.write_bytes(b'x' * 500)
        with patch('y2_platform.boot_retained.MAX_BYTES', 100):
            result = capture(self.ctx, 'zero', None)
        self.assertEqual(result['errors'][0]['error'], 'retained_source_exceeds_archive_bound')
        root = self.ctx.path('/data/system/platform/retained')
        (root / 'owner-evidence.tar').write_bytes(b'keep')
        for index in range(10):
            capture(self.ctx, 'test-' + str(index), 'previous')
        self.assertEqual(len(list(root.glob('boot-*.tar'))), 8)
        self.assertEqual((root / 'owner-evidence.tar').read_bytes(), b'keep')
        self.assertEqual(self.panic.read_bytes(), b'x' * 500)
        with self.assertRaisesRegex(ValueError, 'invalid_boot_archive_identity'):
            capture(self.ctx, '../escape', None)
