"""Counter discontinuities must not become fictitious power measurements."""
import importlib.machinery
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('power_audit', str(ROOT/'tools/platform/y2-power-audit'))
spec = importlib.util.spec_from_loader(loader.name, loader)
audit = importlib.util.module_from_spec(spec)
loader.exec_module(audit)


class Audit(unittest.TestCase):
    def samples(self):
        base = '/sys/devices/system/cpu/cpu0/cpuidle/state2'
        opp = '/sys/devices/system/cpu/cpufreq/policy0/stats/time_in_state'
        a = {'boot_id': 'one', 'threads': {'4:4:2': {'name': 'old', 'utime': 0, 'stime': 0, 'context_switches': {}}},
             'files': {'/proc/interrupts': 'CPU0 CPU1\n12: 100 50 timer\n', '/proc/stat': 'ctxt 100\n',
                       base+'/time': '1000000', base+'/usage': '4', base+'/name': 'DORMANT',
                       opp: '598000 50\n1300000 50\n'}}
        b = {'boot_id': 'one', 'threads': {'4:4:8': {'name': 'new', 'utime': 500, 'stime': 0, 'context_switches': {}}},
             'files': {'/proc/interrupts': 'CPU0\n12: 110 timer\n', '/proc/stat': 'ctxt 120\n',
                       base+'/time': '6000000', base+'/usage': '9', base+'/name': 'DORMANT',
                       opp: '598000 140\n1300000 60\n'}}
        return a, b

    def test_real_deltas_restart_and_offline_irq_counters(self):
        result = audit.delta(*self.samples(), 10)
        self.assertEqual(result['cpuidle'][0]['percent_wall_time'], 50)
        self.assertEqual(result['cpuidle'][0]['entries'], 5)
        self.assertEqual(result['cpu0_idle_exits_per_second'], .5)
        self.assertEqual(result['top_cpu_threads'], [])
        self.assertIsNone(result['irqs'][0]['per_second'])
        self.assertTrue(result['irqs'][0]['counter_discontinuity'])
        self.assertEqual(result['frequency_residency'][0]['percent_recorded_residency'], 90)
        self.assertEqual(result['scheduler']['ctxt']['per_second'], 2)
        self.assertIsNone(result['wakeups_per_second'])

    def test_cross_boot_refused(self):
        a, b = self.samples()
        b['boot_id'] = 'two'
        with self.assertRaises(ValueError):
            audit.delta(a, b, 10)
