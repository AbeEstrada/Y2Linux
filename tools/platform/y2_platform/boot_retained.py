"""Once-per-boot private archive of retained PM/pstore bytes, without clearing them."""
# SPDX-License-Identifier: GPL-2.0-only
import hashlib
import io
import json
import os
import re
import stat
import tarfile
import time
from .boot import private_directory

MAX_BYTES = 2 * 1024 * 1024
KEEP = 8
PM_FILES = ('previous', 'devices_previous', 'state', 'devices', 'reset_status', 'backstop_s')


def capture(ctx, boot_id, previous_boot_id):
    if not re.fullmatch(r'[A-Za-z0-9-]{1,64}', boot_id):
        raise ValueError('invalid_boot_archive_identity')
    directory = private_directory(ctx.path('/data/system/platform/retained'))
    name = 'boot-' + boot_id + '.tar'
    destination = directory / name
    temporary = directory / ('.' + name + '.' + str(os.getpid()) + '.tmp')
    result = {'archive': str(destination.relative_to(ctx.root)), 'files': [],
              'captured_on_boot_id': boot_id, 'previous_boot_id': previous_boot_id,
              'pstore_mounted': False, 'errors': [], 'source_entries_deleted': False}
    from .observe import mountinfo
    result['pstore_mounted'] = any(m['path'] == '/sys/fs/pstore' and m['filesystem'] == 'pstore'
                                 for m in mountinfo(ctx.read('/proc/self/mountinfo')))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    used = 0
    try:
        with os.fdopen(fd, 'wb') as output, tarfile.open(fileobj=output, mode='w') as archive:
            def add(path, entry, limit):
                nonlocal used
                source = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
                with os.fdopen(source, 'rb') as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                        raise ValueError('retained_source_not_regular')
                    raw = stream.read(min(limit, MAX_BYTES - used) + 1)
                if len(raw) > min(limit, MAX_BYTES - used):
                    raise ValueError('retained_source_exceeds_archive_bound')
                info = tarfile.TarInfo(entry)
                info.size, info.mode = len(raw), 0o600
                archive.addfile(info, io.BytesIO(raw))
                used += len(raw)
                result['files'].append({'name': entry, 'bytes': len(raw),
                                        'sha256': hashlib.sha256(raw).hexdigest()})

            sources = [(ctx.path('/sys/firmware/y2_pm/' + part), 'pm/' + part, 65536)
                       for part in PM_FILES]
            if result['pstore_mounted']:
                pstore = ctx.path('/sys/fs/pstore')
                # Refuse traversal even if the mount table was stale or forged.
                pstore_fd = os.open(pstore, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
                try:
                    names = sorted(os.listdir(pstore_fd))
                    if len(names) > 32:
                        result['errors'].append({'source': 'pstore', 'error': 'entry_count_exceeds_32'})
                    sources += [(pstore / part, 'pstore/' + part, MAX_BYTES) for part in names[:32]]
                finally:
                    os.close(pstore_fd)
            for path, entry, limit in sources:
                try:
                    add(path, entry, limit)
                except FileNotFoundError:
                    if entry.startswith('pstore/'):
                        result['errors'].append({'source': entry, 'error': 'disappeared_during_capture'})
                except (OSError, ValueError) as error:
                    result['errors'].append({'source': entry, 'error': str(error)})
            raw = json.dumps(result, sort_keys=True).encode()
            info = tarfile.TarInfo('manifest.json')
            info.size, info.mode = len(raw), 0o600
            archive.addfile(info, io.BytesIO(raw))
            archive.close()
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
        # Only archives owned by this helper rotate. Kernel pstore is never
        # removed; raw bytes remain available to the owner after boot capture.
        archives = sorted((p for p in directory.glob('boot-*.tar')
                           if stat.S_ISREG(p.lstat().st_mode)), key=lambda p: p.stat().st_mtime_ns)
        for old in archives[:-KEEP]:
            if old != destination:
                old.unlink()
        parent = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    result['captured_monotonic_s'] = time.monotonic()
    return result
