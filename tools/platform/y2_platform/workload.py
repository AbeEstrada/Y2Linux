"""Scoped semantic QoS for platform workers; the kernel owns frequency policy."""
# SPDX-License-Identifier: GPL-2.0-only
import functools
import fcntl
import os
import threading


def workload(class_name):
    if class_name not in ('NetworkTransfer', 'Maintenance'):
        raise ValueError('unsupported_platform_workload')
    def decorate(function):
        @functools.wraps(function)
        def wrapped(ctx, *args, **kwargs):
            # Unlike optional frequency hints this is a mandatory operation
            # exclusion. flock dies with the process; a leftover file is inert.
            from .boot import private_directory
            root = private_directory(ctx.path('/run/y2'))
            lease = os.open(root / 'activity.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
            fd = None
            stopped = threading.Event()
            worker = None
            payload = (class_name + ' 3000\n').encode('ascii')
            try:
                try:
                    fcntl.flock(lease, fcntl.LOCK_SH | fcntl.LOCK_NB)
                except BlockingIOError as error:
                    raise ValueError('sleep_operation_in_progress') from error
                try:
                    fd = os.open(ctx.path('/dev/y2-workload'), os.O_WRONLY | os.O_CLOEXEC)
                    def renew():
                        while not stopped.is_set():
                            try:
                                if os.write(fd, payload) != len(payload):
                                    return
                            except OSError:
                                return
                            if stopped.wait(1):
                                return
                    # Acquire before work starts; renew on an independent worker
                    # even when a blocking transfer subprocess runs for minutes.
                    if os.write(fd, payload) == len(payload):
                        worker = threading.Thread(target=renew, daemon=True)
                        worker.start()
                except OSError:
                    pass  # QoS is optional; never fail a transfer on a hint.
                return function(ctx, *args, **kwargs)
            finally:
                stopped.set()
                if worker is not None:
                    worker.join()
                if fd is not None:
                    os.close(fd)  # close/process death releases only this lease
                os.close(lease)
        return wrapped
    return decorate
