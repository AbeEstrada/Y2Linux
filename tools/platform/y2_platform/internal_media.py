"""Internal user media: the eMMC partition that the stock firmware used as its storage (p8).

Y2Media is ext4, label Y2MEDIA, fixed UUID, at stock logical sector 3742720 for 11460608
sectors, on the internal controller. It is mounted at /media/internal and carries only the music
library (Reborn) and what the owner copies over MTP/SFTP. System state stays on Y2DATA (/data).

Mounting only ever accepts that exact identity. Creating the filesystem is a separate, explicit,
one-time provisioning that names the stock filesystem it replaces and first moves the old
/data/music library across with checksums. Nothing here runs automatically except `mount`.
"""
# SPDX-License-Identifier: GPL-2.0-only
import fcntl
import hashlib
import os
import stat
from .common import atomic_json, read
from .observe import device_instance, mountinfo

PATH = '/media/internal'
MUSIC = PATH + '/music'
LEGACY_MUSIC = '/data/music'
LABEL = 'Y2MEDIA'
UUID = '79324c69-6e75-4801-8000-000000000103'
START = '3742720'
SIZE = '11460608'
CONTROLLER = '/11230000.mmc/'
MARKER = '/run/y2/internal-media.json'
OPTIONS = 'rw,nosuid,nodev,noexec,noatime'  # 30: no access-time writes during playback
CHUNK = 1 << 20
RESERVE = 64 << 20         # keep this much free after a migration


def partition(ctx):
    """The one internal partition with the Y2Media geometry, else None."""
    found = []
    for entry in ctx.glob('/sys/class/block/mmcblk*p*'):
        try:
            real = str(entry.resolve())
        except OSError:
            continue
        if (CONTROLLER in real and read(entry / 'partition') is not None and
                read(entry / 'start') == START and read(entry / 'size') == SIZE):
            found.append(entry)
    return found[0] if len(found) == 1 else None


def probe(ctx, entry):
    answer = ctx.command(['blkid', '-p', '-o', 'export', '/dev/' + entry.name])
    if not answer['ok']:
        return {}
    return dict(line.split('=', 1) for line in (answer['output'] or '').splitlines() if '=' in line)


def valid(props):
    return props.get('TYPE') == 'ext4' and props.get('LABEL') == LABEL and props.get('UUID') == UUID


def mounts(ctx):
    return [m for m in mountinfo(ctx.read('/proc/self/mountinfo')) if m['path'] == PATH]


def record(ctx, state, reason=None, **fields):
    value = {'schema': 1, 'state': state, 'reason': reason, 'path': PATH,
             'boot_id': ctx.read('/proc/sys/kernel/random/boot_id'), **fields}
    ctx.path('/run/y2').mkdir(mode=0o700, parents=True, exist_ok=True)
    atomic_json(ctx.path(MARKER), value)
    return value


def lock_runtime(ctx):
    runtime = ctx.path('/run/y2')
    runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = os.open(runtime / 'internal-media.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(lock)
        raise
    return lock


def ready(ctx):
    """True only while the recorded mount is still the live, exact Y2Media mount."""
    claim = ctx.json(MARKER, {})
    current = mounts(ctx)
    return (claim.get('state') == 'Ready' and len(current) == 1 and
            claim.get('boot_id') == ctx.read('/proc/sys/kernel/random/boot_id') and
            claim.get('mount_id') == current[0]['mount_id'] and
            claim.get('device_id') == current[0]['device_id'])


def music_root(ctx):
    """Where internal music lives now: Y2Media when mounted, the legacy folder otherwise."""
    return MUSIC if ready(ctx) else LEGACY_MUSIC


def mount(ctx):
    lock = lock_runtime(ctx)
    try:
        entry = partition(ctx)
        if entry is None:
            return record(ctx, 'Unavailable', 'partition_geometry_not_found')
        props = probe(ctx, entry)
        if not valid(props):
            return record(ctx, 'Unavailable', 'filesystem_identity_not_y2media',
                          filesystem=props.get('TYPE'), label=props.get('LABEL'))
        current = mounts(ctx)
        if current:
            same = len(current) == 1 and current[0]['source'] == '/dev/' + entry.name
            return record(ctx, 'Ready' if same else 'Failed', None if same else 'foreign_mount_at_path',
                          mount_id=current[0]['mount_id'], device_id=current[0]['device_id'], uuid=UUID)
        device = '/dev/' + entry.name
        # Same policy as Y2DATA in the initramfs: only safe automatic repairs (journal replay etc).
        check = ctx.command(['e2fsck', '-p', device], timeout=180)
        if not check['ok']:
            return record(ctx, 'Degraded', 'filesystem_check_failed')
        ctx.path(PATH).mkdir(parents=True, exist_ok=True)
        result = ctx.command(['mount', '-t', 'ext4', '-o', OPTIONS, device, PATH], timeout=20)
        current = mounts(ctx)
        if not result['ok'] or len(current) != 1 or current[0]['source'] != device:
            return record(ctx, 'Failed', result['reason'] or 'mount_identity_failed')
        return record(ctx, 'Ready', mount_id=current[0]['mount_id'], device_id=current[0]['device_id'],
                      uuid=UUID, source_instance=device_instance(ctx, current[0]['device_id']))
    finally:
        os.close(lock)


def unmount(ctx):
    lock = lock_runtime(ctx)
    try:
        current = mounts(ctx)
        if not current:
            return record(ctx, 'Unavailable', 'not_mounted')
        result = ctx.command(['umount', PATH], timeout=10)
        if not result['ok'] or mounts(ctx):
            return record(ctx, 'Failed', result['reason'] or 'unmount_busy')
        return record(ctx, 'Unavailable', 'unmounted')
    finally:
        os.close(lock)


def status(ctx):
    entry = partition(ctx)
    props = probe(ctx, entry) if entry else {}
    return {'schema': 1, 'path': PATH, 'partition': entry.name if entry else None,
            'filesystem': props.get('TYPE'), 'label': props.get('LABEL'), 'uuid': props.get('UUID'),
            'identity_valid': valid(props), 'mounted': bool(mounts(ctx)), 'ready': ready(ctx),
            'marker': ctx.json(MARKER, {})}


# --- one-time provisioning ------------------------------------------------------------------

def tree(root):
    """(relative path, size) of every regular file; refuses symlinks and special files."""
    files, directories = [], []
    for current, names, entries in os.walk(root, followlinks=False):
        relative = os.path.relpath(current, root)
        for name in list(names):
            if os.path.islink(os.path.join(current, name)):
                raise ValueError('migration_refuses_symlink:' + os.path.join(relative, name))
        directories.append(relative)
        for name in entries:
            path = os.path.join(current, name)
            info = os.lstat(path)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError('migration_refuses_special_file:' + os.path.join(relative, name))
            files.append((os.path.normpath(os.path.join(relative, name)), info.st_size))
    return files, directories


def digest(path):
    h = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        try:
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)     # read the media, not the page cache
        except OSError:
            pass
        while True:
            chunk = os.read(fd, CHUNK)
            if not chunk:
                break
            h.update(chunk)
    finally:
        os.close(fd)
    return h.hexdigest()


