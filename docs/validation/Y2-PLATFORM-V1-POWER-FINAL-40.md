# POWER-FINAL-40 — handover snapshot for the restart display defect

Status: **SEALED, awaiting the owner flash** (2026-10-15). Package `out/y2linux-platform-v1-power-final-candidate-40/`
(fallback = 39), receipts `out/deep-sleep-final/build40-receipts/`. BOOTIMG
`bc44a93d183ea980a4755eef95f0b935dbd491a86084eda1d87c93870d68d503`, Y2ROOT
`37198d908a7e3fc99265e227f596993dfd2e2ed9b543cfd64e42d900cfd6392d`, RECOVERY
`ad06315e34500c6a33d90f8d6e81867d5c03409a12cdec57c2d6fac8de16d1f6`. Kernel `6.18.56-y2linux-platform-v1-power-final-40`,
release `…candidate.40`, update sequence 4000. Container suite **718 OK**, all seal checks PASS. Diagnostic only;
contains 39.

## Why

After a software restart SMI larb0 reads busy (39, archives 137/138), also when the display was stopped before
the restart. Unknown: is larb0 already busy when Linux takes over LK's pipeline, or does our handover wedge it?

| Change | Detail |
| --- | --- |
| Handover snapshots | `/sys/kernel/debug/y2_display_snapshot` slots 2 (`handover`, DSI probe before Linux touches LK's live pipeline) and 3 (`parked`), first probe of the boot only; larb0 0x400–0x4fc added. |
| Log | `handoff: snapshot …` and `handoff: parked …` with larb0 stat/greq, OVL status, OVL RDMA0, RDMA irq. |

## Owner steps

1. Flash 40 (BOOTIMG + ANDROID). Cold start: the agent saves the snapshots.
2. With the owner's OK: one software restart; the panel will likely stay dark. The agent saves the snapshots, then
   the owner holds Power 10 s. Diff cold/warm at `handover` and `parked`.
