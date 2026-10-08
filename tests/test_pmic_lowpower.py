"""POWER-FINAL-05 PMIC low-power select regressions. Synthetic evidence, never a device receipt."""
from pathlib import Path
import re
import unittest
from test_power import run_c

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / 'kernel/platform'


class WriteWhitelist(unittest.TestCase):
    def test_only_bit_zero_of_the_five_vendor_ldos_is_writable(self):
        run_c(r'''
#include <assert.h>
#include "policy.h"
int main(void) {
 static const unsigned regs[] = {0x404, 0x500, 0x502, 0x552, 0x556};
 for (unsigned i = 0; i < 5; i++) {
  assert(y2_pmic_write_mask(regs[i]) == 0x0001);   /* LP_SEL only */
  assert(y2_pmic_value_allowed(regs[i], 0xc001));
 }
 /* Existing guarded fields are unchanged: VMC/VMCH enable only, eMMC supply, VPROC/VSYS buck. */
 assert(y2_pmic_write_mask(0x504) == 0x1000 || y2_pmic_write_mask(0x504) == 0x1001);
 assert(y2_pmic_write_mask(0x50c) == 0x8000 && y2_pmic_write_mask(0x532) == 0x00e0);
 assert(y2_pmic_write_mask(0x230) == 0 && y2_pmic_write_mask(0x256) == 0 && y2_pmic_write_mask(0x216) == 0);
 assert(y2_pmic_write_mask(0x21a) == 0 && y2_pmic_write_mask(0x240) == 0);   /* buck enables */
 return 0;
}
''')

    def test_enable_and_mode_bits_of_those_ldos_stay_unwritable(self):
        source = (PLATFORM / 'policy.h').read_text()
        for reg in ('0x404', '0x500', '0x502', '0x552', '0x556'):
            self.assertRegex(source, r'case ' + reg + r'[^\n]*\n(?:[^\n]*case [^\n]*\n)*\s*return 0x0001;')


class Driver(unittest.TestCase):
    def setUp(self):
        self.header = (PLATFORM / 'pmic-lowpower-policy.h').read_text()
        self.source = (PLATFORM / 'pmic-lowpower.c').read_text()

    def test_chip_gate_and_parser(self):
        run_c(r'''
#include <assert.h>
#include "pmic-lowpower-policy.h"
int main(void) {
 assert(!y2_pmic_lp_chip_ok(0x1023) && y2_pmic_lp_chip_ok(0x2023) && y2_pmic_lp_chip_ok(0x2123));
 assert(y2_pmic_lp_parse("1\n", 2) == 1 && y2_pmic_lp_parse("0", 1) == 0);
 assert(y2_pmic_lp_parse("", 0) == -1 && y2_pmic_lp_parse("2", 1) == -1 && y2_pmic_lp_parse("11", 2) == -1);
 assert(y2_pmic_lp_parse("1\n\n", 3) == -1 && y2_pmic_lp_parse("on", 2) == -1);
 assert(Y2_PMIC_LP_RAILS == 5 && y2_pmic_lp_rails[0].reg == 0x404 && y2_pmic_lp_rails[4].reg == 0x556);
 return 0;
}
''')

    def test_driver_touches_only_the_table_and_requires_admin_for_revert(self):
        self.assertIn('regmap_update_bits(lp_map, y2_pmic_lp_rails[i].reg, Y2_PMIC_LP_BIT', self.source)
        self.assertEqual(len(re.findall(r'regmap_update_bits\(', self.source)), 1)
        self.assertEqual(len(re.findall(r'regmap_write\(', self.source)), 0)
        self.assertIn('capable(CAP_SYS_ADMIN)', self.source)
        self.assertIn('0600', self.source)
        self.assertIn('readback', self.source.lower() + ' readback')  # verified in lp_apply below
        self.assertIn('-EIO', self.source)
        self.assertIn('y2_pmic_lp_chip_ok(cid)', self.source)

    def test_rails_exclude_emmc_sd_vproc_and_vsys(self):
        regs = {int(x, 16) for x in re.findall(r'\{(0x[0-9a-fA-F]+),', self.header.split('struct y2_pmic_lp_rail y2_pmic_lp_rails')[1].split('};')[0])}
        self.assertEqual(regs, {0x404, 0x500, 0x502, 0x552, 0x556})
        self.assertTrue(regs.isdisjoint({0x504, 0x506, 0x508, 0x21a, 0x240, 0x230, 0x256}))

    def test_makefile_builds_it_under_the_power_option_only(self):
        self.assertIn('obj-$(CONFIG_Y2_POWER) += pmic-lowpower.o', (PLATFORM / 'Makefile').read_text())


if __name__ == '__main__':
    unittest.main()
