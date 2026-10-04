"""Cross-owner contracts that did not exist in any individual source tree."""
import os
from pathlib import Path
import signal
import socket
import sys
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/platform'))
from y2_platform.network import EventMonitor
from y2_platform.service import SignalWake


class ReadinessWake(unittest.TestCase):
    def test_control_without_supplicant_and_stop_share_one_wait(self):
        running = [True]
        old_handlers = {s: signal.getsignal(s) for s in (signal.SIGUSR1, signal.SIGTERM, signal.SIGINT)}
        monitor = EventMonitor(None)
        wake = SignalWake(running)
        try:
            os.kill(os.getpid(), signal.SIGUSR1)
            start = time.monotonic()
            monitor.wait(2, wake_fd=wake.read_fd)
            self.assertLess(time.monotonic() - start, 1)
            self.assertTrue(running[0])
            wake.drain()
            start = time.monotonic()
            monitor.wait(.03, wake_fd=wake.read_fd)
            self.assertGreaterEqual(time.monotonic() - start, .025)
            timer = threading.Timer(.02, lambda: os.kill(os.getpid(), signal.SIGTERM))
            timer.start()
            monitor.wait(2, wake_fd=wake.read_fd)
            timer.join()
            self.assertFalse(running[0])
        finally:
            wake.close()
        self.assertEqual(old_handlers, {s: signal.getsignal(s) for s in old_handlers})

    def test_supplicant_and_control_each_wake_without_losing_packets(self):
        monitor = EventMonitor(None)
        monitor.sock, sender = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
        wake = SignalWake([True])
        try:
            timer = threading.Timer(.02, lambda: sender.send(b'link'))
            timer.start()
            start = time.monotonic()
            monitor.wait(2, wake_fd=wake.read_fd)
            timer.join()
            self.assertLess(time.monotonic() - start, 1)
            self.assertEqual(monitor.sock.recv(16, socket.MSG_DONTWAIT), b'link')
            # The second wake must work when the supplicant socket is idle.
            os.kill(os.getpid(), signal.SIGUSR1)
            start = time.monotonic()
            monitor.wait(2, wake_fd=wake.read_fd)
            self.assertLess(time.monotonic() - start, 1)
        finally:
            wake.close()
            monitor.close()
            sender.close()
