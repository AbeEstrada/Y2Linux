#!/usr/bin/env python3
"""Resident clean-image PM stages and one bounded, source-matched real trial.

The host owns the device lease and supplies the freshly verified boot ID.
A live maintenance lock excludes product auto-entry during this diagnostic;
the explicit owner helper retains its own suspend/activity locks. A durable
product guard quarantines automatic entry until the host reviews the result.
Use BOOTTIME for the owner gesture schedule; never retry a failed entry.
"""
import argparse
import fcntl
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time


EXPECTED = {
    'build_id': 'Y2LINUX-PLATFORM-V1-DEEPSLEEP-FINAL-02',
    'build_git_commit': '5a32683f1ae9493c6a37bd18af3d131afb04d450',
    'reborn_source_commit': '5a9f7586dd8d80ab5afc16c6a9a7e853e7469aeb',
    'kernel_version': '6.18.0-y2linux-platform-v1-deepsleep-final-02',
}


def boottime():
    return time.clock_gettime(time.CLOCK_BOOTTIME)


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boot-id', required=True)
    parser.add_argument('--stages', action='store_true')
    parser.add_argument('--wake', choices=('power', 'rtc'), required=True)
    parser.add_argument('--alarm', type=int, required=True)
    parser.add_argument('--entry-after', type=int, required=True)
    args = parser.parse_args()
    require(30 <= args.alarm <= 600, 'existing RTC bound')
    require(15 <= args.entry_after <= 300, 'bounded gesture schedule')
    require(not args.stages or args.entry_after >= 180, 'stage schedule too short')
    require(args.wake != 'power' or args.alarm >= 300, 'Power needs generous RTC fallback')
    os.umask(0o077)
    os.environ['PATH'] = '/usr/sbin:/usr/bin:/sbin:/bin'
    sys.path.insert(0, '/usr/lib/y2-platform')
    from y2_platform.common import Context
    from y2_platform.product_sleep import guard_record, spm_state
    ctx = Context()
    versions = ctx.json('/etc/y2linux/versions.json', {})
    require(all(versions.get(k) == v for k, v in EXPECTED.items()), 'different installed source')
    require(ctx.read('/proc/sys/kernel/osrelease') == EXPECTED['kernel_version'], 'different kernel')
    require(ctx.read('/proc/sys/kernel/random/boot_id') == args.boot_id, 'different boot')
    require(ctx.read('/proc/sys/kernel/tainted') == '0', 'diagnostic taint is not admitted')
    require(spm_state(ctx).get('system_sleep_abi') == '1', 'built-in context fix absent')
    require(ctx.read('/sys/module/printk/parameters/console_suspend') == 'Y', 'normal console PM required')
    require(ctx.read('/sys/class/rtc/rtc0/wakealarm') in ('', '0'), 'existing RTC alarm')
    require('[none]' in (ctx.read('/sys/power/pm_test') or ''), 'PM test already owned')
    maintenance = os.open('/data/system/platform/.maintenance.lock',
                          os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    fcntl.flock(maintenance, fcntl.LOCK_EX | fcntl.LOCK_NB)
    root = Path('/data/logs/deepsleep-clean-' + args.boot_id[:8] + '-' + str(int(time.monotonic())))
    root.mkdir(mode=0o700)
    spec = importlib.util.spec_from_file_location('q', '/run/y2/qualify-platform-v1-suspend.py')
    q = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(q)
    backstop = q.fields(ctx.read('/sys/firmware/y2_pm/backstop_s'))
    require(backstop.get('provider') == '1' and backstop.get('armed_s') == '0'
            and backstop.get('running') == '0', 'backstop unavailable or already owned')

    def record(name, value):
        with (root / name).open('x') as stream:
            json.dump(value, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def guard():
        require(ctx.read('/proc/sys/kernel/random/boot_id') == args.boot_id, 'boot changed')
        require(ctx.read('/proc/sys/kernel/tainted') == '0', 'kernel tainted')
        require(ctx.read('/sys/class/power_supply/y2-usb-presence/online') == '0', 'USB present')
        require(ctx.read('/sys/class/power_supply/BAT0/status') == 'Discharging', 'not discharging')
        require((ctx.integer('/sys/class/power_supply/BAT0/voltage_now') or 0) >= 3800000,
                'diagnostic voltage floor')
        require(ctx.read('/sys/class/rtc/rtc0/wakealarm') in ('', '0'), 'existing alarm')
        require(spm_state(ctx).get('broken') == '0', 'SPM quarantined')

    def preserve(label):
        paths = ['/proc/interrupts', '/sys/kernel/debug/wakeup_sources',
                 '/run/y2/power.json', '/proc/uptime', '/proc/sys/kernel/random/boot_id']
        paths += [str(p) for p in Path('/sys/firmware/y2_pm').iterdir() if p.is_file()]
        record(label + '-state.json', {'boottime': boottime(), 'monotonic': time.monotonic(),
                                      'files': {p: ctx.read(p) for p in paths}})
        with (root / (label + '.tar')).open('xb') as stream:
            with tarfile.open(fileobj=stream, mode='w') as archive:
                for source in [Path('/data/system/platform'), Path('/data/reborn/logs'),
                               *Path('/data/logs').glob('system.log*')]:
                    if source.exists():
                        archive.add(source, arcname=str(source).lstrip('/'))
                # sysfs size is not the readable file length; preserve actual bytes.
                for source in sorted(Path('/sys/fs/pstore').glob('*')):
                    if source.is_file():
                        data = source.read_bytes()
                        info = tarfile.TarInfo(str(source).lstrip('/'))
                        info.size, info.mode = len(data), 0o600
                        archive.addfile(info, io.BytesIO(data))
            stream.flush()
            os.fsync(stream.fileno())
        with (root / (label + '-dmesg.txt')).open('x') as stream:
            subprocess.run(['dmesg'], stdout=stream, check=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.sync()

    record('armed.json', {'boot_id': args.boot_id, 'identity': EXPECTED, 'stages': args.stages,
                         'wake': args.wake, 'alarm': args.alarm, 'entry_after': args.entry_after,
                         'schedule_clock': 'CLOCK_BOOTTIME', 'automatic_retry': False,
                         'product_quarantine_until_host_review': True,
                         'maintenance_lock_pid': os.getpid()})
    print(root, flush=True)
    guard_record(ctx, True)
    try:
        deadline = boottime() + 1800
        while ctx.read('/sys/class/power_supply/y2-usb-presence/online') != '0':
            require(boottime() < deadline, 'unplug deadline')
            time.sleep(2)
        unplugged = boottime()
        record('unplugged.json', {'boottime': unplugged, 'entry_target': unplugged + args.entry_after})
        time.sleep(8)
        guard()
        preserve('before-stages')
        modes = ['freezer', 'devices', 'platform', 'processors', 'core'] if args.stages else []
        for mode in modes + ['none']:
            guard()
            # A reset during this exact attempt must not start an automatic loop.
            guard_record(ctx, True)
            if mode == 'none':
                require(boottime() < unplugged + args.entry_after - 10, 'missed real-entry schedule')
                preserve('before-real')
                require(boottime() < unplugged + args.entry_after - 2, 'archive exceeded schedule')
                time.sleep(max(0, unplugged + args.entry_after - boottime()))
                guard()
            directory = root / mode
            directory.mkdir(mode=0o700)
            record(mode + '-start.json', {'boottime': boottime(), 'monotonic': time.monotonic()})
            with (directory / 'log').open('x') as stream:
                result = subprocess.run(['python3', '-I', '/run/y2/suspend_platform_device.py',
                                         str(directory), mode, str(args.alarm if mode == 'none' else 0),
                                         args.wake], stdout=stream, stderr=stream)
            require(result.returncode == 0 and (directory / 'result.json').is_file(), 'missing return receipt')
            value = json.loads((directory / 'result.json').read_text())
            verdict = q.verdict(value)
            record(mode + '-verdict.json', verdict)
            require(verdict['pass'], 'failed ' + mode + ' verdict; no retry')
            time.sleep(2)
        record('complete.json', {'same_boot': ctx.read('/proc/sys/kernel/random/boot_id') == args.boot_id,
                                'boottime': boottime(), 'review_required': True})
    except Exception as error:
        record('error.json', {'type': type(error).__name__, 'error': str(error), 'boottime': boottime()})
        raise
    finally:
        # The host clears this only after reviewing the actual clean return.
        guard_record(ctx, True)
        record('finished.json', {'boottime': boottime(), 'quarantined': True})
        os.close(maintenance)


if __name__ == '__main__':
    main()
