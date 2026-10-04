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
from y2_platform.diagnostics import project


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


class DiagnosticContracts(unittest.TestCase):
    def test_shared_public_observations_survive_without_private_values(self):
        private = 'private-control-secret'
        raw = {
            'bluetooth': {'devices': [{'bonded': True, 'paired': False, 'trusted': True,
                                      'address': private, 'name': private}]},
            'wifi': {'state': 'Online', 'status_query_failures': 3,
                     'signal_observation': {'ok': False, 'reason': 'command_timeout', 'bssid': private}},
            'system': {'usb': {'file_transfer': {
                'schema': 'org.y2linux.usb-transfer/v1', 'state': 'Copying',
                'mode': 'mtp', 'filesystem_owner': 'linux', 'block_export': False,
                'active': True, 'refresh_generation': 23,
                'views': [{'name': 'SD Card', 'access': 'rw', 'path': private, 'cid': private}]}}},
            'sleep': {'state': 'waking', 'same_boot': True},
            'audio': {'pcm_contract': {'evidence': 'driver_contract',
                      'physical_bit_capture': False, 'hardware_max_meaningful_bits': None,
                      'supported_modes': [{'meaningful_bits': 16, 'i2s_slot_bits': 32}]}},
            'spm': 'suspend_restore_failures=0 private=secret',
        }
        result = project(raw)
        self.assertTrue(result['bluetooth']['devices'][0]['bonded'])
        self.assertEqual(result['wifi']['signal_observation']['reason'], 'command_timeout')
        usb = result['system']['usb']['file_transfer']
        self.assertEqual(usb['schema'], 'org.y2linux.usb-transfer/v1')
        self.assertEqual(usb['refresh_generation'], 23)
        self.assertTrue(usb['active'])
        self.assertEqual(usb['views'][0]['name'], 'SD Card')
        self.assertEqual(result['sleep']['state'], 'waking')
        self.assertFalse(result['audio']['pcm_contract']['physical_bit_capture'])
        self.assertEqual(result['spm']['suspend_restore_failures'], '0')
        import json
        self.assertNotIn(private, json.dumps(result))

    def test_bond_records_and_unknown_strings_remain_private(self):
        for value in ('private-secret', {'link_key': 'private-secret'}, [True], 1):
            self.assertEqual(project({'bonded': value})['bonded'], '[redacted]')
        for value in (False, True):
            self.assertIs(project({'bonded': value})['bonded'], value)
        self.assertEqual(project({'file_transfer': {'mode': 'private-secret'}})
                         ['file_transfer']['mode'], '[redacted]')