def copy_verified(source, target, size):
    """Copy to a temporary name, fsync, verify by hash, then publish atomically."""
    if os.path.exists(target):
        if os.path.getsize(target) == size and digest(source) == digest(target):
            return 'present'
        raise ValueError('migration_target_differs:' + target)
    temporary = target + '.part'
    src = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    dst = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o644)
    try:
        while True:
            chunk = os.read(src, CHUNK)
            if not chunk:
                break
            view = memoryview(chunk)
            while view:
                view = view[os.write(dst, view):]
        os.fsync(dst)
    finally:
        os.close(src)
        os.close(dst)
    if digest(source) != digest(temporary):
        os.unlink(temporary)
        raise ValueError('migration_hash_mismatch:' + source)
    os.replace(temporary, target)
    info = os.stat(source)
    os.utime(target, ns=(info.st_atime_ns, info.st_mtime_ns))
    return 'copied'


def migrate(ctx, source=LEGACY_MUSIC, target=MUSIC):
    """Move the old music library onto Y2Media. Sources are removed only after everything verified."""
    src, dst = str(ctx.path(source)), str(ctx.path(target))
    if not os.path.isdir(src):
        return {'files': 0, 'bytes': 0, 'copied': 0, 'removed': 0}
    files, directories = tree(src)
    total = sum(size for _, size in files)
    free = os.statvfs(ctx.path(PATH))
    if total + RESERVE > free.f_bavail * free.f_frsize:
        raise ValueError('migration_does_not_fit')
    os.makedirs(dst, mode=0o755, exist_ok=True)
    for relative in directories:
        os.makedirs(os.path.join(dst, relative), mode=0o755, exist_ok=True)
    copied = 0
    for relative, size in files:
        if copy_verified(os.path.join(src, relative), os.path.join(dst, relative), size) == 'copied':
            copied += 1
    os.sync()
    # Everything on the target is verified: only now remove the originals.
    removed = 0
    for relative, _ in files:
        os.unlink(os.path.join(src, relative))
        removed += 1
    for relative in sorted(directories, key=len, reverse=True):
        if relative != '.':
            try:
                os.rmdir(os.path.join(src, relative))
            except OSError:
                pass
    return {'files': len(files), 'bytes': total, 'copied': copied, 'removed': removed}


def provision(ctx, confirm_uuid, migrate_music=True):
    """Create Y2Media over the stock FAT partition. Names the filesystem it replaces."""
    lock = lock_runtime(ctx)
    try:
        entry = partition(ctx)
        if entry is None:
            return record(ctx, 'Unavailable', 'partition_geometry_not_found')
        props = probe(ctx, entry)
        in_use = mounts(ctx) or any(m['source'] == '/dev/' + entry.name
                                    for m in mountinfo(ctx.read('/proc/self/mountinfo')))
        if in_use and not valid(props):
            # Never replace a mounted filesystem. A finished Y2Media may be re-run to resume
            # an interrupted migration.
            return record(ctx, 'Failed', 'partition_is_mounted')
        if not valid(props):
            if props.get('TYPE') != 'vfat' or not confirm_uuid or props.get('UUID') != confirm_uuid:
                # Only the stock FAT filesystem, named by its serial, may be replaced.
                return record(ctx, 'Failed', 'confirmation_does_not_match_stock_filesystem',
                              filesystem=props.get('TYPE'), serial=props.get('UUID'))
            device = '/dev/' + entry.name
            made = ctx.command(['mkfs.ext4', '-F', '-q', '-L', LABEL, '-U', UUID, '-m', '0', '-J', 'size=64',
                                '-E', 'lazy_itable_init=1,lazy_journal_init=1', device], timeout=300)
            if not made['ok']:
                return record(ctx, 'Failed', 'mkfs_failed:' + str(made['reason']))
    finally:
        os.close(lock)
    state = mount(ctx)
    if state['state'] != 'Ready':
        return state
    ctx.path(MUSIC).mkdir(mode=0o755, parents=True, exist_ok=True)
    result = dict(state)
    if migrate_music:
        try:
            result['migration'] = migrate(ctx)
        except (OSError, ValueError) as error:
            return record(ctx, 'Degraded', 'migration_failed:' + str(error),
                          mount_id=state.get('mount_id'), device_id=state.get('device_id'), uuid=UUID)
    return result
