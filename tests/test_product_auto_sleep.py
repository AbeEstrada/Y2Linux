"""Exercise real lock ownership, policy refusal and complete product PM flows."""
import fcntl
import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/platform'))
from y2_platform.common import Context
from y2_platform import product_sleep as pm
from y2_platform.sleep import request
from y2_platform.suspend_record import record
from y2_platform.workload import workload


class ProductAutoSleep(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.calls = []
        self.rpc = []
        self.ctx = Context(self.tmp.name, runner=self.command)
        for name, text in {
            '/proc/sys/kernel/random/boot_id': 'same-boot',
            '/proc/sys/kernel/osrelease': 'corrected-kernel',
            '/proc/sys/kernel/tainted': '0',
            '/etc/y2linux/versions.json': '{"build_git_commit":"corrected-source"}',
            '/sys/power/pm_test': '[none] core',
            '/sys/power/state': 'mem', '/sys/power/wakeup_count': '8',
            '/sys/firmware/y2_pm/stage': '',
            '/sys/firmware/y2_pm/backstop_s': 'provider=1 armed_s=0 running=0',
            '/sys/class/power_supply/y2-usb-presence/online': '0',
            '/sys/class/power_supply/BAT0/status': 'Discharging',
            '/sys/class/power_supply/BAT0/voltage_now': '3900000',
            '/sys/module/workload/parameters/leases': '',
            '/sys/devices/platform/18070000.connectivity/status': 'powered=0 functions=0 error=0 ',
            '/data/network/enabled': '0', '/data/bluetooth/enabled': '0',
            '/data/.y2data-schema': '1', '/run/y2/suspend.lock': '',
        }.items():
            self.write(name, text)
        self.ctx.path('/data/updates').mkdir()
        self.write('/etc/y2linux/power-policy.json', (ROOT / 'buildroot/board/y2/production-overlay/etc/y2linux/power-policy.json').read_text())
        self.write('/run/y2/power.json', json.dumps({'boot_id': 'same-boot', 'state': 'Normal',
                                                   'monotonic_ns': time.monotonic_ns()}))
        self.power, self.rtc = 2, 1
        self.irqs()
        self.spm(False, 0)
        self.write('/sys/firmware/y2_pm/state', 'valid=0 stage=EXIT error=0')
        self.fd = os.open(self.ctx.path('/run/y2/suspend.lock'), os.O_RDWR)
        self.addCleanup(os.close, self.fd)
        fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.addCleanup(patch.stopall)
        patch('y2_platform.suspend_record.application_rpc', side_effect=self.application).start()

    def write(self, name, value):
        path = self.ctx.path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)

    def command(self, argv, **kwargs):
        self.calls.append(argv)
        return {'ok': True, 'output': ''}

    def application(self, ctx, op):
        self.rpc.append(op)
        return {'sleep_ready': True, 'screen_off': op == 'sleep_prepare'}

    def irqs(self):
        self.write('/proc/interrupts', f'  66: {self.rtc} 0 mt6323 20 Level mt6397-rtc\n'
                   f'  70: {self.power} 0 mt6323 5 Level mtk-pmic-keys\n')

    def spm(self, timer, ticks):
        self.write('/sys/bus/platform/devices/10006000.power-controller/state',
                   f'system_sleep_abi=1 broken=0 timer_wake={int(timer)} ticks32k={ticks}')

    def returned(self, timer=False, rtc=False):
        if not timer:
            if rtc:
                self.rtc += 1
            else:
                self.power += 1
        self.irqs()
        self.spm(timer, (600 if timer else 25) * 32768)
        self.write('/sys/firmware/y2_pm/state', 'valid=1 stage=EXIT error=0 wake=' +
                   ('0x1' if timer else '0x20') + ' reset_resume_entry=0x59325253 pcm_length=596')

    def run_sleep(self, enter):
        record(self.ctx, 'requested', 0, mode='product')
        return pm.execute(self.ctx, self.fd, enter)

    def test_timer_maintenance_keeps_app_quiesced_then_power_fully_restores(self):
        calls = []
        def enter(ctx):
            calls.append(1)
            self.assertEqual(self.rpc, ['sleep_prepare'])
            self.returned(timer=len(calls) == 1)
        with patch('y2_platform.product_sleep.time.sleep'):
            self.assertEqual(self.run_sleep(enter), 0)
        receipt = self.ctx.json('/data/system/platform/suspend-last.json')
        self.assertEqual(receipt['cycles'], 2)
        self.assertEqual(receipt['maintenance_wakes'], 1)
        self.assertEqual(receipt['suspended_seconds'], 625)
        self.assertEqual(receipt['product']['wake_reason'], 'power')
        self.assertEqual(receipt['product']['state'], 'restored')
        self.assertEqual(self.rpc, ['sleep_prepare', 'sleep_restore'])
        self.assertFalse(self.ctx.json(pm.GUARD)['pending'])

    def test_rtc_restores_without_automatic_reentry(self):
        self.assertEqual(self.run_sleep(lambda ctx: self.returned(rtc=True)), 0)
        receipt = self.ctx.json('/data/system/platform/suspend-last.json')
        self.assertEqual(receipt['cycles'], 1)
        self.assertEqual(receipt['product']['wake_reason'], 'rtc')

    def test_kernel_busy_restores_once_without_claiming_sleep_or_retrying(self):
        calls = []
        def busy(ctx):
            calls.append(1)
            raise OSError(errno.EBUSY, 'wake event during device suspend')
        self.assertEqual(self.run_sleep(busy), 2)
        receipt = self.ctx.json('/data/system/platform/suspend-last.json')
        self.assertEqual(calls, [1])
        self.assertEqual(receipt['product']['reason'], 'kernel_suspend_refused')
        self.assertFalse(receipt['product']['kernel_completed'])
        self.assertNotIn('cycles', receipt)
        self.assertEqual(self.rpc, ['sleep_prepare', 'sleep_restore'])
        self.assertFalse(self.ctx.json(pm.GUARD)['pending'])

    def test_power_press_during_preparation_cancels_entry_and_restores(self):
        original = self.application
        def preparation(ctx, op):
            if op == 'sleep_prepare':
                self.power += 1
                self.irqs()
            return original(ctx, op)
        with patch('y2_platform.suspend_record.application_rpc', side_effect=preparation):
            self.assertEqual(self.run_sleep(lambda ctx: self.fail('lost Power gesture')), 2)
        self.assertEqual(self.rpc, ['sleep_prepare', 'sleep_restore'])
        self.assertFalse(self.ctx.json(pm.GUARD)['pending'])

    def test_playback_preparation_refusal_remains_a_named_inhibitor(self):
        with patch('y2_platform.suspend_record.application_rpc', side_effect=ValueError('playback_active')):
            self.assertEqual(self.run_sleep(lambda ctx: self.fail('entered during playback')), 2)
        value = self.ctx.json('/data/system/platform/suspend-last.json')['product']
        self.assertEqual((value['state'], value['reason']), ('refused', 'playback_active'))
        self.assertFalse(self.ctx.json(pm.GUARD)['pending'])

    def test_request_passes_lock_ownership_to_detached_helper(self):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        owned = []
        def launch(ctx, fd):
            owned.append(os.dup(fd))
        try:
            with patch('y2_platform.product_sleep.launch', side_effect=launch):
                self.assertEqual(request(self.ctx)['state'], 'requested')
            self.assertEqual(request(self.ctx)['reason'], 'sleep_operation_in_progress')
        finally:
            for fd in owned:
                os.close(fd)
        with patch('y2_platform.product_sleep.launch', side_effect=launch):
            self.assertEqual(request(self.ctx)['state'], 'requested')
        os.close(owned[-1])

    def test_power_press_during_maintenance_gap_cancels_next_entry(self):
        calls = []
        def enter(ctx):
            calls.append(1)
            self.returned(timer=True)
        def gap(seconds):
            self.power += 1
            self.irqs()
        with patch('y2_platform.product_sleep.time.sleep', side_effect=gap):
            self.assertEqual(self.run_sleep(enter), 2)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.rpc, ['sleep_prepare', 'sleep_restore'])
        self.assertFalse(self.ctx.json(pm.GUARD)['pending'])

    def test_active_owner_refuses_but_dead_owner_and_leftover_file_do_not(self):
        lease = self.ctx.path('/run/y2/activity.lock')
        child = subprocess.Popen([sys.executable, '-c',
            'import fcntl,sys,time; f=open(sys.argv[1],"w"); fcntl.flock(f,fcntl.LOCK_SH); '
            'print("held",flush=True); time.sleep(60)', str(lease)], stdout=subprocess.PIPE, text=True)
        self.addCleanup(child.stdout.close)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'held')
            self.assertEqual(self.run_sleep(lambda ctx: self.fail('entered with live owner')), 2)
            self.assertEqual(self.ctx.json('/data/system/platform/suspend-last.json')['product']['reason'], 'activity_operation')
        finally:
            child.terminate()
            child.wait(timeout=5)
        self.assertTrue(lease.exists())
        self.assertEqual(self.run_sleep(lambda ctx: self.returned()), 0)

    def test_kernel_fault_quarantines_same_image_and_new_image_retries(self):
        def broken(ctx):
            raise OSError('failed after kernel entry')
        self.assertEqual(self.run_sleep(broken), 1)
        self.assertTrue(self.ctx.json(pm.GUARD)['pending'])
        self.assertEqual(self.ctx.read('/sys/firmware/y2_pm/backstop_s'), '0')
        # A regular fixture file records the write; real sysfs reads status.
        self.write('/sys/firmware/y2_pm/backstop_s', 'provider=1 armed_s=0 running=0')
        with self.assertRaisesRegex(pm.Refused, 'sleep_recovery_required'):
            pm.admission(self.ctx)
        self.write('/etc/y2linux/versions.json', '{"build_git_commit":"next-source"}')
        pm.admission(self.ctx)

    def test_old_kernel_and_tainted_diagnostic_cannot_enable_product_sleep(self):
        self.write('/proc/sys/kernel/tainted', '4096')
        with self.assertRaisesRegex(pm.Refused, 'kernel_sleep_unavailable'):
            pm.admission(self.ctx)
        self.write('/sys/bus/platform/devices/10006000.power-controller/state', 'broken=0')
        with self.assertRaisesRegex(pm.Refused, 'physical_qualification_required'):
            pm.admission(self.ctx)

    def test_active_wakeup_count_read_is_bounded_without_periodic_polling(self):
        path = self.ctx.path('/sys/power/wakeup_count')
        path.unlink()
        os.mkfifo(path)
        holder = os.open(path, os.O_RDWR | os.O_NONBLOCK)
        try:
            with self.assertRaisesRegex(pm.Refused, 'wake_event_in_progress'):
                pm.wakeup_count(self.ctx, timeout=.02)
        finally:
            os.close(holder)

    def test_workload_expiry_and_mandatory_operation_exclusion(self):
        self.write('/sys/module/workload/parameters/leases', 'Maintenance remaining_ms=3000 min_khz=598000')
        with self.assertRaisesRegex(pm.Refused, 'workload_Maintenance'):
            pm.operation_state(self.ctx)
        self.write('/sys/module/workload/parameters/leases', 'Maintenance remaining_ms=0 min_khz=0')
        pm.operation_state(self.ctx)
        @workload('Maintenance')
        def work(ctx):
            return 'completed'
        with pm.operation_locks(self.ctx):
            with self.assertRaisesRegex(ValueError, 'sleep_operation_in_progress'):
                work(self.ctx)
        self.assertEqual(work(self.ctx), 'completed')

    def test_pending_update_low_voltage_and_usb_each_prevent_entry(self):
        for path, value, reason in (
                ('/sys/class/power_supply/BAT0/voltage_now', '3590000', 'battery_reserve'),
                ('/sys/class/power_supply/y2-usb-presence/online', '1', 'charger_or_usb_active'),
                ('/data/updates/state.json', '{"schema":1,"state":"Queued"}', 'firmware_update')):
            old = self.ctx.read(path)
            self.write(path, value)
            self.assertEqual(self.run_sleep(lambda ctx: self.fail('unsafe entry')), 2)
            self.assertEqual(self.ctx.json('/data/system/platform/suspend-last.json')['product']['reason'], reason)
            if old is None:
                self.ctx.path(path).unlink()
            else:
                self.write(path, old)


if __name__ == '__main__':
    unittest.main()
