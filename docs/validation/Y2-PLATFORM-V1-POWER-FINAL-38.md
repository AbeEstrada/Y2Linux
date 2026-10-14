# POWER-FINAL-38 — stock restart sequence (external reset)

Status: **SEALED, awaiting the owner** (2026-10-15). Package `out/y2linux-platform-v1-power-final-candidate-38/`
(fallback = 37), receipts `out/deep-sleep-final/build38-receipts/`. BOOTIMG
`aedd1c3ebbc2332dfd788cad2d918ee9be1a3ee23b5d9f12f942dd4f9cd575cf`, Y2ROOT
`91ec460bdacc3b94575fbf208fb7a0d0bfc121493c5a130fa787c10564962531`, RECOVERY
`a6d1de5fe888a82dcfd03b3a11716169f51e41b926afd054d8c7188e8413c482`. Kernel `6.18.56-y2linux-platform-v1-power-final-38`,
release `1.0.0-platform-v1-power-final-candidate.38`, update sequence 3800. Container suite **718 OK**, all seal checks
PASS. Signed OTA (release key): `out/y2linux-platform-v1-power-final-candidate-38-ota-release/`.

## Why

A software restart leaves the panel dark (since 11; archives 130/131 on 35). LK shows its logo and initialises the
display without a boot-reason branch (REA, FM `lk.bin` `platform_init` 0x81e004b8). The stock kernel's restart
(REA, FM kernel `wdt_arch_reset` 0xc0541d10) writes `WDT_MODE = (mode & 0xffffffa6) | 0x22000014` — external
reset to the PMIC and auto-restart — waits 2.5 ms, then `WDT_SWRST = 0x1209`. Upstream `mtk_wdt_restart` (ours)
only wrote `WDT_SWRST`, so display-path state survived and Linux got no frames after the logo.

| Change | Detail |
| --- | --- |
| Restart | `mtk_wdt_restart` on MT6582 uses the stock sequence (patch 0037). The suspend backstop watchdog is unchanged. |
| Updates | Restart instead of power-off only with the owner switch `/data/updates/restart.json` `{"mode": "reboot"}` (apply and recovery), until a restart is proven on the device. |
| Snapshot | 37's read-only display snapshot stays for a cold/warm diff if a restart still fails. |

## Owner steps

1. Install 38 (SP Flash Tool BOOTIMG + ANDROID, or over the air from 37 with the signed package).
2. With the owner's OK: one `y2-platform shutdown reboot`. Panel lit → restart fixed; then
   `restart.json` on, and an install test without pressing Power. Panel dark → hold Power 10 s; the agent diffs
   the snapshots (cold: archive 133).
