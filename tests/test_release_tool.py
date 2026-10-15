import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.production import release


class ReleaseTool(unittest.TestCase):
    def test_prune_keeps_the_workspace_and_two_release_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / 'out'
            def folder(name, age, files=()):
                path = out / name
                path.mkdir(parents=True)
                for file, text in files:
                    (path / file).parent.mkdir(parents=True, exist_ok=True)
                    (path / file).write_text(text)
                os.utime(path, (1000 + age, 1000 + age))
                return path
            folder('build', 9, [('buildroot/host/lib/x.pc', f'prefix={out}/power-final-34-build/buildroot\n')])
            for number, age in (('34', 1), ('50', 2), ('51', 3)):
                folder(f'power-final-{number}-build', age)
            for label, age in (('52', 4), ('53', 5), ('54', 6)):
                folder(f'release-{label}', age, [('summary.json', '{}'), ('update/manifest.json', '{}')]
                       + [('published.json', '{}')] * (label != '54'))
            folder('y2linux-1.0.0-beta.2-update', 3, [('manifest.json', '{}')])
            folder('y2linux-platform-v1-power-final-candidate-49', 2)
            folder('release-51-assets', 3)
            for keep in ('deep-sleep-final', 'rea', 'screenshots'):
                folder(keep, 0)
            with patch.object(release, 'OUT', out), patch.object(release, 'WORKSPACE', out / 'build'):
                removed, skipped = release.prune(2)
                # 54 was built but not published: the base stays the published 53.
                self.assertEqual(release.previous_package(out / 'release-55'), out / 'release-53/update')
            left = sorted(path.name for path in out.iterdir())
            self.assertEqual(left, ['build', 'deep-sleep-final', 'power-final-34-build', 'rea',
                                    'release-53', 'release-54', 'screenshots'])
            self.assertIn('power-final-34-build', skipped[0])  # the workspace still uses it

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
