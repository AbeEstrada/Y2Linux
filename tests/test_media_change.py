"""Explicit SD format/grow, the recycled-mount-id marker fix and the undersized report."""
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/platform'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_platform_storage_tools as base_tests
from y2_platform.common import Context
from y2_platform.media import PARTITION_START, WIPE_TAIL_SECTORS, change_card, mbr_for, operation
from y2_platform.observe import storage

SECTORS = 131072          # a 64 MiB test card
CID = 'card-cid-one'


class MediaChange(unittest.TestCase):
    card_fixture = base_tests.StorageTools.card_fixture
    put = base_tests.StorageTools.put

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ctx = Context(self.temp.name)
        self.ctx.path('/data').mkdir()
        self.put('/proc/sys/kernel/random/boot_id', 'boot-one')
        self.calls = self.card_fixture()
        disk = self.ctx.path('/sys/devices/platform/11240000.mmc/block/mmcblk1')
        (disk / 'size').write_text(str(SECTORS))
        (disk / 'dev').write_text('179:8')
        link = self.ctx.path('/sys/class/block/mmcblk1')
        link.symlink_to(disk)
        self.device = self.ctx.path('/dev/mmcblk1')
        self.device.parent.mkdir(parents=True, exist_ok=True)
        self.device.write_bytes(b'\xa5' * (SECTORS * 512))           # old contents everywhere
        self.ctx.path('/dev/mmcblk1p1').write_bytes(b'')              # node the kernel creates on re-read
        self.rereads = []
        self.ctx.ioctl = lambda fd, request: self.rereads.append(request)
        self.fs = 'exfat'
        self.inner = self.ctx.runner

        def runner(argv, **kwargs):
            self.calls.append(argv)
            if argv[0] == 'mkfs.ext4':
                self.fs = 'ext4'
            if argv[0] == 'umount':
                self.put('/proc/self/mountinfo', '')
                return {'ok': True, 'reason': None, 'output': ''}
            if argv[0] == 'blkid':
                text = 'TYPE=%s\nUUID=card-uuid-one' % self.fs
                return {'ok': True, 'reason': None, 'output': 'card-uuid-one' if 'UUID' in argv and '-s' in argv else text}
            if argv[0] == 'mount':
                self.put('/proc/self/mountinfo', '51 1 179:9 / /media/sd rw - %s /dev/mmcblk1p1 rw' % self.fs)
                return {'ok': True, 'reason': None, 'output': ''}
            return {'ok': True, 'reason': None, 'output': ''}
        self.ctx.runner = runner
        self.calls.clear()

    def names(self):
        return [c[0] for c in self.calls]

    def test_mbr_is_one_linux_partition_to_the_end_and_caps_at_32_bits(self):
        mbr = mbr_for(SECTORS)
        self.assertEqual(len(mbr), 512)
        self.assertEqual(mbr[510:], b'\x55\xaa')
        status, _, kind, _, start, size = struct.unpack('<B3sB3sII', mbr[446:462])
        self.assertEqual((status, kind, start, size), (0, 0x83, PARTITION_START, SECTORS - PARTITION_START))
        self.assertEqual(mbr[462:510], bytes(48))
        self.assertEqual(struct.unpack('<II', mbr_for(1 << 33)[454:462]), (PARTITION_START, 0xFFFFFFFF))

    def test_format_needs_the_exact_card_cid_and_touches_nothing_otherwise(self):
        before = self.device.read_bytes()
        for wrong in (None, '', 'other-card'):
            result = change_card(self.ctx, 'format', wrong)
            self.assertEqual((result['state'], result['reason']), ('Failed', 'cid_confirmation_mismatch'))
        self.assertEqual(self.device.read_bytes(), before)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.rereads, [])

    def test_format_repartitions_wipes_stale_metadata_and_mounts_the_new_filesystem(self):
        result = change_card(self.ctx, 'format', CID)
        self.assertEqual((result['state'], result['reason']), ('Ready', None))
        data = self.device.read_bytes()
        self.assertEqual(data[:512], mbr_for(SECTORS))
        # Everything between the MBR and the partition start, and the GPT backup area, is zero.
        self.assertEqual(data[512:PARTITION_START * 512], bytes((PARTITION_START - 1) * 512))
        self.assertEqual(data[-WIPE_TAIL_SECTORS * 512:], bytes(WIPE_TAIL_SECTORS * 512))
        # The partition interior is not written by the platform: mkfs owns it.
        self.assertEqual(data[PARTITION_START * 512:PARTITION_START * 512 + 512], b'\xa5' * 512)
        self.assertEqual(self.rereads, [0x125F])
        mkfs = next(c for c in self.calls if c[0] == 'mkfs.ext4')
        self.assertEqual(mkfs[-1], '/dev/mmcblk1p1')
        self.assertIn('Y2SD', mkfs)
        self.assertEqual(mkfs[mkfs.index('-m') + 1], '0')           # no root-reserved blocks on a media card
        self.assertNotIn('-J', mkfs)                                 # small card: default journal
        order = self.names()
        self.assertLess(order.index('mkfs.ext4'), order.index('mount'))
        self.assertEqual(result['action'], 'format')

    def test_large_cards_get_a_bounded_journal(self):
        big = 64 * 1024 * 1024
        (self.ctx.path('/sys/devices/platform/11240000.mmc/block/mmcblk1') / 'size').write_text(str(big))
        # Do not allocate a 32 GiB test file: exercise only the argv decision.
        from y2_platform import media
        with patch.object(media.os, 'open', return_value=3), patch.object(media.os, 'pwrite'), \
                patch.object(media.os, 'fsync'), patch.object(media.os, 'close'):
            state = {'state': 'Starting'}
            media.format_steps(self.ctx, state, '/dev/mmcblk1', big)
        mkfs = next(c for c in self.calls if c[0] == 'mkfs.ext4')
        self.assertEqual(mkfs[mkfs.index('-J') + 1], 'size=128')

    def test_mounted_card_is_released_from_mtp_even_with_a_cable_then_unmounted_before_any_write(self):
        self.assertEqual(operation(self.ctx, 'mount')['state'], 'Ready')
        self.calls.clear()
        seen = []

        def release(ctx, mount_id, explicit=False):
            seen.append((mount_id, explicit))
            # nothing may have been written yet
            self.assertEqual(self.device.read_bytes()[:512], b'\xa5' * 512)
            return True
        with patch('y2_platform.usb.release_sd', release):
            result = change_card(self.ctx, 'format', CID)
        self.assertEqual(result['state'], 'Ready')
        self.assertEqual(seen, [(51, True)])
        order = self.names()
        self.assertLess(order.index('umount'), order.index('mkfs.ext4'))

    def test_a_failed_release_or_unmount_aborts_before_any_write(self):
        operation(self.ctx, 'mount')
        self.calls.clear()
        before = self.device.read_bytes()
        with patch('y2_platform.usb.release_sd', lambda *a, **k: False):
            result = change_card(self.ctx, 'format', CID)
        self.assertEqual((result['state'], result['reason']), ('Failed', 'usb_release_failed'))
        self.assertEqual(self.device.read_bytes(), before)
        self.assertNotIn('mkfs.ext4', self.names())
        inner = self.ctx.runner
        self.ctx.runner = lambda argv, **k: ({'ok': False, 'reason': 'command_failed', 'output': None}
                                             if argv[0] == 'umount' else inner(argv, **k))
        with patch('y2_platform.usb.release_sd', lambda *a, **k: True):
            result = change_card(self.ctx, 'format', CID)
        self.assertEqual(result['state'], 'Failed')
        self.assertEqual(self.device.read_bytes(), before)

    def test_only_the_removable_card_controller_can_ever_be_formatted(self):
        # The internal eMMC disk is not a candidate, and without a card nothing is touched.
        internal = self.ctx.path('/sys/devices/platform/11230000.mmc/block/mmcblk0')
        (internal / 'device').mkdir(parents=True)
        (internal / 'device/cid').write_text('internal-cid')
        (internal / 'size').write_text('15203328')
        self.ctx.path('/sys/class/block/mmcblk0').symlink_to(internal)
        self.ctx.path('/sys/class/block/mmcblk1').unlink()
        self.ctx.path('/dev/mmcblk0').write_bytes(b'\x11' * 4096)
        for action in ('format', 'grow'):
            result = change_card(self.ctx, action, 'internal-cid')
            self.assertEqual((result['state'], result['reason']), ('Unavailable', 'no_unique_card'))
        self.assertEqual(self.ctx.path('/dev/mmcblk0').read_bytes(), b'\x11' * 4096)
        self.assertEqual(self.calls, [])

    def test_a_too_small_card_and_unknown_actions_are_refused(self):
        (self.ctx.path('/sys/devices/platform/11240000.mmc/block/mmcblk1') / 'size').write_text('100')
        self.assertEqual(change_card(self.ctx, 'format', CID)['reason'], 'card_too_small')
        with self.assertRaises(ValueError):
            change_card(self.ctx, 'wipe', CID)

    def test_partition_reread_failure_stops_before_mkfs(self):
        def refuse(fd, request):
            raise OSError(16, 'busy')
        self.ctx.ioctl = refuse
        result = change_card(self.ctx, 'format', CID)
        self.assertEqual((result['state'], result['reason']), ('Failed', 'partition_reread_failed'))
        self.assertNotIn('mkfs.ext4', self.names())

    def test_grow_checks_then_resizes_only_one_ext4_card(self):
        self.fs = 'ext4'
        result = change_card(self.ctx, 'grow')
        self.assertEqual(result['state'], 'Ready')
        order = self.names()
        self.assertLess(order.index('e2fsck'), order.index('resize2fs'))
        self.assertLess(order.index('resize2fs'), order.index('mount'))
        self.assertNotIn('mkfs.ext4', order)
        self.assertEqual(self.device.read_bytes(), b'\xa5' * (SECTORS * 512))     # grow never writes the disk itself

    def test_grow_refuses_a_foreign_or_unchecked_filesystem(self):
        result = change_card(self.ctx, 'grow')                    # exfat card
        self.assertEqual((result['state'], result['reason']), ('Failed', 'grow_requires_one_ext4_card'))
        self.assertNotIn('resize2fs', self.names())
        self.fs = 'ext4'
        self.calls.clear()
        inner = self.ctx.runner
        self.ctx.runner = lambda argv, **k: ({'ok': False, 'reason': 'command_failed', 'output': None}
                                             if argv[0] == 'e2fsck' else inner(argv, **k))
        result = change_card(self.ctx, 'grow')
        self.assertEqual((result['state'], result['reason']), ('Failed', 'filesystem_check_failed'))
        self.assertNotIn('resize2fs', self.names())

    def test_a_recycled_mount_id_cannot_leave_the_new_card_hidden(self):
        """The kernel reuses mount ids: after reformat/eject the release marker must not match again."""
        self.put('/run/y2/usb-release-sd.json', json.dumps({'mount_id': 51}))
        self.assertEqual(operation(self.ctx, 'mount')['state'], 'Ready')
        self.assertFalse(self.ctx.path('/run/y2/usb-release-sd.json').exists())

    def test_storage_reports_an_undersized_filesystem_without_changing_it(self):
        operation(self.ctx, 'mount')
        entry = self.ctx.path('/sys/class/block/mmcblk1p1')
        (entry / 'size').write_text(str(249735168))
        fake = types.SimpleNamespace(f_blocks=131072, f_bavail=100000, f_bfree=100000, f_favail=500, f_files=1000, f_frsize=4096)
        with patch('y2_platform.observe.os.statvfs', return_value=fake):
            volume = storage(self.ctx)['volumes'][2]
        self.assertEqual(volume['partition_bytes'], 249735168 * 512)
        self.assertEqual(volume['capacity_state'], 'Undersized')
        (entry / 'size').write_text(str(131072 * 8))
        with patch('y2_platform.observe.os.statvfs', return_value=fake):
            self.assertEqual(storage(self.ctx)['volumes'][2]['capacity_state'], 'Full')


if __name__ == '__main__':
    unittest.main()
