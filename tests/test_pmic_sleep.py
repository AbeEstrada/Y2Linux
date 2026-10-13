"""POWER-FINAL-18: stock MT6323 suspend fields with exact restore.

Registers start at 17's real sleep-entry values (archive 112, boot de37f6bc,
pmic_golden): 0x102=0x8043, 0x108=0x03bf, 0x10e=0, 0x70c=0x1c32, 0x776=0,
0x778=0. Field names: ledger F15/F16.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

from test_power import run_c

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / 'kernel/platform'
sys.path.insert(0, str(ROOT / 'tools/platform'))


class PmicSleep(unittest.TestCase):
    def test_apply_reaches_stock_and_restore_is_exact(self):
        run_c(r'''
#include <assert.h>
#include <errno.h>
#include <string.h>
#include "pmic-sleep-policy.h"
#include "pmic-golden-policy.h"
#include "policy.h"
struct reg { unsigned reg, value; };
static struct reg regs[] = { {0x102, 0x8043}, {0x108, 0x03bf}, {0x10e, 0}, {0x70c, 0x1c32}, {0x776, 0}, {0x778, 0} };
#define N (sizeof regs / sizeof regs[0])
static unsigned writes, fail_reg, stuck_reg;
static struct reg *find(unsigned r) { for (unsigned i = 0; i < N; i++) if (regs[i].reg == r) return &regs[i]; return 0; }
static int rd(void *c, unsigned r, unsigned *v) { (void)c; struct reg *p = find(r); assert(p); *v = p->value; return 0; }
static int upd(void *c, unsigned r, unsigned m, unsigned v) {
 (void)c; struct reg *p = find(r); assert(p);
 /* Every write must pass the production PMIC write policy. */
 assert(!(m & ~y2_pmic_write_mask(r)));
 assert(y2_pmic_value_allowed(r, (p->value & ~m) | (v & m)));
 if (r == fail_reg) return -ETIMEDOUT;
 writes++;
 if (r != stuck_reg) p->value = (p->value & ~m) | (v & m);
 return 0;
}
static int golden(unsigned r) {
 for (unsigned i = 0; i < Y2_PMIC_GOLDEN_ROWS; i++)
  if (y2_pmic_golden[i].reg == r) return (find(r)->value & y2_pmic_golden[i].mask) == y2_pmic_golden[i].golden;
 assert(0); return 0;
}
int main(void) {
 struct reg saved[N]; memcpy(saved, regs, sizeof regs);
 struct y2_ps_io io = { 0, rd, upd };
 struct y2_ps_state s;
 assert(!y2_ps_apply(&io, Y2_PS_ALL, &s));
 /* Every touched row now matches the stock suspend golden. */
 assert(golden(0x102) && golden(0x10e) && golden(0x776) && golden(0x778));
 /* 0x108: only accdet (bit 9) still differs; Linux gates it, stock does not. */
 assert(((find(0x108)->value ^ 0x15ff) & 0xffff) == 0x200);
 assert(!(find(0x70c)->value & 0x10));                       /* adacck off */
 assert(find(0x70c)->value == 0x1c22);                       /* nothing else in 0x70c */
 assert(!y2_ps_restore(&io, &s) && !s.changed);
 assert(!memcmp(saved, regs, sizeof regs));                  /* bit-exact */
 /* Group 1 only: audio clocks, nothing else. */
 assert(!y2_ps_apply(&io, Y2_PS_AUDIO, &s));
 assert(!(find(0x102)->value & 1) && !(find(0x70c)->value & 0x10) && find(0x108)->value == 0x03bf);
 assert(find(0x776)->value == 0);
 assert(!y2_ps_restore(&io, &s)); assert(!memcmp(saved, regs, sizeof regs));
 /* Fields already at stock are not written. */
 find(0x776)->value = 0x8000; find(0x778)->value = 0x8000; writes = 0;
 assert(!y2_ps_apply(&io, Y2_PS_VREF, &s) && !writes && !s.changed);
 find(0x776)->value = 0; find(0x778)->value = 0;
 /* A failed write undoes everything already written. */
 fail_reg = 0x10e;
 assert(y2_ps_apply(&io, Y2_PS_ALL, &s) == -ETIMEDOUT && !s.changed);
 assert(!memcmp(saved, regs, sizeof regs));
 /* A readback that does not follow is refused and undone. */
 fail_reg = 0; stuck_reg = 0x776;
 assert(y2_ps_apply(&io, Y2_PS_ALL, &s) == -EIO);
 assert(!memcmp(saved, regs, sizeof regs));
 /* Group 0: nothing written. */
 stuck_reg = 0; writes = 0;
 assert(!y2_ps_apply(&io, 0, &s) && !writes);
 /* VEMC_3V3 enable stays closed: the root eMMC is retained across suspend. */
 assert(!(y2_pmic_write_mask(0x508) & 0x4000));
 return 0;
}
''')

    def test_wiring_order_and_switch(self):
        spm = (PLATFORM / 'spm.c').read_text()
        enter = spm[spm.index('static int y2_spm_enter('):spm.index('int y2_spm_dormant_idle(')]
        # Apply after the VPROC step, capture after both, restore before VPROC.
        self.assertLess(enter.index('y2_pmic_vproc_sleep_begin();'), enter.index('y2_pmic_sleep_begin();'))
        self.assertLess(enter.index('y2_pmic_sleep_begin();'), enter.index('y2_pmic_golden_capture();'))
        self.assertLess(enter.index('y2_pmic_golden_capture();'), enter.index('y2_spm_suspend_arm('))
        self.assertLess(enter.index('y2_pmic_sleep_end();'), enter.index('y2_pmic_vproc_sleep_end();'))
        pwrap = (PLATFORM / 'pwrap.c').read_text()
        self.assertIn('module_param_named(pmic_sleep, pmic_sleep_groups, uint, 0644);', pwrap)
        self.assertIn('static unsigned pmic_sleep_groups;', pwrap)   # kernel default off
        diagnostics = (ROOT / 'tools/platform/y2_platform/sleep_diagnostics.py').read_text()
        self.assertIn("'pmic_sleep_state'", diagnostics)

    def test_userspace_arms_all_groups_with_owner_override(self):
        from y2_platform.common import Context
        from y2_platform.power_features import apply
        with tempfile.TemporaryDirectory() as temp:
            ctx = Context(temp)
            param = ctx.path('/sys/module/pwrap/parameters/pmic_sleep')
            param.parent.mkdir(parents=True)
            param.write_text('0')
            self.assertEqual(apply(ctx)['pmic_sleep']['wanted'], 7)
            self.assertEqual(param.read_text(), '7')
            override = ctx.path('/data/system/platform/power-features.json')
            override.parent.mkdir(parents=True)
            override.write_text(json.dumps({'pmic_sleep': 1}))
            apply(ctx)
            self.assertEqual(param.read_text(), '1')
            override.write_text(json.dumps({'pmic_sleep': 8}))
            self.assertIn('error', apply(ctx)['pmic_sleep'])


if __name__ == '__main__':
    unittest.main()
