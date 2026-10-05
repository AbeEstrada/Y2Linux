"""USB-only owner SSH, started only after the kernel CRNG is initialized."""
# SPDX-License-Identifier: GPL-2.0-only
import fcntl
import json
import os
import select
import signal
import socket
import subprocess
import time
from .boot import private_directory
from .common import atomic_json


def entropy_ready(getrandom=os.getrandom):
    try:
        return len(getrandom(1, os.GRND_NONBLOCK)) == 1
    except (BlockingIOError, OSError):
        return False


def usb_address(ctx):
    result = ctx.command(['ip', '-j', '-4', 'addr', 'show', 'dev', 'usb0'], timeout=1)
    try:
        interfaces = json.loads(result['output'] or '')
        if not any(a.get('local') == '10.42.0.1' and a.get('prefixlen') == 24
                   for i in interfaces if i.get('ifname') == 'usb0' for a in i.get('addr_info', [])):
            return False, 'usb_address_not_ready'
        return True, None
    except (ValueError, TypeError, AttributeError):
        return False, 'usb_interface_not_ready'


def prerequisites(ctx, entropy, address=None):
    if not ctx.read('/root/.ssh/authorized_keys'):
        return 'Unavailable', 'no_owner_authorized_key'
    if not entropy:
        return 'Starting', 'kernel_crng_not_ready'
    valid, reason = usb_address(ctx) if address is None else address
    if not valid:
        return 'Starting', reason
    if ctx.read('/data/.y2data-schema') != '1':
        return 'Failed', 'data_schema_unavailable'
    return 'Ready', 'usb_address_key_and_crng_ready'


class AddressEvents:
    """Passive link/IPv4-address events; never configures the USB interface."""
    def __init__(self):
        self.sock = None
        try:
            self.sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW | socket.SOCK_NONBLOCK,
                                      socket.NETLINK_ROUTE)
            self.sock.bind((0, 1 | 0x10))  # RTMGRP_LINK | RTMGRP_IPV4_IFADDR
        except OSError:
            self.close()

    def close(self):
        if self.sock is not None:
            self.sock.close()
        self.sock = None

    def wait(self, timeout, wake_fd):
        readers = [wake_fd] + ([] if self.sock is None else [self.sock])
        ready, _, _ = select.select(readers, [], [], timeout)
        if wake_fd in ready:
            while True:
                try:
                    if not os.read(wake_fd, 4096):
                        break
                except BlockingIOError:
                    break
        changed = self.sock in ready
        if changed:
            # Drain a bounded burst. Remaining events stay readable next time.
            for _ in range(32):
                try:
                    self.sock.recv(65536)
                except BlockingIOError:
                    break
                except OSError:
                    self.close()  # refresh on the bounded fallback cadence
                    break
        return changed


def serve(ctx):
    runtime = private_directory(ctx.path('/run/y2'))
    lock = os.open(runtime/'ssh.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    running = [True]
    wake_read, wake_write = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
    previous_wake = signal.set_wakeup_fd(wake_write)
    previous_handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGCHLD)}
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: running.__setitem__(0, False))
    signal.signal(signal.SIGCHLD, lambda *_: None)
    events = AddressEvents()
    address, refresh_at, changed = None, 0, True
    child = None
    try:
        while running[0]:
            now = time.monotonic()
            if changed or events.sock is None or address is None or now >= refresh_at:
                address = usb_address(ctx)
                refresh_at = now + (60 if address[0] else 1)
            ready, reason = prerequisites(ctx, entropy_ready(), address)
            if child is None and ready == 'Ready':
                # Fixed policy, never credentials/configuration-derived shell text.
                child = subprocess.Popen(['/usr/sbin/dropbear', '-F', '-E', '-R', '-s', '-g', '-j', '-k',
                                          '-p', '10.42.0.1:22', '-l', 'usb0', '-K', '10', '-I', '600'],
                                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL, start_new_session=True)
                ready, reason = 'Starting', 'listener_starting'
            elif child is not None:
                if child.poll() is not None:
                    raise RuntimeError('ssh_listener_exited')
                # Child success is not readiness: require its bound listening address.
                listening = any('01002A0A:0016' in line and line.split()[3] == '0A'
                                for line in (ctx.read('/proc/net/tcp') or '').splitlines()[1:]
                                if len(line.split()) > 3)
                ready, reason = ('Ready', 'usb_bound_key_only_listener') if listening and ready == 'Ready' else ('Starting', reason)
            atomic_json(runtime/'ssh.json', {'schema': 1, 'boot_id': ctx.read('/proc/sys/kernel/random/boot_id'),
                        'monotonic_s': time.monotonic(), 'state': ready, 'reason': reason,
                        'bind': '10.42.0.1:22', 'interface': 'usb0', 'authentication': 'owner_public_key',
                        'sftp': ctx.path('/usr/libexec/y2-sftp-server').is_file(),
                        'pid': child.pid if child else None})
            # Keep the existing <10-second readiness freshness contract.
            # SIGTERM/child death and kernel address changes wake immediately.
            changed = events.wait(5 if ready == 'Ready' else 1, wake_read)
    finally:
        events.close()
        signal.set_wakeup_fd(previous_wake)
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)
        os.close(wake_read)
        os.close(wake_write)
        if child and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
        os.close(lock)
