"""Every overlay patch must reproduce its manifest result hash.

POWER-FINAL-16: run.py caches overlays by result_sha256, so a patch edit whose
manifest hash was not updated silently built the previous overlay (the MMSYS
DCM hook in 0011 never reached candidate 16).
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [Path('/src'), ROOT / '.cache/sources/linux-6.18']


class OverlayHashes(unittest.TestCase):
    def test_patches_reproduce_manifest_results(self):
        source = next((s for s in SOURCES if (s / 'Makefile').exists()), None)
        if source is None:
            self.skipTest('pinned Linux source unavailable')
        specs = json.loads((ROOT / 'kernel/patches/manifest.json').read_text())['overlays']
        with tempfile.TemporaryDirectory() as temp:
            for spec in specs:
                work = Path(temp) / 'file'
                shutil.copyfile(source / spec['path'], work)
                self.assertEqual(hashlib.sha256(work.read_bytes()).hexdigest(), spec['base_sha256'], spec['path'])
                subprocess.run(['patch', '--batch', '--fuzz=0', str(work)],
                               input=(ROOT / 'kernel/patches' / spec['patch']).read_bytes(),
                               check=True, capture_output=True)
                self.assertEqual(hashlib.sha256(work.read_bytes()).hexdigest(), spec['result_sha256'],
                                 spec['patch'])


if __name__ == '__main__':
    unittest.main()
