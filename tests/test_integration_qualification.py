"""Coordinator ownership, identity and evidence gates, without device access."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/development'))
from device_lease import open_lease

spec = importlib.util.spec_from_file_location('integration_campaign', ROOT / 'tools/development/qualify-platform-v1-integration.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


class Coordinator(unittest.TestCase):
    def test_nonblocking_lease_inheritance_preserves_parent_and_rejects_wrong_inode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'device.lock'
            with open_lease(path=path) as parent:
                with self.assertRaises(BlockingIOError):
                    open_lease(path=path)
                with open_lease(parent.fileno(), path=path):
                    pass
                with self.assertRaises(BlockingIOError):
                    open_lease(path=path)
                other = Path(directory) / 'other.lock'
                other.touch()
                with self.assertRaisesRegex(ValueError, 'inode'):
                    open_lease(parent.fileno(), path=other)
            with open_lease(path=path):
                pass

    def test_exact_source_taint_and_boot_gates_do_not_promote_observation(self):
        expected = h.expected_identity(dict(build_git_commit='a' * 40, reborn_source_commit='b' * 40,
                                            kernel_version='kernel', rootfs_version='root'))
        sample = {'schema': 'org.y2linux.status/v1', 'record': {
            'y2linux_commit': 'a' * 40, 'reborn_commit': 'b' * 40,
            'kernel': 'kernel', 'rootfs_release': 'root', 'boot_id': 'one'},
            'system': {'kernel_taint': 0}}
        self.assertEqual(h.check_identity(sample, expected), 'one')
        sample['record']['reborn_commit'] = 'c' * 40
        with self.assertRaisesRegex(ValueError, 'identity'):
            h.check_identity(sample, expected)
        sample['record']['reborn_commit'] = 'b' * 40
        with self.assertRaisesRegex(ValueError, 'boot change'):
            h.check_identity(sample, expected, 'two')
        sample['system']['kernel_taint'] = 1
        with self.assertRaisesRegex(ValueError, 'tainted'):
            h.check_identity(sample, expected)
        plan = h.plan()
        self.assertEqual(plan['state'], 'PHYSICAL_QUALIFICATION_PENDING')
        self.assertFalse(plan['endurance_qualified'])

    def test_failed_or_missing_child_receipt_stops_even_with_zero_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            package = base / 'package'
            package.mkdir()
            (package / 'manifest.json').write_text(json.dumps(dict(build_git_commit='a' * 40,
                reborn_source_commit='b' * 40, kernel_version='kernel', rootfs_version='root')))
            args = argparse.Namespace(package=package, output=base / 'capture',
                                      suspend_stage='none')
            with open_lease(path=base / 'lock') as lease:
                launches = []
                def runner(argv, **kwargs):
                    launches.append(argv)
                    output = args.output / 'suspend'
                    output.mkdir(exist_ok=True)
                    (output / 'verdict.json').write_text(json.dumps({'pass': False, 'deep_resume': False}))
                    return subprocess.CompletedProcess(argv, 0)
                campaign = h.Campaign(args, lease, runner)
                with patch.object(campaign, 'observe'):
                    with self.assertRaisesRegex(RuntimeError, 'failed'):
                        campaign.child('suspend', ['fixture'])
                self.assertEqual(len(launches), 1)
                self.assertEqual(campaign.results[-1]['state'], 'FAIL')
                receipt = json.loads((args.output / 'campaign.json').read_text())
                self.assertEqual(receipt['physical_acceptance'], 'PENDING_EVIDENCE_REVIEW')

    def test_read_timeout_may_use_wifi_without_replaying_mutation(self):
        campaign = object.__new__(h.Campaign)
        campaign.args = argparse.Namespace(host='usb', wifi_host='wifi', ssh_config=Path('fixture'))
        attempts = []
        def runner(argv, **kwargs):
            attempts.append(argv[-2])
            if len(attempts) == 1:
                raise subprocess.TimeoutExpired(argv, 30)
            return subprocess.CompletedProcess(argv, 0, '{}', '')
        campaign.runner = runner
        self.assertEqual(campaign.read(['fixture']), {})
        self.assertEqual(attempts, ['usb', 'wifi'])


if __name__ == '__main__':
    unittest.main()
