# POWER-FINAL-20 — reclaim the never-initialised UART1 clock

Status: **SEALED, AWAITING THE OWNER FLASH** (2026-10-13). Package `out/y2linux-platform-v1-power-final-candidate-20/`
(fallback = 19), receipts `out/deep-sleep-final/build20-receipts/`. BOOTIMG
`1ffdb4a2d024cf2d1c8554c518b859b2e7fe8a56186aefea4f8cbb35e4e93c55`, Y2ROOT
`98ffdca9c2595f245c0ad94b25c9e89c99796f2234324fbd22c994c046859548`. Identity: build `Y2LINUX-PLATFORM-V1-POWER-FINAL-20`,
kernel `6.18.56-y2linux-platform-v1-power-final-20`, root `2026.08-platform-v1.50`, release
`1.0.0-platform-v1-power-final-candidate.20`; Linux `c853915` on `main`, Reborn unchanged (`217e28d`). Flash BOOTIMG +
ANDROID only with `MT6582_preserve_data_scatter.txt`, Download Only. Scope audit: "POWER-FINAL-20 UART1 clock reclaim
scope audit" in the [roadmap gap audit](../planning/roadmap-gap-audit.md).

## Why

After 19 every INFRA clock gate matches stock at sleep entry and INFRA still stays powered (archive 116). The last
peripheral gate that differs is PERI_PDN0 bit 17, UART1: stock gates it in every scenario checklist (idle, deep idle,
suspend). UART1 has no Linux owner. 19's boot handoff showed `UART1 lcr=0 ier=0 lsr=0x0 dma=0
reason=tx_not_drained retained=1`: an all-zero, never-initialised UART was taken for an undrained transmitter, so
its clock stayed on from the bootloader for the whole uptime (UART2/3 read the idle 0x60 and were gated).

## What 20 changes

- `y2_unused_uart_never_initialised()` (`idle-clock-policy.h`): an all-zero LCR/IER/DMA/LSR set is not busy; the CCF
  unused-clock handoff reclaims UART1 at boot like UART2/3. Any non-zero field keeps the previous rule.
  `clocks.unused_handoff` reports `reason=never_initialised retained=0`.
- Every UART1 register read in the kernel was already conditional on its clock being on.
- Expected side effect: the deep-idle UART owner check no longer sees an unknown UART1.

## Tests

Locked-container production suite: 689 cases, exit 0 (the new assertions extend `test_cpu_idle_completion`).
Package validation, ELF, installed ARM, privacy and inventory PASS.

## What to check after the flash

1. Boot, display, audio, radios, USB; `cat /sys/module/clocks/parameters/unused_handoff` shows UART1
   `reason=never_initialised retained=0`; PERI_PDN0 bit 17 set (`golden` row `PERI_PDN0_STA` now matching).
2. A ~35-min sleep: golden SoC differences down by one; **`y2_infra/state last_lost`**.
3. The overnight drain against 16's ≈8.6 mA (first night for 17–20 together).
