"""Single explicit SD lifecycle, guarded by controller and filesystem identity."""
# SPDX-License-Identifier: GPL-2.0-only
import fcntl
import json
import os
import hashlib
import struct
import time
from .common import atomic_json, read
from .observe import mountinfo, device_instance


def media_identity(entry, filesystem, uuid):
    """CID/partition geometry supplies identity when a legal FAT UUID is absent."""
    device = entry.resolve()
    partition = read(entry / 'partition')
    if partition is not None:
        device = device.parent
    cid = read(device / 'device/cid')
    geometry = {'partition': partition, 'start': read(entry / 'start') if partition is not None else '0',
                'size': read(entry / 'size')}
    if not uuid and (not cid or any(geometry[k] is None or not geometry[k].isdigit()
                                  for k in ('start', 'size'))):
        return None
    identity = dict(cid=cid, geometry=geometry, filesystem=filesystem, uuid=uuid)
    identity['id'] = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return identity


def candidates(ctx):
    result = []
    for entry in ctx.glob('/sys/class/block/*'):
        if '/11240000.mmc/' not in str(entry.resolve()):
            continue
        if not (entry / 'partition').is_file() and list(entry.glob('*/partition')):
            continue
        answer = ctx.command(['blkid', '-p', '-o', 'export', '/dev/' + entry.name])
        if not answer['ok']:
            continue
        props = dict(line.split('=', 1) for line in answer['output'].splitlines() if '=' in line)
        if props.get('TYPE') not in ('ext4', 'vfat', 'exfat'):
            continue
        identity = media_identity(entry, props['TYPE'], props.get('UUID'))
        instance = device_instance(ctx, read(entry / 'dev') or '')
        if identity is None or instance is None:
            continue
        result.append({'device': '/dev/' + entry.name, 'filesystem': props['TYPE'],
                       'uuid': props.get('UUID'), 'cid': identity['cid'], 'identity': identity,
                       'source_instance': instance})
    return result


def mounts(ctx):
    return [m for m in mountinfo(ctx.read('/proc/self/mountinfo')) if m['path'] == '/media/sd']


def owned_mount(ctx, mounted):
    device = ctx.path('/sys/dev/block/' + mounted['device_id'])
    if device.exists():
        return '/11240000.mmc/' in str(device.resolve())
    claim = ctx.json('/run/y2/media-mount.json', {})
    # Removed cards no longer have a sysfs controller path. The retained claim
    # permits only the exact mount we created, never an arbitrary mountpoint.
    return (claim.get('boot_id') == ctx.read('/proc/sys/kernel/random/boot_id') and
            claim.get('mount_id') == mounted['mount_id'] and
            claim.get('device_id') == mounted['device_id'] and
            claim.get('device') == mounted['source'])


def inventory(ctx):
    """SD presence by stable kernel identity, never by kernfs inode/ctime.

    Page-cache drops and ordinary memory pressure reclaim kernfs inodes, so a
    recreated inode is not a new card. dev_t and the disk sequence number stay
    fixed for one gendisk; every re-enumeration allocates a new diskseq, which
    also distinguishes a reinserted identical card (same CID)."""
    result = []
    for entry in ctx.glob('/sys/class/block/mmcblk*'):
        try:
            device = entry.resolve()
            if '/11240000.mmc/' in str(device):
                disk = device.parent if read(entry / 'partition') is not None else device
                result.append((entry.name, read(entry / 'dev'), read(disk / 'diskseq'),
                               read(disk / 'device/cid')))
        except OSError:
            pass
    return result


def reconcile(ctx):
    """Insertion/removal work; no automatic retry storm or remount after eject."""
    runtime = ctx.path('/run/y2')
    runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    current = [list(v) for v in inventory(ctx)]
    previous = ctx.json('/run/y2/media-lifecycle.json', {})
    if previous.get('inventory') == current and not previous.get('retry'):
        return previous
    attempts = previous.get('attempts', 0) if previous.get('inventory') == current else 0
    attempts = attempts if isinstance(attempts, int) else 0
    result = {'schema': 1, 'inventory': current, 'attempts': attempts + 1, 'retry': False}
    if mounts(ctx):
        result.update(operation(ctx, 'unmount'))
        if mounts(ctx):
            result.update(retry=attempts < 4, reason='source_change_unmount_failed')
            atomic_json(runtime / 'media-lifecycle.json', result)
            return result
    if current:
        result.update(operation(ctx, 'mount'))
    else:
        result.update(state='Unavailable', reason='no_card')
    atomic_json(runtime / 'media-lifecycle.json', result)
    return result


