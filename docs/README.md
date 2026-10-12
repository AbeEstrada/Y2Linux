# Y2Linux documentation

**Baseline 15 (2026-10-12)** is the current published state: the POWER-FINAL-15
image (13's stock suspend power parity, 14's persistent sleep diagnostics, every
component on its newest release, Linux 6.18.56) that runs on the maintainer's Y2.
Git tag `baseline-15` in both repositories.

**POWER-FINAL-16 (2026-10-12)** is the newest image, on `main` of Y2Linux: stock
sleep parity from the Y2's own stock kernel (display power domain, stock clock
gating, golden sleep entry, stock fuel gauge, USB-after-wake and charging fixes).
Installed on the maintainer's Y2; its overnight drain test is running. See the
[16 report](validation/Y2-PLATFORM-V1-POWER-FINAL-16.md) and the
[stock suspend ledger](knowledge/stock-suspend-re-ledger.md).

| Need | Start here |
| --- | --- |
| Build it yourself | [BUILDING.md](BUILDING.md) |
| Flash it, connect, update, go back to stock | [INSTALL.md](INSTALL.md) |
| What works, what doesn't, latest hardware results | [Current platform state](CURRENT_PLATFORM_STATE.md) |
| What 16, 15, 14 and 13 changed | [16 stock sleep parity](validation/Y2-PLATFORM-V1-POWER-FINAL-16.md), [15 dependency update](validation/Y2-PLATFORM-V1-POWER-FINAL-15.md), [14 diagnostics](validation/Y2-PLATFORM-V1-POWER-FINAL-14.md), [13 stock power parity](validation/Y2-PLATFORM-V1-POWER-FINAL-13.md) |
| Deep sleep history (01 to 13) | [Deep-sleep report](validation/Y2-PLATFORM-V1-DEEP-SLEEP-FINAL.md), [suspend architecture](architecture/deep-suspend.md) |
| Charging, storage | [Charging policy](knowledge/charging-current-policy.md), [internal storage](knowledge/internal-storage.md) |
| Platform API and ownership | [Platform API](architecture/platform-api-v1.md), [power contract](architecture/platform-power-v1.md) |
| Partition layout and recovery | [Partitions](architecture/production-partitions.json), [install runbook](architecture/production-install.md), [recovery runbook](architecture/production-recovery.md) |
| Build inputs and source delivery | [Locked environment](build/environment.md), [reconstruction](build/platform-v1-reconstruction.md), [source delivery](release/Y2-COMMUNITY-SOURCE-DELIVERY.md) |
| Roadmap and open work | [Roadmap](planning/platform-v1-roadmap.md), [scope audits](planning/roadmap-gap-audit.md), [maintainer handoff](planning/NEXT-SESSION-HANDOFF.md) |
| The player | [Y2Reborn](https://github.com/SchulzCode/Y2Reborn) ([current state](https://github.com/SchulzCode/Y2Reborn/blob/main/docs/CURRENT_REBORN_STATE.md)) |
| Every page | [Complete catalog](DOCUMENTATION_CATALOG.md), [knowledge rules](KNOWLEDGE_BASE.md) |

Most pages under `build/`, `validation/`, `hardware-evidence/` and `release/` are
dated records of a specific candidate. Their "current", "next" and permission
statements belong to that date. Paths like `out/...` in them refer to the
maintainer's local build outputs and are not part of the repository.


## Historical navigation snapshot

The following text retains earlier dated decisions and results. Its “current”,
“next” and candidate labels belong to those sessions; the Baseline02 summary
above takes precedence. Historical failures and seal-time NOT_RUN receipts
remain evidence for their exact images.

---

# Y2Linux documentation

Start with the [complete community beta audit](release/Y2-COMMUNITY-BETA-FEATURE-AUDIT.md) and [selective RC1 plan](release/Y2-COMMUNITY-BETA-PLAN.md). They reconcile current source, sealed images and physical evidence at the2026-10-02 snapshot. The latest broad hardware report is [CPU Final Fix02 qualification](validation/Y2-CPU-FINAL-FIX02-PHYSICAL-QUALIFICATION.md); newer storage observations are narrower and do not establish whole-system acceptance.

| Need | Start here |
| --- | --- |
| Latest facts, limits and next batch | [Current state](CURRENT_PLATFORM_STATE.md) |
| What happened on the device | [Fix02 physical result](validation/Y2-CPU-FINAL-FIX02-PHYSICAL-QUALIFICATION.md) |
| Current observed capabilities | [Capability ledger](validation/Y2-HARDWARE-FINAL-CAPABILITIES.md) |
| Exact candidate/fallback identities | [Candidate index](knowledge/candidate-index.md) |
| CPU source/software provenance | [Fix01 implementation](validation/Y2-CPU-FINAL-FIX01.md), [sources](validation/Y2-CPU-FINAL-FIX01-SOURCES.md) |
| API and subsystem ownership | [Platform API](architecture/platform-api-v1.md), [contract catalog](DOCUMENTATION_CATALOG.md#architecture) |
| Power/hardware acceptance gates | [Hardware gates](knowledge/platform-v1-hardware-gates.md) |
| Next scope and decisions | [Roadmap](planning/platform-v1-roadmap.md), [standing audit](planning/roadmap-gap-audit.md#standing-milestone-boundary-rule) |
| Rebuild a recorded source pair | [Reconstruction](build/platform-v1-reconstruction.md) |
| Application state | [Reborn current state](https://github.com/SchulzCode/Y2Reborn/blob/main/docs/CURRENT_REBORN_STATE.md) |
| Every retained document | [Complete catalog](DOCUMENTATION_CATALOG.md) |
| How this knowledge base stays truthful | [Knowledge rules](KNOWLEDGE_BASE.md) |

## Reading older material

Historical validation, deployment, source research and hardware captures are
retained at their original paths. Their "current", "next" and authorization
statements apply to the recorded session. They do not override the current
state or authorize another flash/test. The
[catalog](DOCUMENTATION_CATALOG.md) labels records by scope; pages outside raw
evidence carry corresponding notices. Original captures/checksums are unchanged.

The prior [CPU Final physical run](validation/Y2-CPU-FINAL-PHYSICAL-QUALIFICATION.md)
is Fix01's before-state. Hardware Final and Platform v1 completion describe
earlier software boundaries, not the currently tested pair. The
[September 23 entry review](CURRENT_PLATFORM_STATE.entry-2026-09-23.md),
[old issue specifications](planning/issues/),
[build receipts](build/evidence/) and [hardware evidence](hardware-evidence/)
preserve provenance and narrow successes/failures. Original boot, stock ROM,
partition and source research remains under [knowledge/](knowledge/).

Earlier removed rolling handoffs remain available in
[Git history](https://github.com/SchulzCode/Y2Linux/tree/89230dd3add8f1fbbe7511d392f768a5db3305c0/docs/planning).
This cleanup changes navigation and summaries, not candidate bytes, acceptance
flags, reserved memory, firmware, keys or owner data.
