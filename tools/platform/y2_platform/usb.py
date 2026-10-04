"""Consumer MTP + advanced ECM; Linux is the only block/filesystem owner.

No block-export function is selectable. The daemon pins media roots per lifetime;
mount identity changes require unbinding/stopping it before a replacement view.
"""
# SPDX-License-Identifier: GPL-2.0-only
import os
import signal
import subprocess
import time
from pathlib import Path
from .common import atomic_json, read
from .observe import mountinfo, storage

GADGET = '/sys/kernel/config/usb_gadget/y2'
FUNCTIONS = {'mtp': ('ffs.mtp', 'ecm.usb0'), 'developer': ('acm.usb0', 'ecm.usb0')}
SCHEMA = 'org.y2linux.usb-transfer/v1'


def selection(mode):
    if mode not in FUNCTIONS:
        raise ValueError('unsupported_usb_mode')
    return FUNCTIONS[mode]


def media_views(ctx):
    """Host receives user music, never Y2DATA/private/system contents or a LUN."""
    volumes = storage(ctx)['volumes']
    mounts = mountinfo(ctx.read('/proc/self/mountinfo'))
    result = []
    for volume, path, label in ((volumes[1], '/data/music', 'Internal Storage'),
                                (volumes[2], '/media/sd', 'SD Card')):
        mount = next((m for m in mounts if m['path'] == volume['path']), None)
        root = ctx.path(path)
        if path == '/data/music':
            device = ctx.path('/sys/dev/block/' + mount['device_id']) if mount else None
            if (not device or read(device / 'start') != '2104320' or
                    read(device / 'size') != '1638400' or
                    volume.get('uuid') != '79324c69-6e75-4801-8000-000000000102' or
                    not mount or mount['filesystem'] != 'ext4'):
                continue
        # Existing validated internal partition and platform SD mount claim
        # supply the identity. Never create a view of an absent underlying mount.
        release = ctx.json('/run/y2/usb-release-sd.json', {})
        if path == '/media/sd' and mount and release.get('mount_id') == mount['mount_id']:
            continue
        if (volume['state'] in ('Ready', 'Degraded') and mount and root.is_dir() and not root.is_symlink()
                and not any(m['path'].startswith(path + '/') or
                            (path == '/data/music' and m['path'] == path) for m in mounts)):
            result.append({'path': path, 'name': label, 'mount_id': mount['mount_id'],
                           'device_id': mount['device_id'], 'uuid': volume.get('uuid'),
                           'filesystem': mount['filesystem'], 'access': 'ro' if 'ro' in mount['options'] or 'ro' in mount['super_options'] else 'rw'})
    return result


def config(views):
    # Only fixed paths and labels reach the responder parser.
    allowed = {'/data/music': 'Internal Storage', '/media/sd': 'SD Card'}
    lines = ['loop_on_disconnect 1', 'manufacturer "Y2Linux"', 'product "Y2"',
             'serial "Y2LINUX-DEV-01"', 'interface "MTP"', 'firmware_version "Platform 1.0"',
             'mtp_extensions ""', 'usb_class 0x6', 'usb_subclass 0x1', 'usb_protocol 0x1', 'perceived_device_type 0x2', 'usb_functionfs_mode 1',
             'usb_dev_path "/dev/ffs-mtp/ep0"', 'usb_epin_path "/dev/ffs-mtp/ep1"',
             'usb_epout_path "/dev/ffs-mtp/ep2"', 'usb_epint_path "/dev/ffs-mtp/ep3"',
             'usb_max_packet_size 0x200', 'usb_max_rd_buffer_size 0x10000',
             'usb_max_wr_buffer_size 0x10000', 'read_buffer_cache_size 0x100000',
             'sync_when_close 1', 'no_inotify 1', 'umask 077']
    for v in views:
        if allowed.get(v['path']) != v['name'] or v['access'] not in ('ro', 'rw'):
            raise ValueError('unsafe_media_view')
        lines.append('storage "%s" "%s" "%s"' % (v['path'], v['name'], v['access']))
    return '\n'.join(lines) + '\n'


def status(ctx):
    state = ctx.json('/run/y2/usb-transfer.json', {})
    if state.get('schema') != SCHEMA or state.get('boot_id') != ctx.read('/proc/sys/kernel/random/boot_id'):
        return {'schema': SCHEMA, 'state': 'Unavailable', 'reason': 'service_not_observed',
                'filesystem_owner': 'linux', 'block_export': False}
    return state


def request_mode(ctx, mode):
    selection(mode)
    # Avoid disconnecting a host with an open session. Changes take effect after
    # unplug/replug; advanced users may choose before attaching the cable.
    atomic_json(ctx.path('/data/system/platform/usb-mode.json'), {'mode': mode}, durable=True)
    return {'state': 'Queued', 'mode': mode, 'apply': 'when_disconnected'}


