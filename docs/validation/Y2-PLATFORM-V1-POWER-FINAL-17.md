# POWER-FINAL-17 — modem request gate and screen-first wake

Status: **SEALED, AWAITING THE OWNER FLASH** (2026-10-13). Package `out/y2linux-platform-v1-power-final-candidate-17/`
(fallback = 16), receipts `out/deep-sleep-final/build17-receipts/`. BOOTIMG
`2ddd8d384cf6d9336d1a3505944f6a787764e982f7327400b5e886a41ea52d9a`, Y2ROOT
`dc1f057a6c1d5768cbe3822893b5f71d3c3615bfbb3848e78491d9f0882a3e76`. Flash BOOTIMG + ANDROID only with
`MT6582_preserve_data_scatter.txt`, Download Only. Identity: build `Y2LINUX-PLATFORM-V1-POWER-FINAL-17`, kernel
`6.18.56-y2linux-platform-v1-power-final-17`, root `2026.08-platform-v1.47`, release
`1.0.0-platform-v1-power-final-candidate.17`; Linux `0459116` on `main` (later: a test-only commit), Reborn unchanged (`217e28d`). Base: Baseline 16
([16 report](Y2-PLATFORM-V1-POWER-FINAL-16.md)). Scope audit: "POWER-FINAL-17 sleep-floor and wake-latency scope audit"
in the [roadmap gap audit](../planning/roadmap-gap-audit.md).

Goal set by the owner: stock sleep parity, ≈0.1 points/h (≈1.3 mA), with deep suspend and resume working every time,
and a faster wake (screen first, radios afterwards). 16's first night drew ≈8.6 mA.

## What 17 changes

| Area | Change | Switch |
| --- | --- | --- |
| Modem (MD1) clock requests | The never-used modem's 26 peripheral clock requests are gated (PERICFG MD1_SET 0x20, readback MD1_STA 0x30) once the UI is up, and re-checked at every sleep entry. Stock golden has them all gated; 16 read 0 at all 33 sleep entries. Proven AP-writable and harmless by the live test on 16 ([ledger](../knowledge/stock-suspend-re-ledger.md) F11). Main suspect for INFRA never powering down. | `md1_gate` |
| Wake order | After a wake by the owner, the sleep helper asks Reborn to light the screen first and restores Wi-Fi and Bluetooth afterwards. On 16 the screen waited ≈1.9 s for the radios' firmware and calibration (archive 110: SPM return 217.92 s, screen ≈220.45 s). Expected: screen ≈1 s after Power. | — (a failed early restore is retried at completion, as before) |
| From 16's follow-ups (`d1953fa`) | The MMSYS part of the stock DCM now reaches the image; the USB DMA-unmask readback uses bits 15..8 (no more false `dma_unmask_lost`). | — |

`md1_gate` lives in `/data/system/platform/power-features.json` with the 16 switches, e.g. `{"md1_gate": false}`;
the SPM `state` shows `md1_gate=1 md1_result=0 md1_sta=0x3ffffff md1_regates=N`.

## Tests

Locked-container production suite: 682 cases, exit 0 (16: 676; new: MD1 gate policy/wiring/switch, wake order, early
restore reuse). The overlay-hash test added after 16 failed on its first container run because the container's `/src`
already carries the overlays (the kernel was fine: it contains the 0011 MMSYS DCM hook); the test now reverses each
patch first (`ebdfcf8`). Package validation, ELF closure (354 files), installed ARM (40 modules), privacy and inventory
PASS.

## What to check after the flash

1. `cat /sys/devices/platform/10006000.power-controller/state`: `md1_gate=1 md1_result=0 md1_sta=0x3ffffff`; USB,
   Wi-Fi, Bluetooth, charger and audio as on 16.
2. Wake: press Power after a sleep and judge the time to the screen; read `restoring_radios` vs the DSI modeset in
   `dmesg` (screen now before the radios).
3. After one sleep: `golden` row `PERI_PDN0_MD1_STA` now matches (`e=3ffffff 1`), and `y2_infra/state` `last_lost`
   (non-zero = INFRA finally powers down).
4. Overnight drain against 16's ≈8.6 mA.
