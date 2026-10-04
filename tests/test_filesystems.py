"""Real filesystem/checker behavior on newly created host scratch images only."""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest


class Filesystems(unittest.TestCase):
    def image(self, directory, size=64 * 1024**2):
        path = Path(directory) / 'scratch.img'
        with path.open('xb') as stream:
            stream.truncate(size)
        return path

    def digest(self, path):
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()

    def run_tool(self, *argv):
        return subprocess.run(argv, capture_output=True, text=True,
                              env={**os.environ, 'LC_ALL': 'C.UTF-8'}, timeout=30)

    @unittest.skipUnless(shutil.which('mkfs.fat') and shutil.which('fsck.fat')
                         and shutil.which('mcopy'), 'native FAT tools required')
    def test_fat32_unicode_long_names_hashes_and_read_only_dirty_check(self):
        with tempfile.TemporaryDirectory() as directory:
            image = self.image(directory)
            self.assertEqual(self.run_tool('mkfs.fat', '-F', '32', str(image)).returncode, 0)
            original = Path(directory) / ('音楽-Été-' + 'a' * 180 + '.flac')
            original.write_bytes(bytes(range(256)) * 4096)
            self.assertEqual(self.run_tool('mcopy', '-i', str(image), str(original), '::').returncode, 0)
            copy = Path(directory) / 'readback'
            self.assertEqual(self.run_tool('mcopy', '-i', str(image), '::' + original.name,
                                          str(copy)).returncode, 0)
            self.assertEqual(self.digest(original), self.digest(copy))
            before = self.digest(image)
            self.assertEqual(self.run_tool('fsck.fat', '-n', str(image)).returncode, 0)
            self.assertEqual(self.digest(image), before)
            # Only this new image: clear FAT32's clean-unmount bit in both FATs.
            with image.open('r+b') as stream:
                boot = stream.read(512)
                sector = struct.unpack_from('<H', boot, 11)[0]
                reserved = struct.unpack_from('<H', boot, 14)[0]
                fats = boot[16]
                fat_sectors = struct.unpack_from('<I', boot, 36)[0]
                for index in range(fats):
                    offset = (reserved + index * fat_sectors) * sector + 4
                    stream.seek(offset)
                    flags = struct.unpack('<I', stream.read(4))[0]
                    stream.seek(offset)
                    stream.write(struct.pack('<I', flags & ~(1 << 27)))
            dirty = self.digest(image)
            checked = self.run_tool('fsck.fat', '-n', str(image))
            self.assertIn('Dirty bit is set', checked.stdout)
            self.assertNotEqual(checked.returncode, 0)
            self.assertEqual(self.digest(image), dirty)

    @unittest.skipUnless(shutil.which('mkfs.exfat') and shutil.which('fsck.exfat'),
                         'native exFAT tools required')
    def test_exfat_read_only_checker_preserves_new_image(self):
        with tempfile.TemporaryDirectory() as directory:
            image = self.image(directory)
            self.assertEqual(self.run_tool('mkfs.exfat', str(image)).returncode, 0)
            before = self.digest(image)
            self.assertEqual(self.run_tool('fsck.exfat', '-n', str(image)).returncode, 0)
            self.assertEqual(self.digest(image), before)

    @unittest.skipUnless(shutil.which('mkfs.ext4') and shutil.which('e2fsck'),
                         'native ext4 tools required')
    def test_ext4_read_only_checker_preserves_new_image(self):
        with tempfile.TemporaryDirectory() as directory:
            image = self.image(directory)
            self.assertEqual(self.run_tool('mkfs.ext4', '-q', '-F', str(image)).returncode, 0)
            before = self.digest(image)
            self.assertEqual(self.run_tool('e2fsck', '-f', '-n', str(image)).returncode, 0)
            self.assertEqual(self.digest(image), before)


if __name__ == '__main__':
    unittest.main()
