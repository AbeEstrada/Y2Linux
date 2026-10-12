# POWER-FINAL-16 — stock sleep parity from the Y2's own stock kernel (REA)

Status: **INSTALLED, FIRST PHYSICAL CHECKS PASS, OVERNIGHT DRAIN RUNNING** (2026-10-12). Package
`out/y2linux-platform-v1-power-final-candidate-16/` (fallback = 15), receipts `out/deep-sleep-final/build16-receipts/`.
Identity: build `Y2LINUX-PLATFORM-V1-POWER-FINAL-16`, kernel `6.18.56-y2linux-platform-v1-power-final-16`, root
`2026.08-platform-v1.46`, release `1.0.0-platform-v1-power-final-candidate.16`; Linux `a4e9c3b` on `main` (later commits:
the two follow-ups below, tests and docs). Reborn unchanged (`f68e088`). BOOTIMG
`2f1cd1c0091e2015afa2af6ffbd2f191f58090d3cbdc3b52f58a71ef5d6edebf`, Y2ROOT
`bd4a12a07b39f21c9313d82069014891e1e1707ffee9eb532e04cece69a43d9f`.

Goal set by the owner: fix what was broken on 15 and reach the best possible deep sleep, stock parity of about
0.1 percentage points per hour (≈1 % per night, ≈1.3 mA on the stock 1300 mAh model). Every stock behaviour below
was read from the Y2's own stock kernel with REA/Ghidra; the evidence and addresses are in the
[stock suspend ledger](../knowledge/stock-suspend-re-ledger.md). Scope audit: "POWER-FINAL-16 stock sleep-parity
scope audit" in the [roadmap gap audit](../planning/roadmap-gap-audit.md).

## What 16 changes

| Area | Change | Switch |
| --- | --- | --- |
| Defect B (USB dead after every wake, 13–15) | The MUSB DMA completion unmask (MAC+0x200) is re-armed whenever the interrupt gate reopens (reconnect, restore); full 32-bit diagnostics (`dma_unmask_*` in the y2-usb `status`). | — |
| Defect C (no sleep, no charge on a powered-off PC) | A standard PC port charges at the stock 450 mA whatever the gadget negotiated; sleep is admitted with a cable when no host has configured the gadget and nothing charges. | — |
| Display (DIS) power domain | Off at screen-off and during sleep with the exact stock MTCMOS sequence (`spm_mtcmos_ctrl_disp`); OVL/RDMA and the MMSYS clock provider drive it; the GPU domain is its child. Armed only once the UI has drawn its first frame. | `dis_pdn` |
| Stock DCM | Hardware dynamic clock gating as stock `dcm_enable(0x1ff)`: CPU, TOPCKGEN, INFRA/bus, DRAMC and PERI at boot. | boot `spm.dcm=0` |
| Golden sleep entry | At sleep entry, with every device suspended: MMPLL/VENCPLL/MSDCPLL/UNIVPLL off (stock PLL ops), mux power-down bits, unused PERI/INFRA clock gates; restored bit-exactly at wake. Never: MAINPLL/ARMPLL, the AXI mux, the console UART mux, PMIC_WRAP. | `golden_apply` bitmask 1/2/4/8 |
| Diagnostics | Read-only PMIC golden comparison (44 stock rows) and MD-side peripheral requests at every sleep entry. | — |
| Fuel gauge | Stock 25 °C battery profile (95 rows, 4175 → 3400 mV), stock internal-resistance correction while charging, Q_MAX 1300 mAh. Percentages read higher than on 15 (3.8 V: 54 % instead of 45 %). | — |
| Small fixes | Python 3.15 lost early boot log lines (`/dev/kmsg` EINVAL); the power journal keeps more than a day (8 MiB files). | — |

Owner switches live in `/data/system/platform/power-features.json`, for example `{"dis_pdn": false, "golden_apply": 3}`;
they apply at the next start of the UI.

## Tests

Locked-container production suite: 676 cases, exit 0 (15: 664), including the busybox syntax check of the changed
init scripts. Package validation, ELF closure (354 files), installed ARM (40 modules), privacy and inventory PASS.
Host suite: no new failures against `main` (739 cases, same host-environment errors).

## Hardware results (2026-10-12, boot `0b0e8a77`)

- First boot healthy, reset cause none. Display: screen off/on 5 times without a problem; the display domain powered
  off and on 5/5 times with no failures after arming.
- Wi-Fi, Bluetooth, MTP, SSH and audio up.
- One unplugged sleep 15:32 → 16:08 (36 min, one maintenance wake), clean. **USB worked after the wake** — the first
  time since 13. The unmask register still read `0000ff00` after the wake (not lost), so the cause of the fix is not
  yet proven; more wakes are needed.
- Golden SoC rows differing at sleep entry: **26 → 11** (4 of the 11 are deliberate exceptions, see the ledger).
  PMIC golden: 15 of 44 rows differ (first capture). INFRA still never loses power (`last_lost=0x0`).
- The 36-min sleep gives no drain figure: it started right after charging, so the voltage relaxation dominates.
- Live MD1 test (owner-authorised probe module): the AP may write PERICFG MD1_SET/CLR (0x20/0x28); gating all 26
  modem-side requests leaves the AP untouched. 17 will gate them at boot.

## Found after the build (fixed in source for 17)

- The MMSYS part of the DCM never reached 16: kernel overlays are cached by their manifest result hash, and the
  edited 0011 patch kept the old hash. New test `test_overlay_hashes` re-applies every overlay.
- The DMA unmask readback is in bits 15..8, so 16's `dma_unmask_lost` counter is a false positive.

## Not verified

The overnight drain (running), Defect B over many wakes, long-term stability of the golden sleep entry.
