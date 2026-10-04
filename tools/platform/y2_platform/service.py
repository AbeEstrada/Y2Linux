"""Bounded readiness/maintenance work, separate from the battery deadline owner."""
# SPDX-License-Identifier: GPL-2.0-only
import fcntl
import os
import signal
import time
from .boot import private_directory
import json
from .common import atomic_json, read
from .media import inventory
from .network import DnsProbeSchedule, EventMonitor, probe_dns
from .observe import wifi
from .timekeeping import status as time_status


# Fix02 background attribution: every iteration used to start a complete
# Python interpreter for `media reconcile` (every 3 s) plus two more every
# 30 s. On the Y2 that recurring start-up work drove schedutil to 1040 MHz
# and >10% samples during screen-off idle. The reconcile subprocess is still
# the only owner of mount/unmount work; it is now started only when its own
# no-op condition (unchanged SD inventory, no retry) is false.
INTERVAL_S = 3
DARK_INTERVAL_S = 10  # Reborn treats network.json older than 15 s as stale
MAINTENANCE_S = 30
DARK_MAINTENANCE_S = 300


def display_dark(ctx):
    """Same meaning as the kernel's backlight_is_blank(): Reborn blanks with
    bl_power=4 (FB_BLANK_POWERDOWN) and leaves brightness unchanged."""
    devices = ctx.glob('/sys/class/backlight/*')
    states = [(read(path / 'bl_power'), read(path / 'brightness')) for path in devices]
    return bool(states) and all(power not in (None, '0') or brightness == '0' for power, brightness in states)


def media_reconcile_needed(ctx):
    """Mirror media.reconcile's own early return without mounting anything."""
    lifecycle = ctx.json('/run/y2/media-lifecycle.json', {})
    current = [list(v) for v in inventory(ctx)]
    return not isinstance(lifecycle, dict) or lifecycle.get('inventory') != current or bool(lifecycle.get('retry'))


def health_settled(answer):
    """True once health-ack reports a non-pending state for this boot."""
    if not answer or not answer.get('ok'):
        return False
    try:
        value = json.loads(answer.get('output') or '')
    except (ValueError, TypeError):
        return False
    return isinstance(value, dict) and value.get('state') not in (None, 'PendingHealth', 'Failed')


def cadence(dark, settled):
    return (DARK_INTERVAL_S if dark else INTERVAL_S,
            DARK_MAINTENANCE_S if dark and settled else MAINTENANCE_S)


class SignalWake:
    """Wake the same select as supplicant events; retain signals until drained."""
    def __init__(self, running):
        self.read_fd, self.write_fd = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            self.previous_fd = signal.set_wakeup_fd(self.write_fd, warn_on_full_buffer=False)
        except BaseException:
            os.close(self.read_fd)
            os.close(self.write_fd)
            raise
        def stop(*_):
            running[0] = False
        self.previous_handlers = {
            sig: signal.signal(sig, stop if sig != signal.SIGUSR1 else lambda *_: None)
            for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1)
        }

    def drain(self):
        try:
            os.read(self.read_fd, 4096)
        except BlockingIOError:
            pass

    def close(self):
        signal.set_wakeup_fd(self.previous_fd)
        for sig, handler in self.previous_handlers.items():
            signal.signal(sig, handler)
        os.close(self.read_fd)
        os.close(self.write_fd)


def serve(ctx):
    runtime = private_directory(ctx.path('/run/y2'))
    fd = os.open(runtime / 'service.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    monitor = EventMonitor(ctx)
    running = [True]
    wake = usb = None
    try:
        wake = SignalWake(running)
        dns_schedule = DnsProbeSchedule()
        next_maintenance = next_ntp = 0
        associating_since = None
        from .radio_policy import Coexistence, wifi_policy
        coexistence = Coexistence()
        next_radio_policy = 0
        settled = False
        from .usb import USBService
        usb = USBService(ctx)
        previous = ctx.json('/run/y2/network.json', {})
        query_failures = previous.get('status_query_failures', 0) if previous.get('boot_id') == ctx.read('/proc/sys/kernel/random/boot_id') else 0
        query_failures = query_failures if isinstance(query_failures, int) and query_failures >= 0 else 0
        while running[0]:
            wake.drain()
            before = time.monotonic()
            dark = display_dark(ctx)
            interval, maintenance = cadence(dark, settled)
            monitor.poll()
            usb.tick()
            value = wifi(ctx)
            if value['state'] == 'Associating':
                associating_since = before if associating_since is None else associating_since
                if before - associating_since > 30:
                    value.update(state='Failed', reason='authentication_timeout')
            else:
                associating_since = None
            if dns_schedule.due(value, ctx.read('/run/y2/wifi-epoch'), before):
                probe_dns(ctx, value)
                value = wifi(ctx, signal_cache=value)
            if value.get('radio_present') and value.get('supplicant_observation', {}).get('ok') is False:
                query_failures += 1
            value.update(status_query_failures=query_failures, schema=1, boot_id=ctx.read('/proc/sys/kernel/random/boot_id'), monotonic_s=time.monotonic())
            atomic_json(runtime / 'network.json', value)
            activity = coexistence.observe(ctx, value, before)
            if before >= next_radio_policy and value['association'] == 'COMPLETED':
                next_radio_policy = before + 30
                wifi_policy(ctx, activity)
            atomic_json(runtime / 'time-status.json', time_status(ctx))
            if media_reconcile_needed(ctx):
                ctx.command(['/usr/sbin/y2-platform', 'media', 'reconcile'], timeout=7)
            if value['state'] == 'Online' and before >= next_ntp:
                next_ntp = before + 60
                ctx.command(['/etc/init.d/S43y2-time', 'start'], timeout=1)
            if before >= next_maintenance:
                next_maintenance = before + maintenance
                # Run slow fs/stat/cleanup outside this readiness process. A
                # kernel D-state does not block Wi-Fi or the power daemon.
                ctx.command(['/usr/sbin/y2-platform', 'space', '--cleanup'], timeout=2)
                settled = settled or health_settled(
                    ctx.command(['/usr/sbin/y2-platform', 'update', 'health-ack'], timeout=8))
                ready = ctx.json('/run/y2/application-ready.json', {})
                journal = ctx.json('/data/system/platform/boot.json', {})
                if (ready.get('boot_id') == ctx.read('/proc/sys/kernel/random/boot_id') and
                        ready.get('first_frame') is True and journal.get('last_stage') in ('platform_start', 'services_started')):
                    ctx.command(['/usr/sbin/y2-platform', 'boot-stage', 'application_ready'], timeout=2)
            if value['state'] in ('Scanning', 'Associating', 'AcquiringIP'):
                interval = min(interval, 1)
            monitor.wait(max(.05, interval - (time.monotonic() - before)), wake_fd=wake.read_fd)
    finally:
        try:
            if usb is not None:
                usb.stop()
        finally:
            if wake is not None:
                wake.close()
            monitor.close()
            os.close(fd)