def release_sd(ctx, mount_id):
    """Drop responder root pins before a device-side eject; never force umount."""
    current = status(ctx)
    if not any(v.get('path') == '/media/sd' for v in current.get('views', [])):
        return True
    if current.get('cable') != 'not attached':
        return False
    atomic_json(ctx.path('/run/y2/usb-release-sd.json'), {'mount_id': mount_id})
    pid = ctx.integer('/run/y2/readiness.pid')
    if pid and pid > 1 and ctx.root == Path('/'):
        cmdline = ctx.read('/proc/%s/cmdline' % pid) or ''
        if 'service-daemon' in cmdline and 'y2-platform' in cmdline:
            try:
                os.kill(pid, signal.SIGUSR1)
            except ProcessLookupError:
                return False
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        current = status(ctx)
        if (current.get('state') != 'Failed' and
                not any(v.get('path') == '/media/sd' for v in current.get('views', []))):
            return True
        time.sleep(.05)
    return False


class USBService:
    def __init__(self, ctx, launch=None):
        self.ctx = ctx
        self.launch = launch or self.spawn
        self.child = None
        self.mode = None
        self.views = None
        self.bound = False
        self.ready = False
        self.failures = 0
        self.started = 0
        self.previous_cable = None
        self.seen_generation = 0
        self.refresh_generation = 0
        self.last_record = None
        self.signature = None
        self.cached_views = []
        self.terminal = False

    def write(self, relative, value):
        self.ctx.path(GADGET + '/' + relative).write_text(str(value) + '\n')

    def mkdir(self, relative):
        self.ctx.path(GADGET + '/' + relative).mkdir(parents=True, exist_ok=True)

    def spawn(self):
        # RLIMIT_AS bounds the lazy handle database as well as fixed USB buffers.
        import resource
        def limits():
            resource.setrlimit(resource.RLIMIT_AS, (64*1024**2, 64*1024**2))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        return subprocess.Popen(['/usr/sbin/umtprd', '-conf', '/run/y2/umtprd.conf'],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True, preexec_fn=limits,
            env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL': 'C'})

    def stop(self):
        # Unbind first: endpoint reads return, then join/abort staged uploads.
        unbind_error = None
        if self.ctx.path(GADGET + '/UDC').exists() and (self.bound or self.ctx.read(GADGET + '/UDC')):
            try:
                self.write('UDC', '')
            except OSError as error:
                unbind_error = error
        self.bound = self.ready = False
        if self.child:
            if self.child.poll() is None:
                self.child.terminate()
                try:
                    self.child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.child.kill()
                    self.child.wait(timeout=1)
            self.child = None
        if unbind_error:
            raise unbind_error

    def setup(self, mode, views):
        selection(mode)
        self.stop()
        root = self.ctx.path(GADGET)
        if not self.ctx.path('/sys/kernel/config/usb_gadget').exists():
            answer = self.ctx.command(['mount', '-t', 'configfs', 'none', '/sys/kernel/config'])
            if not answer['ok']:
                raise OSError('configfs_mount_failed')
        self.mkdir('')
        # Keep the existing development VID/PID identity (owner-local build),
        # power request and serial. No fabricated production USB allocation.
        for name, value in {'idVendor': '0x0525', 'idProduct': '0xa4aa', 'bcdUSB': '0x0200',
                            'bcdDevice': '0x0100', 'bDeviceClass': '0',
                            'bDeviceSubClass': '0', 'bDeviceProtocol': '0'}.items():
            self.write(name, value)
        self.mkdir('configs/c.1')
        self.mkdir('os_desc')
        self.write('os_desc/use', '1' if mode == 'mtp' else '0')
        self.write('os_desc/b_vendor_code', '0x20')
        self.write('os_desc/qw_sign', 'MSFT100')
        os_link = root / 'os_desc/c.1'
        if os_link.is_symlink():
            os_link.unlink()
        if mode == 'mtp':
            os_link.symlink_to(root / 'configs/c.1')
        self.mkdir('strings/0x409')
        for name, value in {'manufacturer': 'Y2Linux', 'product': 'Y2', 'serialnumber': 'Y2LINUX-DEV-01'}.items():
            self.write('strings/0x409/' + name, value)
        self.mkdir('configs/c.1/strings/0x409')
        self.write('configs/c.1/strings/0x409/configuration', 'Music Transfer' if mode == 'mtp' else 'Developer')
        self.write('configs/c.1/MaxPower', '0')  # legacy self-powered g_cdc; charger policy owns current
        self.write('configs/c.1/bmAttributes', '0xc0')  # battery/self powered
        for link in root.joinpath('configs/c.1').iterdir():
            if link.is_symlink():
                link.unlink()
        for function in selection(mode):
            self.mkdir('functions/' + function)
            if function == 'ecm.usb0':
                self.write('functions/ecm.usb0/host_addr', '02:42:00:00:00:02')
                self.write('functions/ecm.usb0/dev_addr', '02:42:00:00:00:01')
            root.joinpath('configs/c.1', function).symlink_to(root.joinpath('functions', function))
        # FFS must be mounted and have its descriptors written BEFORE UDC bind.
        if mode == 'mtp':
            ffs = self.ctx.path('/dev/ffs-mtp')
            ffs.mkdir(parents=True, exist_ok=True)
            mounts = mountinfo(self.ctx.read('/proc/self/mountinfo'))
            if not any(m['path'] == '/dev/ffs-mtp' and m['filesystem'] == 'functionfs' for m in mounts):
                result = self.ctx.command(['mount', '-t', 'functionfs', 'mtp', '/dev/ffs-mtp'])
                if not result['ok']:
                    raise OSError('functionfs_mount_failed')
            self.ctx.path('/run/y2/umtprd.conf').write_text(config(views))
            self.child = self.launch()
        self.mode, self.views = mode, views
        self.started = time.monotonic()

    def record(self, state, reason, cable, activity=None):
        value = {'schema': SCHEMA, 'boot_id': self.ctx.read('/proc/sys/kernel/random/boot_id'),
                 'state': state, 'reason': reason, 'mode': self.mode, 'cable': cable,
                 'functions': list(selection(self.mode)) if self.mode else [],
                 'views': self.views or [], 'filesystem_owner': 'linux', 'block_export': False,
                 'refresh_generation': self.refresh_generation,
                 'active': bool((activity or {}).get('active')), 'error': (activity or {}).get('error'),
                 'restarts': self.failures}
        if value != self.last_record:
            atomic_json(self.ctx.path('/run/y2/usb-transfer.json'), value)
            self.last_record = value
        return value

    def tick(self):
        self.ctx.path('/run/y2').mkdir(parents=True, exist_ok=True)
        udcs = self.ctx.glob('/sys/class/udc/*')
        if len(udcs) != 1:
            return self.record('Unavailable', 'no_unique_udc', None)
        cable = read(udcs[0] / 'state')
        if self.terminal:
            return self.record('Failed', 'responder_restart_budget', cable)
        requested = self.ctx.json('/data/system/platform/usb-mode.json', {}).get('mode', 'mtp')
        try:
            selection(requested)
            # Reuse validated views until identity/options change. This adds no
            # recurring blkid process, storage read, or polling wakeup.
            signature = (self.ctx.read('/proc/self/mountinfo'),
                         self.ctx.read('/run/y2/media-mount.json'),
                         self.ctx.read('/run/y2/usb-release-sd.json'),
                         [(p.name, read(p / 'dev'), read(p / 'device/cid'))
                          for p in self.ctx.glob('/sys/class/block/mmcblk*')])
            if signature != self.signature:
                self.cached_views = media_views(self.ctx)
                self.signature = signature
            views = self.cached_views if requested == 'mtp' else []
            if self.mode is not None and requested != self.mode and cable != 'not attached':
                requested = self.mode
                views = self.cached_views if self.mode == 'mtp' else []
            if self.mode != requested or self.views != views:
                if self.mode is not None:
                    self.refresh_generation = time.monotonic_ns()
                self.setup(requested, views)
            if self.child and self.child.poll() is not None:
                self.stop()
                self.failures += 1
                if self.failures >= 5:
                    self.terminal = True
                    return self.record('Failed', 'responder_restart_budget', cable)
                self.mode = None
                return self.record('Starting', 'responder_restarting', cable)
            if not self.bound:
                ready = self.mode == 'developer' or (
                    self.ctx.read(GADGET + '/functions/ffs.mtp/ready') == '1' and
                    all(self.ctx.path('/dev/ffs-mtp/ep' + str(i)).exists() for i in (1, 2, 3)))
                if not ready:
                    if time.monotonic() - self.started > 15:
                        raise OSError('responder_descriptor_timeout')
                    return self.record('Starting', 'waiting_for_descriptors', cable)
                self.write('UDC', udcs[0].name)
                self.bound = self.ready = True
            activity = self.ctx.json('/run/y2/mtp-events.json', {})
            if not self.child or activity.get('pid') != self.child.pid:
                activity = {}
            generation = activity.get('generation', 0)
            if isinstance(generation, int) and generation > self.seen_generation:
                self.seen_generation = generation
                self.refresh_generation = time.monotonic_ns()
            if self.previous_cable == 'configured' and cable not in ('configured', 'suspended'):
                self.refresh_generation = time.monotonic_ns()
            self.previous_cable = cable
            state = 'Disconnected' if cable == 'not attached' else 'Ready' if cable == 'configured' else 'Starting'
            if state == 'Ready' and activity.get('active'):
                state = 'Copying'
            if state == 'Ready' and self.mode == 'mtp' and not self.views:
                state = 'Unavailable'
            return self.record(state, None, cable, activity)
        except (OSError, ValueError) as error:
            try:
                self.stop()
            except OSError:
                self.terminal = True
            self.failures += 1
            self.terminal = self.terminal or self.failures >= 5
            if self.failures < 5:
                self.mode = None
            return self.record('Failed', str(error), cable)