def operation(ctx, action):
    if action not in ('mount', 'unmount', 'check', 'status'):
        raise ValueError('unknown_media_action')
    if action == 'status':
        from .observe import storage
        return storage(ctx)['volumes'][2]
    runtime = ctx.path('/run/y2')
    runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = os.open(runtime / 'media.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = {'schema': 1, 'action': action, 'state': 'Starting', 'reason': None,
                 'boot_id': ctx.read('/proc/sys/kernel/random/boot_id')}
        old = mounts(ctx)
        if old and any(not owned_mount(ctx, m) for m in old):
            state.update(state='Failed', reason='mounted_source_not_sd')
            atomic_json(runtime / 'media.json', state)
            return state
        if action == 'unmount':
            if len(old) > 1:
                state.update(state='Failed', reason='ambiguous_mount_stack')
            elif old:
                from .usb import release_sd
                if not release_sd(ctx, old[0]['mount_id']):
                    state.update(state='Failed', reason='usb_transfer_connected_or_busy')
                    atomic_json(runtime / 'media.json', state)
                    return state
                result = ctx.command(['umount', '/media/sd'], timeout=3)
                if not result['ok'] or mounts(ctx):
                    state.update(state='Failed', reason=result['reason'] or 'unmount_busy')
                else:
                    state.update(state='Unavailable', reason='ejected')
            else:
                state.update(state='Unavailable', reason='not_mounted')
        elif old:
            # Never check/repair an active filesystem or stack a new card on it.
            state.update(state='Failed', reason='already_mounted' if action == 'check' else 'mount_requires_unmounted_path')
        else:
            available = candidates(ctx)
            if len(available) != 1:
                state.update(state='Unavailable', reason='no_unique_supported_filesystem')
            else:
                card = available[0]
                state.update(card)
                if action == 'check':
                    argv = {'ext4': ['e2fsck', '-f', '-n'], 'vfat': ['fsck.fat', '-n'],
                            'exfat': ['fsck.exfat', '-n']}[card['filesystem']]
                    result = ctx.command(argv + [card['device']], timeout=60)
                    state.update(state='Ready' if result['ok'] else 'Degraded',
                                 reason='read_only_check_passed' if result['ok'] else result['reason'])
                else:
                    # Read-only admission never authorizes checker repairs.
                    # Large/unhealthy media may time out;
                    # the owner must see that failure rather than a RW mount.
                    argv = {'ext4': ['e2fsck', '-n'], 'vfat': ['fsck.fat', '-n'],
                            'exfat': ['fsck.exfat', '-n']}[card['filesystem']]
                    result = ctx.command(argv + [card['device']], timeout=60)
                    state['filesystem_check'] = result
                    if not result['ok']:
                        state.update(state='Degraded', reason='filesystem_check_failed')
                        atomic_json(runtime / 'media.json', state)
                        return state
                    if candidates(ctx) != available:
                        state.update(state='Failed', reason='source_changed_during_check')
                        atomic_json(runtime / 'media.json', state)
                        return state
                    target = ctx.path('/media/sd')
                    if target.is_symlink():
                        raise ValueError('mountpoint_symlink')
                    target.mkdir(parents=True, exist_ok=True)
                    options = 'rw,nosuid,nodev,noexec'
                    if card['filesystem'] in ('vfat', 'exfat'):
                        options += ',fmask=0177,dmask=0077'
                    if card['filesystem'] == 'vfat':
                        options += ',utf8=1'
                    result = ctx.command(['mount', '-t', card['filesystem'], '-o', options,
                                          card['device'], '/media/sd'], timeout=3)
                    current = mounts(ctx)
                    if result['ok'] and len(current) == 1 and current[0]['source'] == card['device']:
                        state.update(state='Ready', mount_id=current[0]['mount_id'],
                                     device_id=current[0]['device_id'],
                                     source_instance=device_instance(ctx, current[0]['device_id']))
                        if candidates(ctx) != available:
                            state.update(state='Failed', reason='source_changed_during_mount')
                        else:
                            atomic_json(runtime / 'media-mount.json', state)
                            # The kernel recycles mount ids, so a release marker for a card that was
                            # ejected or reformatted must not hide the next mount that reuses its id.
                            try:
                                ctx.path('/run/y2/usb-release-sd.json').unlink()
                            except FileNotFoundError:
                                pass
                    else:
                        state.update(state='Failed', reason=result['reason'] or 'mount_identity_failed')
        atomic_json(runtime / 'media.json', state)
        return state
    finally:
        os.close(lock)


# ---------------------------------------------------------------------------
# Explicit owner operations on the removable card: format and grow.
# Never automatic: a card with a foreign or undersized filesystem is reported,
# and only a command that names the card by CID may change it.

MIN_CARD_SECTORS = 16384          # 8 MiB; anything smaller is not a storage card
PARTITION_START = 2048            # 1 MiB alignment
WIPE_TAIL_SECTORS = 64            # a stale GPT backup header lives in the last sectors
BLKRRPART = 0x125F


def sd_disk(ctx):
    """The unique whole-disk entry on the removable-card controller, else None."""
    found = []
    for entry in ctx.glob('/sys/class/block/mmcblk*'):
        try:
            real = str(entry.resolve())
        except OSError:
            continue
        if '/11240000.mmc/' in real and read(entry / 'partition') is None:
            found.append(entry)
    return found[0] if len(found) == 1 else None


def mbr_for(sectors):
    """One Linux partition from sector 2048 to the end of the card."""
    size = min(sectors - PARTITION_START, 0xFFFFFFFF)
    entry = struct.pack('<B3sB3sII', 0, b'\xfe\xff\xff', 0x83, b'\xfe\xff\xff', PARTITION_START, size)
    return bytes(446) + entry + bytes(48) + b'\x55\xaa'


