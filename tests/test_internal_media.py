"""Y2Media (eMMC p8): exact-identity mount, owner-confirmed provisioning, verified migration."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/platform'))
from y2_platform import internal_media as im
from y2_platform.common import Context
from y2_platform.observe import storage

STOCK_SERIAL = '3F93-07E6'
MOUNT_LINE = '9 1 179:8 / /media/internal rw - ext4 /dev/mmcblk0p8 rw'


class InternalMedia(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ctx = Context(self.temp.name)
        self.put('/proc/sys/kernel/random/boot_id', 'boot-one')
        self.put('/proc/self/mountinfo', '')
        self.add_partition('mmcblk0p8', '3742720', '11460608', '179:8')
        self.add_partition('mmcblk0p7', '2104320', '1638400', '179:7')
        self.fs = {'TYPE': 'vfat', 'UUID': STOCK_SERIAL}
        self.calls = []
        self.fsck_ok = True
        self.mkfs_ok = True

        def runner(argv, **kwargs):
            self.calls.append(argv)
            ok = {'ok': True, 'reason': None, 'output': ''}
            if argv[0] == 'blkid':
                text = '\n'.join('%s=%s' % kv for kv in self.fs.items())
                return {'ok': True, 'reason': None, 'output': text}
            if argv[0] == 'e2fsck':
                return ok if self.fsck_ok else {'ok': False, 'reason': 'command_failed', 'output': None}
            if argv[0] == 'mkfs.ext4':
                if not self.mkfs_ok:
                    return {'ok': False, 'reason': 'command_failed', 'output': None}
                self.fs = {'TYPE': 'ext4', 'LABEL': argv[argv.index('-L') + 1], 'UUID': argv[argv.index('-U') + 1]}
                return ok
            if argv[0] == 'mount':
                self.put('/proc/self/mountinfo', MOUNT_LINE)
                return ok
            if argv[0] == 'umount':
                self.put('/proc/self/mountinfo', '')
                return ok
            return ok
        self.ctx.runner = runner

    def put(self, path, value):
        p = self.ctx.path(path)
        p.parent.mkdir(exist_ok=True, parents=True)
        if isinstance(value, bytes):
            p.write_bytes(value)
        else:
            p.write_text(value)
        return p

    def add_partition(self, name, start, size, dev):
        disk = self.ctx.path('/sys/devices/platform/11230000.mmc/block/mmcblk0')
        part = disk / name
        part.mkdir(parents=True, exist_ok=True)
        for key, value in (('partition', name[-1]), ('start', start), ('size', size), ('dev', dev)):
            (part / key).write_text(value)
        link = self.ctx.path('/sys/class/block/' + name)
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(part)
        dev_link = self.ctx.path('/sys/dev/block/' + dev)
        dev_link.parent.mkdir(parents=True, exist_ok=True)
        dev_link.symlink_to(part)

    def provisioned(self):
        self.fs = {'TYPE': 'ext4', 'LABEL': im.LABEL, 'UUID': im.UUID}

    def names(self):
        return [c[0] for c in self.calls]

    # ---- identity -------------------------------------------------------------------------

    def test_partition_needs_the_exact_geometry_on_the_internal_controller_only(self):
        self.assertEqual(im.partition(self.ctx).name, 'mmcblk0p8')
        self.ctx.path('/sys/devices/platform/11230000.mmc/block/mmcblk0/mmcblk0p8/size').write_text('11460607')
        self.assertIsNone(im.partition(self.ctx))
        self.ctx.path('/sys/devices/platform/11230000.mmc/block/mmcblk0/mmcblk0p8/size').write_text(im.SIZE)
        # the same numbers on the removable-card controller are not Y2Media
        sd = self.ctx.path('/sys/devices/platform/11240000.mmc/block/mmcblk1/mmcblk1p9')
        sd.mkdir(parents=True)
        for key, value in (('partition', '9'), ('start', im.START), ('size', im.SIZE)):
            (sd / key).write_text(value)
        self.ctx.path('/sys/class/block/mmcblk1p9').symlink_to(sd)
        self.assertEqual(im.partition(self.ctx).name, 'mmcblk0p8')

    def test_mount_checks_then_mounts_only_the_exact_identity(self):
        self.provisioned()
        result = im.mount(self.ctx)
        self.assertEqual((result['state'], result['reason']), ('Ready', None))
        order = self.names()
        self.assertLess(order.index('e2fsck'), order.index('mount'))
        mount = next(c for c in self.calls if c[0] == 'mount')
        self.assertEqual(mount[:4], ['mount', '-t', 'ext4', '-o'])
        self.assertEqual(mount[4], 'rw,nosuid,nodev,noexec,relatime')
        self.assertEqual(mount[5:], ['/dev/mmcblk0p8', '/media/internal'])
        self.assertEqual(next(c for c in self.calls if c[0] == 'e2fsck')[:2], ['e2fsck', '-p'])
        self.assertTrue(im.ready(self.ctx))
        self.assertEqual(im.music_root(self.ctx), '/media/internal/music')
        # idempotent: an existing exact mount is recorded, not remounted
        self.calls.clear()
        self.assertEqual(im.mount(self.ctx)['state'], 'Ready')
        self.assertNotIn('mount', self.names())

    def test_nothing_else_is_ever_mounted(self):
        for fs in ({'TYPE': 'vfat', 'UUID': STOCK_SERIAL},
                   {'TYPE': 'ext4', 'LABEL': 'Y2DATA', 'UUID': im.UUID},
                   {'TYPE': 'ext4', 'LABEL': im.LABEL, 'UUID': '79324c69-6e75-4801-8000-000000000102'},
                   {'TYPE': 'exfat', 'LABEL': im.LABEL, 'UUID': im.UUID}, {}):
            self.fs, self.calls = fs, []
            result = im.mount(self.ctx)
            self.assertEqual((result['state'], result['reason']), ('Unavailable', 'filesystem_identity_not_y2media'), fs)
            self.assertNotIn('mount', self.names())
            self.assertNotIn('e2fsck', self.names())
        self.assertFalse(im.ready(self.ctx))
        self.assertEqual(im.music_root(self.ctx), '/data/music')

    def test_failed_check_or_foreign_mount_is_not_ready(self):
        self.provisioned()
        self.fsck_ok = False
        self.assertEqual(im.mount(self.ctx)['reason'], 'filesystem_check_failed')
        self.assertNotIn('mount', self.names())
        self.fsck_ok = True
        self.put('/proc/self/mountinfo', '9 1 179:7 / /media/internal rw - ext4 /dev/mmcblk0p7 rw')
        self.assertEqual((im.mount(self.ctx)['state'], im.mount(self.ctx)['reason']), ('Failed', 'foreign_mount_at_path'))
        self.assertFalse(im.ready(self.ctx))

    def test_ready_follows_the_live_mount_and_this_boot(self):
        self.provisioned()
        im.mount(self.ctx)
        self.assertTrue(im.ready(self.ctx))
        self.put('/proc/self/mountinfo', '10 1 179:8 / /media/internal rw - ext4 /dev/mmcblk0p8 rw')   # remounted: new id
        self.assertFalse(im.ready(self.ctx))
        self.put('/proc/self/mountinfo', MOUNT_LINE)
        self.assertTrue(im.ready(self.ctx))
        self.put('/proc/sys/kernel/random/boot_id', 'boot-two')
        self.assertFalse(im.ready(self.ctx))
        self.put('/proc/sys/kernel/random/boot_id', 'boot-one')
        self.put('/proc/self/mountinfo', '')
        self.assertFalse(im.ready(self.ctx))

    def test_storage_reports_the_fourth_volume_and_rejects_the_wrong_uuid(self):
        self.provisioned()
        self.put('/proc/self/mountinfo', MOUNT_LINE)
        self.ctx.path('/media/internal').mkdir(parents=True)
        volumes = storage(self.ctx)['volumes']
        self.assertEqual(len(volumes), 4)
        self.assertEqual(volumes[3]['path'], '/media/internal')
        self.fs = {'TYPE': 'ext4', 'LABEL': im.LABEL, 'UUID': 'something-else'}
        self.ctx.runner = lambda argv, **k: {'ok': True, 'reason': None, 'output': 'something-else'}
        self.assertEqual(storage(self.ctx)['volumes'][3]['reason'], 'filesystem_identity_invalid')

    # ---- provisioning ---------------------------------------------------------------------

    def music(self, files):
        for name, data in files.items():
            self.put('/data/music/' + name, data)
        self.ctx.path('/media/internal').mkdir(parents=True, exist_ok=True)

    def test_provision_needs_the_stock_serial_and_replaces_nothing_else(self):
        for fs, confirm, reason in (({'TYPE': 'vfat', 'UUID': STOCK_SERIAL}, None, 'confirmation_does_not_match_stock_filesystem'),
                                    ({'TYPE': 'vfat', 'UUID': STOCK_SERIAL}, 'AAAA-BBBB', 'confirmation_does_not_match_stock_filesystem'),
                                    ({'TYPE': 'ext4', 'LABEL': 'Y2DATA', 'UUID': 'x'}, 'x', 'confirmation_does_not_match_stock_filesystem'),
                                    ({'TYPE': 'ntfs', 'UUID': 'x'}, 'x', 'confirmation_does_not_match_stock_filesystem')):
            self.fs, self.calls = fs, []
            result = im.provision(self.ctx, confirm)
            self.assertEqual((result['state'], result['reason']), ('Failed', reason), (fs, confirm))
            self.assertNotIn('mkfs.ext4', self.names())

    def test_a_mounted_foreign_filesystem_is_never_replaced(self):
        self.put('/proc/self/mountinfo', '9 1 179:8 / /mnt/other rw - vfat /dev/mmcblk0p8 rw')
        result = im.provision(self.ctx, STOCK_SERIAL)
        self.assertEqual((result['state'], result['reason']), ('Failed', 'partition_is_mounted'))
        self.assertNotIn('mkfs.ext4', self.names())

    def test_provision_formats_the_confirmed_stock_fat_mounts_and_creates_the_music_folder(self):
        self.ctx.path('/media/internal').mkdir(parents=True)
        result = im.provision(self.ctx, STOCK_SERIAL, migrate_music=False)
        self.assertEqual((result['state'], result['reason']), ('Ready', None))
        mkfs = next(c for c in self.calls if c[0] == 'mkfs.ext4')
        self.assertEqual(mkfs[-1], '/dev/mmcblk0p8')
        self.assertEqual(mkfs[mkfs.index('-L') + 1], 'Y2MEDIA')
        self.assertEqual(mkfs[mkfs.index('-U') + 1], im.UUID)
        self.assertEqual(mkfs[mkfs.index('-m') + 1], '0')
        self.assertLess(self.names().index('mkfs.ext4'), self.names().index('mount'))
        self.assertTrue(self.ctx.path('/media/internal/music').is_dir())
        self.assertEqual(sum(1 for c in self.calls if c[0] == 'mkfs.ext4'), 1)

    def test_a_failed_mkfs_leaves_the_state_failed_and_mounts_nothing(self):
        self.mkfs_ok = False
        result = im.provision(self.ctx, STOCK_SERIAL)
        self.assertEqual(result['state'], 'Failed')
        self.assertTrue(result['reason'].startswith('mkfs_failed'))
        self.assertNotIn('mount', self.names())

    def test_provision_moves_the_library_with_hashes_and_removes_only_verified_originals(self):
        self.music({'a.flac': b'A' * 3000, 'album/b.mp3': b'B' * 70000, 'album/disc2/c.ogg': b'C' * 11})
        os.utime(self.ctx.path('/data/music/a.flac'), ns=(1_000_000_000, 1_700_000_000_000_000_000))
        result = im.provision(self.ctx, STOCK_SERIAL)
        self.assertEqual(result['state'], 'Ready')
        self.assertEqual(result['migration'], {'files': 3, 'bytes': 73011, 'copied': 3, 'removed': 3})
        for name, data in (('a.flac', b'A' * 3000), ('album/b.mp3', b'B' * 70000), ('album/disc2/c.ogg', b'C' * 11)):
            self.assertEqual(self.ctx.path('/media/internal/music/' + name).read_bytes(), data)
            self.assertFalse(self.ctx.path('/data/music/' + name).exists())
        self.assertEqual(self.ctx.path('/media/internal/music/a.flac').stat().st_mtime_ns, 1_700_000_000_000_000_000)
        self.assertTrue(self.ctx.path('/data/music').is_dir())                    # the folder itself stays
        self.assertFalse(list(self.ctx.path('/media/internal/music').rglob('*.part')))

    def test_any_migration_problem_keeps_every_original(self):
        self.music({'a.flac': b'A' * 100, 'b.flac': b'B' * 100})
        with patch.object(im, 'digest', side_effect=lambda path: 'x' if path.endswith('.part') else 'y'):
            result = im.provision(self.ctx, STOCK_SERIAL)
        self.assertEqual(result['state'], 'Degraded')
        self.assertIn('migration_hash_mismatch', result['reason'])
        for name in ('a.flac', 'b.flac'):
            self.assertTrue(self.ctx.path('/data/music/' + name).exists())
        self.assertFalse(list(self.ctx.path('/media/internal/music').rglob('*.part')))

    def test_symlinks_special_files_and_oversized_libraries_are_refused_untouched(self):
        self.music({'a.flac': b'A' * 100})
        outside = self.ctx.path('/data/elsewhere')
        outside.mkdir()
        self.ctx.path('/data/music/link').symlink_to(outside, target_is_directory=True)
        result = im.provision(self.ctx, STOCK_SERIAL)
        self.assertEqual(result['state'], 'Degraded')
        self.assertIn('migration_refuses_symlink', result['reason'])
        self.assertTrue(self.ctx.path('/data/music/a.flac').exists())
        self.ctx.path('/data/music/link').unlink()
        self.provisioned()
        with patch.object(im, 'RESERVE', 1 << 62):
            result = im.provision(self.ctx, None)
        self.assertIn('migration_does_not_fit', result['reason'])
        self.assertTrue(self.ctx.path('/data/music/a.flac').exists())

    def test_rerun_after_success_is_idempotent_and_resumes_a_partial_copy(self):
        self.music({'a.flac': b'A' * 100})
        self.assertEqual(im.provision(self.ctx, STOCK_SERIAL)['state'], 'Ready')
        self.calls.clear()
        again = im.provision(self.ctx, None)                       # already Y2Media: no confirmation, no mkfs
        self.assertEqual(again['state'], 'Ready')
        self.assertNotIn('mkfs.ext4', self.names())
        # a previously copied but not yet removed file is recognised by hash, not duplicated
        self.put('/data/music/b.flac', 'B' * 50)
        self.put('/media/internal/music/b.flac', 'B' * 50)
        result = im.provision(self.ctx, None)
        self.assertEqual(result['migration']['copied'], 0)
        self.assertEqual(result['migration']['removed'], 1)
        # but a different file at the same name is never overwritten
        self.put('/data/music/c.flac', 'one')
        self.put('/media/internal/music/c.flac', 'two!')
        result = im.provision(self.ctx, None)
        self.assertIn('migration_target_differs', result['reason'])
        self.assertTrue(self.ctx.path('/data/music/c.flac').exists())

    def test_unmount_and_status(self):
        self.provisioned()
        im.mount(self.ctx)
        self.assertTrue(im.status(self.ctx)['ready'])
        self.assertEqual(im.unmount(self.ctx)['reason'], 'unmounted')
        status = im.status(self.ctx)
        self.assertFalse(status['ready'])
        self.assertTrue(status['identity_valid'])
        self.assertEqual(im.unmount(self.ctx)['reason'], 'not_mounted')


if __name__ == '__main__':
    unittest.main()
