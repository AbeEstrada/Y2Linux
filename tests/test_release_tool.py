import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.production import release


class ReleaseTool(unittest.TestCase):
    def test_copied_builds_forget_every_origin_folder(self):
        # Beta 2's build still read .pc/.la files of build 34 through a chain of copies.
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / 'out'
            folder = out / 'power-final-52-build'
            (folder / 'buildroot/host/lib').mkdir(parents=True)
            old34, old51 = out / 'power-final-34-build', out / 'power-final-51-build'
            pc = folder / 'buildroot/host/lib/expat.pc'
            pc.write_text(f'prefix={old34}/buildroot/host\nlibdir={old51}/buildroot/staging/usr/lib\n'
                          f'log={old51}.stdout other=/elsewhere/out/x-build/y\n')
            binary = folder / 'buildroot/host/lib/blob.so'
            binary.write_bytes(b'\0ELF' + os.fsencode(old34) + b'/lib\0')
            os.utime(pc, ns=(1, 2))
            script = folder / 'buildroot/host/lib/libtoolize'
            script.write_text(f'#!/bin/sh\nprefix={old34}/buildroot/host\n')
            script.chmod(0o555)
            with patch.object(release, 'OUT', out), \
                    patch.object(release, 'BUILD_PATH', release.re.compile(
                        release.re.escape(os.fsencode(out)) + rb'/[A-Za-z0-9._-]+-build(?![A-Za-z0-9._-])')), \
                    patch.object(release, 'PROJECT', Path(temporary)):
                self.assertEqual(release.relocate(folder), 2)
            text = pc.read_text()
            self.assertNotIn('power-final-34-build', text)
            self.assertEqual(text.count(f'{folder}/buildroot'), 2)
            self.assertIn(f'{old51}.stdout', text)  # not a build folder path
            self.assertIn('/elsewhere/out/x-build/y', text)  # outside this project
            self.assertEqual(pc.stat().st_mtime_ns, 2)  # make sees nothing new
            self.assertIn(os.fsencode(old34), binary.read_bytes())  # binaries are never rewritten
            self.assertEqual(script.stat().st_mode & 0o777, 0o555)  # read-only files too, mode kept
            self.assertIn(str(folder), script.read_text())

    def test_source_archives_are_reproducible(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'legal-info'
            (root / 'sources/zlib-1').mkdir(parents=True)
            (root / 'sources/zlib-1/zlib.tar.gz').write_bytes(b'zlib')
            (root / 'host-sources/m4-1').mkdir(parents=True)
            (root / 'host-sources/m4-1/m4.tar.xz').write_bytes(b'm4')
            digests = []
            for attempt in range(2):
                for path in root.rglob('*'):
                    os.utime(path, (1000 + attempt, 1000 + attempt))
                archive = Path(temporary) / f'third-{attempt}.tar'
                release.deterministic_tar(archive, root, ['sources/zlib-1', 'host-sources'], 1700000000)
                digests.append(hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertEqual(digests[0], digests[1])
            with release.tarfile.open(archive) as tar:
                names = tar.getnames()
                self.assertEqual(names, sorted(names))
                self.assertIn('legal-info/sources/zlib-1/zlib.tar.gz', names)
                self.assertTrue(all(member.uid == 0 and member.mtime == 1700000000 for member in tar.getmembers()))


if __name__ == '__main__':
    unittest.main()