def reread_partitions(ctx, fd):
    return getattr(ctx, 'ioctl', fcntl.ioctl)(fd, BLKRRPART)


def detach_for_change(ctx, state):
    """Release the card from MTP and unmount it, for an explicit owner command."""
    old = mounts(ctx)
    if not old:
        return True
    if len(old) > 1 or any(not owned_mount(ctx, m) for m in old):
        state.update(state='Failed', reason='ambiguous_or_foreign_mount')
        return False
    from .usb import release_sd
    if not release_sd(ctx, old[0]['mount_id'], explicit=True):
        state.update(state='Failed', reason='usb_release_failed')
        return False
    result = ctx.command(['umount', '/media/sd'], timeout=10)
    if not result['ok'] or mounts(ctx):
        state.update(state='Failed', reason=result['reason'] or 'unmount_busy')
        return False
    return True


def change_card(ctx, action, confirm_cid=None):
    """action: 'format' (new table + ext4 over the whole card) or 'grow' (ext4 to the partition)."""
    if action not in ('format', 'grow'):
        raise ValueError('unknown_media_change')
    state = apply_change(ctx, action, confirm_cid)
    if state['state'] == 'Starting':
        # Mount through the normal admission path, after the change released the media lock.
        state.update(operation(ctx, 'mount'))
        state['action'] = action
    return state


def apply_change(ctx, action, confirm_cid):
    runtime = ctx.path('/run/y2')
    runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = os.open(runtime / 'media.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = {'schema': 1, 'action': action, 'state': 'Starting', 'reason': None,
                 'boot_id': ctx.read('/proc/sys/kernel/random/boot_id')}
        disk = sd_disk(ctx)
        cid = read(disk / 'device/cid') if disk else None
        sectors = read(disk / 'size') if disk else None
        if disk is None or not cid or not sectors or not sectors.isdigit():
            state.update(state='Unavailable', reason='no_unique_card')
        elif action == 'format' and confirm_cid != cid:
            # The owner must name the card: a wrong or swapped card is never formatted.
            state.update(state='Failed', reason='cid_confirmation_mismatch', cid=cid)
        elif int(sectors) < MIN_CARD_SECTORS:
            state.update(state='Failed', reason='card_too_small')
        else:
            device = '/dev/' + disk.name
            state.update(cid=cid, sectors=int(sectors), device=device)
            if detach_for_change(ctx, state):
                if action == 'format':
                    format_steps(ctx, state, device, int(sectors))
                else:
                    grow_steps(ctx, state)
        if state['state'] != 'Starting':
            atomic_json(runtime / 'media.json', state)
        return state
    finally:
        os.close(lock)


def format_steps(ctx, state, device, sectors):
    try:
        fd = os.open(ctx.path(device), os.O_RDWR | os.O_SYNC)
    except OSError:
        state.update(state='Failed', reason='card_not_writable')
        return
    try:
        # The old table, boot sector and a stale GPT backup must not survive.
        zero = bytes(512)
        for sector in list(range(1, PARTITION_START)) + list(range(sectors - WIPE_TAIL_SECTORS, sectors)):
            os.pwrite(fd, zero, sector * 512)
        os.pwrite(fd, mbr_for(sectors), 0)
        os.fsync(fd)
        try:
            reread_partitions(ctx, fd)
        except OSError as error:
            state.update(state='Failed', reason='partition_reread_failed', errno=error.errno)
            return
    except OSError as error:
        state.update(state='Failed', reason='card_write_failed', errno=error.errno)
        return
    finally:
        os.close(fd)
    argv = ['mkfs.ext4', '-F', '-q', '-L', 'Y2SD', '-m', '0', '-E', 'lazy_itable_init=1,lazy_journal_init=1']
    if sectors >= 32 * 1024 * 1024:           # 16 GiB and up: a 128 MiB journal is plenty
        argv += ['-J', 'size=128']
    partition = device + 'p1'
    deadline = time.monotonic() + 5
    while not ctx.path(partition).exists() and time.monotonic() < deadline:
        time.sleep(0.05)          # devtmpfs creates the node as the kernel re-reads the table
    result = ctx.command(argv + [partition], timeout=180)
    if not result['ok']:
        state.update(state='Failed', reason='mkfs_failed:' + str(result['reason']))


def grow_steps(ctx, state):
    available = candidates(ctx)
    if len(available) != 1 or available[0]['filesystem'] != 'ext4':
        state.update(state='Failed', reason='grow_requires_one_ext4_card')
        return
    device = available[0]['device']
    # Only a clean (or safely auto-corrected) filesystem is resized.
    if not ctx.command(['e2fsck', '-f', '-p', device], timeout=300)['ok']:
        state.update(state='Failed', reason='filesystem_check_failed')
        return
    result = ctx.command(['resize2fs', device], timeout=300)
    if not result['ok']:
        state.update(state='Failed', reason='resize_failed:' + str(result['reason']))
