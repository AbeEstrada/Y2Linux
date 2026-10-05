"""Monitor boot-started radio helpers without shell polling or reconnect ownership."""
# SPDX-License-Identifier: GPL-2.0-only
import fcntl
import os
import select
import time
from .boot import private_directory
from .radio_policy import codec_runtime
from .service import SignalWake
from .ssh import AddressEvents

HELPERS = {'calibration': '/usr/sbin/y2-calibration', 'wpa': '/usr/sbin/wpa_supplicant',
           'bluealsa': '/usr/bin/bluealsad', 'reconnect': '/usr/sbin/y2-bt-reconnect'}
HEALTH_S = 30


def alive(ctx, name, binary):
    pid = ctx.integer('/run/y2/' + name + '.pid')
    if pid is None or pid <= 1:
        return None
    try:
        if os.readlink(ctx.path(f'/proc/{pid}/exe')) != os.path.realpath(ctx.path(binary)):
            return None
        os.kill(pid, 0)
        return pid
    except OSError:
        return None


class Supervisor:
    def __init__(self, ctx):
        self.ctx = ctx
        self.attached = False
        self.next_health = self.retry_at = 0
        self.retry_delay = 2
        self.next_restart = {}
        self.pids = {}

    def stop(self, name):
        # Preserve the existing hook cleanup; these pid files are private and
        # produced only by the boot-started helper/its fixed wpa action hook.
        self.ctx.command(['start-stop-daemon', '-K', '-p', '/run/y2/' + name + '.pid'], timeout=2)

    def restart(self, name):
        ctx = self.ctx
        if name == 'wpa':
            ctx.command(['/usr/libexec/y2/wpa-event', 'wlan0', 'DISCONNECTED'], timeout=3)
            ctx.command(['/usr/sbin/y2-platform', 'wifi-event', 'SERVICE_RESTART'], timeout=3)
            self.stop('wifi-action')
            self.attached = False
            return ctx.command(['wpa_supplicant', '-B', '-u', '-g', '/run/wpa_supplicant/global',
                                '-P', '/run/y2/wpa.pid'], timeout=3)
        if name == 'bluealsa':
            try:
                args = codec_runtime(ctx, record=True)
            except (ValueError, OSError):
                return {'ok': False, 'reason': 'codec_policy_unavailable'}
            binary = '/usr/bin/bluealsad'
            extra = ['-p', 'a2dp-source', '--loglevel=warning', *args]
        else:
            binary, extra = HELPERS[name], []
        if name == 'calibration':
            ctx.path('/run/y2/calibration-ready').unlink(missing_ok=True)
        return ctx.command(['start-stop-daemon', '-S', '-b', '-m', '-p',
                            '/run/y2/' + name + '.pid', '-x', binary, '--', *extra], timeout=3)

    def health(self, now, force=False):
        if not force and now < self.next_health:
            return
        self.next_health = now + HEALTH_S
        self.pids = {}
        for name, binary in HELPERS.items():
            pid = alive(self.ctx, name, binary)
            if pid is None and now >= self.next_restart.get(name, 0):
                self.next_restart[name] = now + HEALTH_S
                self.ctx.path('/run/y2/' + name + '.pid').unlink(missing_ok=True)
                self.restart(name)
                pid = alive(self.ctx, name, binary)
            if pid is not None:
                self.pids[name] = pid

    def interface(self, now):
        ctx = self.ctx
        present = ctx.path('/sys/class/net/wlan0').is_dir()
        if not present:
            if self.attached:
                ctx.command(['/usr/libexec/y2/wpa-event', 'wlan0', 'DISCONNECTED'], timeout=3)
                self.stop('wifi-action')
                ctx.command(['wpa_cli', '-g', '/run/wpa_supplicant/global',
                             'interface_remove', 'wlan0'], timeout=2)
            self.attached = False
            self.retry_at, self.retry_delay = 0, 2
            return
        if self.attached or now < self.retry_at:
            return
        added = ctx.command(['wpa_cli', '-g', '/run/wpa_supplicant/global', 'interface_add',
                             'wlan0', '/data/network/wpa_supplicant.conf', 'nl80211',
                             '/run/wpa_supplicant'], timeout=3)
        exists = added.get('ok') and (added.get('output') or '').splitlines()[-1:] == ['OK']
        if not exists:
            # A monitor restart must reuse the existing supplicant interface.
            listed = ctx.command(['wpa_cli', '-g', '/run/wpa_supplicant/global', 'interface_list'], timeout=2)
            exists = listed.get('ok') and 'wlan0' in (listed.get('output') or '').splitlines()
        if exists:
            action = ctx.command(['wpa_cli', '-i', 'wlan0', '-a', '/usr/libexec/y2/wpa-event',
                                  '-B', '-P', '/run/y2/wifi-action.pid'], timeout=3)
            self.attached = action.get('ok') is True
        self.retry_at = now + self.retry_delay
        self.retry_delay = min(60, self.retry_delay * 2)

    def cleanup(self):
        for name in ('wifi-action', 'wifi-dhcp', 'wpa', 'reconnect', 'bluealsa', 'calibration'):
            self.stop(name)


def serve(ctx):
    runtime = private_directory(ctx.path('/run/y2'))
    lock = os.open(runtime/'connectivity-monitor.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    running = [True]
    wake = events = None
    pidfds = {}
    supervisor = Supervisor(ctx)
    changed = dead = True
    try:
        wake, events = SignalWake(running), AddressEvents()
        while running[0]:
            wake.drain()
            now = time.monotonic()
            supervisor.health(now, force=dead)
            if changed or not supervisor.attached or events.sock is None:
                supervisor.interface(now)
            # pidfds make helper death an event. Older hosts retain the existing
            # 30 s health cadence; healthy checks use native reads, no children.
            for name, (pid, fd) in list(pidfds.items()):
                if supervisor.pids.get(name) != pid:
                    os.close(fd)
                    del pidfds[name]
            for name, pid in supervisor.pids.items():
                if name not in pidfds and hasattr(os, 'pidfd_open'):
                    try:
                        pidfds[name] = (pid, os.pidfd_open(pid))
                    except OSError:
                        pass
            timeout = max(0, supervisor.next_health - time.monotonic())
            if not supervisor.attached and ctx.path('/sys/class/net/wlan0').is_dir():
                timeout = min(timeout, max(.05, supervisor.retry_at - time.monotonic()))
            readers = [wake.read_fd] + [fd for _, fd in pidfds.values()]
            if events.sock is not None:
                readers.append(events.sock)
            ready, _, _ = select.select(readers, [], [], timeout)
            changed = events.wait(0, wake.read_fd)
            dead = any(fd in ready for _, fd in pidfds.values())
            if dead:
                # A failed restart must not leave an exited pidfd spinning.
                for name, (_, fd) in list(pidfds.items()):
                    if fd in ready:
                        os.close(fd)
                        del pidfds[name]
                        supervisor.pids.pop(name, None)
    finally:
        for _, fd in pidfds.values():
            os.close(fd)
        if events is not None:
            events.close()
        if wake is not None:
            wake.close()
        supervisor.cleanup()
        os.close(lock)
