"""Execute the kernel's precision snapshot and retain its truthful API fields."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_audio import function

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/platform'))
from y2_platform.diagnostics import project


class PrecisionContract(unittest.TestCase):
    def test_idle_configured_and_running_driver_contract(self):
        source = (ROOT / 'kernel/audio/mt6582-afe.c').read_text()
        fixture = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <sys/types.h>
struct mt6582_afe { int lock; unsigned configured_rate; bool running; };
struct device { struct mt6582_afe *afe; };
struct device_attribute { int unused; };
static void *dev_get_drvdata(struct device *dev) { return dev->afe; }
#define spin_lock_irqsave(p,f) do { (void)(p); (f)=0; } while (0)
#define spin_unlock_irqrestore(p,f) do { (void)(p); (void)(f); } while (0)
#define sysfs_emit(buf,...) snprintf(buf,4096,__VA_ARGS__)
''' + function(source, 'pcm_contract_show') + r'''
int main(void) {
 struct mt6582_afe afe={0}; struct device dev={&afe}; char buf[4096];
 assert(pcm_contract_show(&dev,NULL,buf)>0); fputs(buf,stdout);
 afe.configured_rate=44100;
 assert(pcm_contract_show(&dev,NULL,buf)>0); fputs(buf,stdout);
 afe.configured_rate=48000; afe.running=true;
 assert(pcm_contract_show(&dev,NULL,buf)>0); fputs(buf,stdout);
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / 'contract.c').write_text(fixture)
            subprocess.run(['clang', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-Wno-unused-parameter', str(p / 'contract.c'),
                            '-o', str(p / 'contract')], check=True)
            rows = [json.loads(line) for line in subprocess.check_output(
                [str(p / 'contract')], text=True).splitlines()]
        self.assertEqual(rows[0]['current']['meaningful_bits'], 0)
        self.assertEqual(rows[0]['current']['alsa_format'], 'NONE')
        for row, rate, running in zip(rows, [0, 44100, 48000], [False, False, True]):
            self.assertEqual(row['current']['rate_hz'], rate)
            self.assertEqual(row['current']['running'], running)
            self.assertIsNone(row['hardware_max_meaningful_bits'])
            self.assertFalse(row['physical_bit_capture'])
            mode, = row['supported_modes']
            self.assertEqual((mode['container_bits'], mode['meaningful_bits'],
                              mode['i2s_slot_bits'], mode['i2s_payload_bits']),
                             (16, 16, 32, 16))
            self.assertIsNone(mode['afe_interconnect_physical_bits'])
            exported = project({'audio': {'pcm_contract': row}})['audio']['pcm_contract']
            self.assertEqual(exported['current'], row['current'])
            self.assertEqual(exported['supported_modes'], row['supported_modes'])
            self.assertEqual(exported['evidence'], 'driver_contract')


if __name__ == '__main__':
    unittest.main()
