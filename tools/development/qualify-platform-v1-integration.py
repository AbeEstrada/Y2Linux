#!/usr/bin/env python3
"""One exact-image physical campaign; default prints an offline plan.

Owner execution holds the shared nonblocking lease across existing source-bound
CPU, USB and one-shot suspend helpers. Reads may recover through Wi-Fi; child
mutating launches are never replayed by this coordinator. No flash or main/ref
mutation exists. Untested peer, desktop, input, analog and endurance lanes stay
pending instead of inheriting branch-local qualification.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

from device_lease import open_lease

ROOT = Path(__file__).resolve().parents[2]
LANES = {
    'A': 'Exact paired image identity, boot/taint, readiness, shutdown and preserving recovery.',
    'B': 'CPU/timers/hotplug/OPPs and protected C1/C2/C3, before and after sleep.',
    'C': 'Staged PM then one backstopped RTC/Power trial; same-boot COMPLETE/EXIT and product restore.',
    'D': 'DATA/SD filesystems, different-card identity, eject/reinsert and verified desktop USB transfer.',
    'E': 'Wi-Fi readiness/policy and actual Bluetooth peer/codec/reconnect/coexistence.',
    'F': 'Wired S16/44.1/48 playback; conditional wider modes require AFE/I2S capture and listening.',
    'G': 'Declared formats, metadata/artwork/library plus scanner/playback/source/USB/sleep races.',
    'H': 'DRM/GPU awake/off/wake, render/capture order, counted wheel/buttons and bounded latency.',
    'I': 'Charging/battery/offline/refusal and electrical/endurance evidence under normal owner policy.',
    'J': 'Diagnostics privacy, exact notices/source, owner distribution conditions and preserving update/recovery.',
}


def expected_identity(manifest):
    result = {k: manifest.get(k) for k in ('build_git_commit', 'reborn_source_commit',
                                         'kernel_version', 'rootfs_version')}
    for key in ('build_git_commit', 'reborn_source_commit'):
        if not isinstance(result[key], str) or not re.fullmatch('[0-9a-f]{40}', result[key]):
            raise ValueError('full compiled source pair required')
    if not all(isinstance(v, str) and v for v in result.values()):
        raise ValueError('exact kernel/root identity required')
    return result


def check_identity(sample, expected, previous_boot=None):
    record = sample.get('record', {})
    actual = dict(zip(expected, (record.get(k) for k in
                               ('y2linux_commit', 'reborn_commit', 'kernel', 'rootfs_release'))))
    if sample.get('schema') != 'org.y2linux.status/v1' or actual != expected:
        raise ValueError('integrated candidate identity mismatch')
    boot = record.get('boot_id')
    if not boot or previous_boot and boot != previous_boot:
        raise ValueError('unexpected boot change; stop physical actions')
    if sample.get('system', {}).get('kernel_taint') != 0:
        raise ValueError('tainted kernel; stop physical actions')
    return boot


def plan(package=None):
    result = {'schema': 'org.y2linux.platform-v1-integration-plan/v1', 'lanes': LANES,
              'state': 'PHYSICAL_QUALIFICATION_PENDING', 'automatic_flash': False,
              'default': 'offline plan; --run observes, explicit lane flags exercise',
              'reuse': 'Earlier unaffected receipts retain their exact source/image scope',
              'endurance_qualified': False}
    if package and (package / 'manifest.json').is_file():
        manifest = json.loads((package / 'manifest.json').read_text())
        result['expected'] = expected_identity(manifest)
        result['payloads'] = manifest.get('payloads', [])
    return result


class Campaign:
    def __init__(self, args, lease, runner=subprocess.run):
        self.args, self.lease, self.runner = args, lease, runner
        self.expected = expected_identity(json.loads((args.package / 'manifest.json').read_text()))
        self.boot = None
        self.results = []
        self.sequence = 0
        args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.save()

    def save(self):
        receipt = {'schema': 'org.y2linux.platform-v1-integration-campaign/v1',
                   'expected': self.expected, 'boot': self.boot, 'results': self.results,
                   'lanes': LANES, 'physical_acceptance': 'PENDING_EVIDENCE_REVIEW',
                   'endurance_qualified': False, 'automatic_flash': False}
        (self.args.output / 'campaign.json').write_text(json.dumps(receipt, indent=2) + '\n')

    def read(self, argv):
        failures = []
        for host in filter(None, (self.args.host, self.args.wifi_host)):
            try:
                result = self.runner(['ssh', '-F', str(self.args.ssh_config), '-oBatchMode=yes',
                                      '-oStrictHostKeyChecking=yes', '-oConnectTimeout=5',
                                      host, shlex.join(argv)], capture_output=True, text=True, timeout=30)
            except subprocess.TimeoutExpired:
                failures.append({'host': host, 'failure': 'read_timeout'})
                continue
            if result.returncode == 0:
                if len(result.stdout.encode()) > 1024 * 1024:
                    raise ValueError('bounded observation exceeded')
                return json.loads(result.stdout)
            failures.append({'host': host, 'exit': result.returncode})
        raise RuntimeError('read-only observation unavailable: ' + json.dumps(failures))

    def observe(self, label):
        sample = self.read(['y2-platform', 'status', '--json', '--reborn', '--pss'])
        self.boot = check_identity(sample, self.expected, self.boot)
        self.sequence += 1
        path = self.args.output / f'{self.sequence:03d}-{label}.json'
        path.write_text(json.dumps(sample, indent=2) + '\n')
        self.results.append({'lane': label, 'state': 'OBSERVED', 'sample': path.name,
                             'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        self.save()

    def child(self, label, argv):
        self.observe('before-' + label)
        log = self.args.output / (label + '.log')
        with log.open('w') as stream:
            # One launch, one inherited lease, no alternate-host replay.
            result = self.runner([sys.executable, *map(str, argv)], cwd=ROOT,
                                 pass_fds=(self.lease.fileno(),), stdout=stream,
                                 stderr=subprocess.STDOUT, timeout=2400)
        directory = self.args.output / label
        inspection = label == 'suspend' and self.args.suspend_stage == 'inspect'
        receipt_path = directory / ('inspect.txt' if inspection else
                                    'verdict.json' if label == 'suspend' else 'result.json')
        reported = None
        if inspection and receipt_path.is_file():
            reported = {'observation_only': True}
        elif receipt_path.is_file():
            reported = json.loads(receipt_path.read_text())
        if label.startswith('usb-'):
            passed = bool(reported and str(reported.get('result', '')).startswith('PASS'))
        elif inspection:
            passed = bool(reported)
        else:
            passed = bool(reported and reported.get('pass') is True)
            if label == 'suspend' and self.args.suspend_stage == 'none':
                passed = passed and reported.get('deep_resume') is True
        passed = passed and result.returncode == 0
        state = 'OBSERVED_INSPECTION' if passed and inspection else 'REPORTED_BOUNDED_PASS' if passed else 'FAIL'
        self.results.append({'lane': label, 'state': state,
                             'log': log.name, 'exit': result.returncode,
                             'receipt': str(receipt_path.relative_to(self.args.output)) if reported else None,
                             'receipt_sha256': hashlib.sha256(receipt_path.read_bytes()).hexdigest() if reported else None,
                             'qualification': 'Exact-image scoped receipt; human/equipment/endurance gates remain'})
        self.save()
        self.observe('after-' + label)
        if not passed:
            raise RuntimeError(label + ' failed; later physical actions stopped')

    def run(self):
        self.observe('baseline')
        if self.args.cpu:
            self.child('cpu-idle', [ROOT / 'tools/development/qualify-cpu-idle-completion.py',
                '--run', '--package', self.args.package, '--ssh-config', self.args.ssh_config,
                '--host', self.args.host, '--wifi-host', self.args.wifi_host,
                '--enable-qualified-runtime',
                '--output', self.args.output / 'cpu-idle'])
        if self.args.usb:
            for volume in self.args.volumes:
                argv = [ROOT / 'tools/usb/qualify.py', '--run', '--package', self.args.package,
                        '--ssh-config', self.args.ssh_config, '--host', self.args.host,
                        '--protocol', self.args.usb, '--volume', volume,
                        '--device-lock-fd', str(self.lease.fileno()),
                        '--output', self.args.output / ('usb-' + volume)]
                if self.args.usb == 'mtp':
                    argv.extend(['--mtp-uri', self.args.mtp_uri])
                self.child('usb-' + volume, argv)
        if self.args.suspend_stage:
            argv = [ROOT / 'tools/development/qualify-platform-v1-suspend.py',
                    '--host', self.args.suspend_host or self.args.wifi_host or self.args.host,
                    '--ssh-config', self.args.ssh_config,
                    '--key', self.args.key, '--stage', self.args.suspend_stage,
                    '--device-lock-fd', str(self.lease.fileno()),
                    '--output', self.args.output / 'suspend']
            if self.args.suspend_stage == 'none':
                argv.extend(['--alarm-seconds', '30', '--wake-source', 'rtc'])
            self.child('suspend', argv)
        self.observe('final')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=ROOT / 'out/y2linux-platform-v1-integration-candidate')
    parser.add_argument('--output', type=Path, default=ROOT / 'out/platform-v1-physical' /
                        datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--ssh-config', type=Path)
    parser.add_argument('--host', default='y2')
    parser.add_argument('--wifi-host')
    parser.add_argument('--cpu', action='store_true')
    parser.add_argument('--usb', choices=['sftp', 'mtp'])
    parser.add_argument('--volumes', choices=['internal', 'sd'], nargs='+', default=['internal'])
    parser.add_argument('--mtp-uri')
    parser.add_argument('--suspend-stage', choices=['inspect', 'freezer', 'devices', 'platform',
                                                  'processors', 'core', 'none'])
    parser.add_argument('--suspend-host')
    parser.add_argument('--key', type=Path, default=Path.home() / '.ssh/y2linux_ed25519')
    args = parser.parse_args()
    args.package, args.output = args.package.resolve(), args.output.resolve()
    if args.ssh_config:
        args.ssh_config = args.ssh_config.resolve()
    if not args.run:
        print(json.dumps(plan(args.package), indent=2))
        return 0
    if not args.ssh_config or not args.ssh_config.is_file():
        parser.error('existing authorized --ssh-config required')
    if args.cpu and not args.wifi_host:
        parser.error('CPU lane requires the independently pinned --wifi-host')
    if args.usb == 'mtp' and (not args.mtp_uri or len(args.volumes) != 1):
        parser.error('MTP requires one matching volume and its standard file-manager --mtp-uri')
    if args.suspend_stage == 'none' and (not args.cpu or not args.wifi_host):
        parser.error('one-shot full RTC requires fresh awake CPU lane and independent Wi-Fi observation')
    os.umask(0o077)
    try:
        with open_lease() as lease:
            campaign = Campaign(args, lease)
            try:
                campaign.run()
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                campaign.results.append({'lane': 'campaign', 'state': 'STOPPED', 'reason': str(error)})
                campaign.save()
                print('STOPPED; inspect campaign.json; no mutating launch is retried')
                return 2
    except BlockingIOError:
        print('NOT_RUN_DEVICE_LOCK_BUSY; no device access')
        return 2
    print('Captured one campaign; human/equipment/endurance lanes require evidence review')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
