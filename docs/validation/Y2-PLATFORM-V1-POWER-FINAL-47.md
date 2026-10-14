# POWER-FINAL-47 — DSI register read lag: keep DCM off for DSI/DPI

Status: **SEALED, not yet on the player** (2026-10-16). Package `out/y2linux-platform-v1-power-final-candidate-47/`
(fallback = 46, which the player runs), receipts `out/deep-sleep-final/build47-receipts/`. BOOTIMG
`97f2ef876bc78b140933204f504142830786f6ec9b4f65a2b5b08b632cf9e280`, Y2ROOT
`efb3f4e66f85ed8f200f4b292d1e1a2894bf462e04641748e27aff5a1df40bce`, RECOVERY
`4293cfcafa4d041bdfb89c6af5c9e3dbc57d24949a4b2ee9d3f25ac9deb2ce35`. Kernel `6.18.56-y2linux-platform-v1-power-final-47`,
update sequence 4700, Linux `ba7a003`, Reborn `850687d`. Container suite **718 OK**, all seal checks PASS. Signed
with the release key: `…-47-ota-release/`.

## Why

46's recovery log (archive `20261016/150`) narrows the lag to a 42 ms window: LK's DSI registers read correctly at the
hand-over (`ps=000305a0 vact=00000168`), every read lags at Linux's first modeset, and power-cycling DSI clocks and
PHY three times does not clear it. In that window the display mutex's first prepare applies MMSYS DCM, group 1 (DSI
engine/digital, DPI) included. Stock (`out/rea/fm-kernel.elf`) calls `dcm_enable` only from `mt_dcm_init` and the
sysfs store — once at boot, with its display streaming — and toggles only bus DCM around idle. All three lagged
boots (143, 43's recovery, 150) are after POWER-FINAL-16 introduced the DCM; the older dark restarts read correctly.

| Change | Detail |
| --- | --- |
| `dcm-policy.h` | DIS DCM group 1 stays off (`0x1400012c`/`0x14000130` = 0xf; the clear register is not written). Group 0 and SMI DCM unchanged. No power cost: the DSI streams whenever the screen is on; DIS is powered down when it is off. |
| DSI evidence (patch 0017) | Hand-over and read-back lines print `dcm1=` (0xf expected from 47 on). |
| `update probe-recovery` | Follows the restart setting: restart into the recovery screen and back, nothing installed. |

## Owner steps

1. Install 47 (owner's choice: GitHub pre-release over Wi-Fi, or staged over USB).
2. With the owner's OK: several `y2-platform update probe-recovery` runs (each restarts into the recovery screen
   and back); the agent archives each recovery log. Pass: every recovery screen lit, no `read-back` line.
3. Then publish/promote 47 as the latest release.
