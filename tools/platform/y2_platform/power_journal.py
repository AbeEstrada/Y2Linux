"""Bounded incident history, driven by the existing safety sample; no new timer."""
# SPDX-License-Identifier: GPL-2.0-only
import json
import fcntl
import os
import stat
import time
from .boot import private_directory
from .common import read

PATH = '/data/system/platform/power-journal.jsonl'
PERIOD = 300
# Two bounded files retain at least a normal night even at the maximum row
# size (128 five-minute rows per file). No increase in sampling/write rate.
LIMIT = 2097152


def idle_counters(ctx):
    """Cheap cumulative counters only when a journal row is already due.

    No AUXADC, subprocess, RPC, tracing, or additional periodic wakeup. Missing
    interfaces stay null. Hotplug can reset per-core counters; readers must not
    turn decreasing values into negative rates.
    """
    started = time.process_time()
    idle = {}
    for cpu in range(4):
        states = {}
        for index in range(3):
            base = f'/sys/devices/system/cpu/cpu{cpu}/cpuidle/state{index}'
            name = ctx.read(base + '/name', limit=64)
            if name is not None:
                states[name] = {field: ctx.integer(base + '/' + field)
                                for field in ('usage', 'time', 'rejected', 'disable')}
        if states:
            idle[str(cpu)] = states
    scheduler = {}
    for line in (ctx.read('/proc/stat') or '').splitlines():
        fields = line.split()
        if fields and fields[0] in ('ctxt', 'intr', 'processes'):
            try:
                scheduler[fields[0]] = int(fields[1])
            except (ValueError, IndexError):
                scheduler[fields[0]] = None
    runtime = {}
    for path in ctx.glob('/sys/bus/platform/devices/*/power/runtime_status'):
        name = path.parent.parent.name
        if name.startswith(('11200000.', '11220000.', '11230000.', '11240000.',
                            '13010000.', '14007000.', '14008000.', '18070000.')):
            runtime[name] = read(path, limit=64)
    result = {'online': ctx.read('/sys/devices/system/cpu/online', limit=64),
              'cpuidle': idle, 'scheduler': scheduler, 'runtime_pm': runtime,
              'frequency_khz': ctx.integer('/sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq'),
              'frequency_ticks': ctx.read('/sys/devices/system/cpu/cpufreq/policy0/stats/time_in_state', limit=512),
              'idle_rejections': {path.name: read(path, limit=128)
                                  for path in ctx.glob('/sys/module/idle/parameters/*')},
              'clock_blockers': {path.name: read(path, limit=128)
                                 for path in ctx.glob('/sys/module/clocks/parameters/*blockers')},
              'counter_reset_rule': 'decreasing per-core counters are unknown, not negative rates'}
    result['collector_cpu_seconds'] = time.process_time() - started
    return result


class PowerJournal:
    def __init__(self, ctx):
        self.ctx = ctx
        self.next_snapshot = 0
        self.next_event = 0
        self.signature = None
        self.failures = 0
        from .sleep_diagnostics import Diagnostics
        self.diagnostics = Diagnostics(ctx)

    def observe(self, state, battery, shutdown=None, event=None, now=None):
        now = time.monotonic() if now is None else now
        try:
            # POWER-FINAL-14: persist USB state changes (and one follow-up) so a
            # USB failure after a wake leaves evidence across a restart.
            self.diagnostics.observe_usb(now)
        except (OSError, ValueError, TypeError):
            self.diagnostics.failures += 1
        signature = (state, battery.get('status'), battery.get('charging'))
        safety = state == 'ShutdownPending' and signature != self.signature
        if not (event or safety or now >= self.next_snapshot or
                (signature != self.signature and now >= self.next_event)):
            return False
        self.next_snapshot = now + PERIOD
        self.next_event = now + 60
        self.signature = signature
        try:
            # Do not create persistent state on an unverified/missing data mount.
            from .sleep_diagnostics import data_ready, usb_net
            if not data_ready(self.ctx):
                return False
            ctx = self.ctx
            from .sleep import status as sleep_status
            receipt = ctx.json('/data/system/platform/suspend-last.json', {})
            if not isinstance(receipt, dict):
                receipt = {}
            row = {'schema': 1, 'event': event or ('state_change' if safety else 'snapshot'),
                   'wall_time': time.time(), 'monotonic_s': now,
                   'boottime_s': time.clock_gettime(time.CLOCK_BOOTTIME),
                   'boot_id': ctx.read('/proc/sys/kernel/random/boot_id'),
                   'build': ctx.json('/etc/y2linux/versions.json'), 'state': state,
                   'battery': battery, 'shutdown': shutdown,
                   'usb': {p.name: read(p / 'state') for p in ctx.glob('/sys/class/udc/*')},
                   'usb_net': usb_net(ctx),
                   'charger': ctx.read('/sys/class/power_supply/BAT0/charging_state'),
                   'backlight': {p.parent.name: read(p) for p in ctx.glob('/sys/class/backlight/*/bl_power')},
                   'radios': {p.name: {'type': read(p / 'type'), 'blocked': read(p / 'soft')}
                              for p in ctx.glob('/sys/class/rfkill/*')},
                   'idle_policy': ctx.json('/run/y2/cpu-idle-policy.json'),
                   'idle_counters': idle_counters(ctx),
                   'sleep': sleep_status(ctx),
                   # Preserve completed intervals when a later refusal replaces
                   # suspend-last.json. This shares the existing event cadence.
                   'suspend': {key: receipt.get(key) for key in
                               ('mode', 'stage', 'first_entry', 'resume', 'cycles',
                                'suspended_seconds', 'maintenance_wakes')},
                   'kernel_pm': ctx.read('/sys/firmware/y2_pm/state', limit=8192)}
            self.append(row, durable=bool(event or safety))
            return True
        except (OSError, ValueError, TypeError):
            # A journal failure must never delay or disable battery protection.
            self.failures += 1
            return False

    def append(self, row, durable=False):
        encoded = (json.dumps(row, separators=(',', ':')) + '\n').encode()
        if len(encoded) > 16384:
            raise ValueError('power_journal_row_too_large')
        append_bounded(self.ctx, PATH, encoded, LIMIT, durable)


def append_bounded(ctx, name, encoded, limit, durable=False):
    """Append one complete row to a private file on Y2DATA; rotate once at `limit`."""
    path = ctx.path(name)
    private_directory(path.parent)
    lock = os.open(path.parent / ('.' + path.stem + '.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _append(path, encoded, limit, durable)
    finally:
        os.close(lock)


def _append(path, encoded, limit, durable):
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('power_journal_not_regular')
        if os.fstat(fd).st_size + len(encoded) > limit:
            os.close(fd)
            fd = -1
            os.replace(path, path.with_suffix('.previous.jsonl'))
            fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        # Regular-file append is bounded; handle short writes without dropping a row.
        remaining = memoryview(encoded)
        while remaining:
            n = os.write(fd, remaining)
            if n <= 0:
                raise OSError('power_journal_short_write')
            remaining = remaining[n:]
        if durable:
            os.fsync(fd)
    finally:
        if fd >= 0:
            os.close(fd)
