# Y2Linux documentation

**Baseline 24 (2026-10-13)** is the current published state: the POWER-FINAL-24
image that runs on the maintainer's Y2, git tag `baseline-24` in both repositories.
Since Baseline 18: Reborn's **Cover Flow** for Albums and **Genres**
([23](validation/Y2-PLATFORM-V1-POWER-FINAL-23.md), smooth frame pacing in
[24](validation/Y2-PLATFORM-V1-POWER-FINAL-24.md)), no colour flash at start-up and a dark
screen at power-off ([21](validation/Y2-PLATFORM-V1-POWER-FINAL-21.md),
[22](validation/Y2-PLATFORM-V1-POWER-FINAL-22.md)), and the PMIC_WRAP and UART1 clocks gated like
stock ([19](validation/Y2-PLATFORM-V1-POWER-FINAL-19.md),
[20](validation/Y2-PLATFORM-V1-POWER-FINAL-20.md)). Baseline 18 set the power-management chip to its stock suspend values while asleep (the
audio 26 MHz clock request Linux never released, unused clocks, VREF18); see the
[18 report](validation/Y2-PLATFORM-V1-POWER-FINAL-18.md). Baseline 17 gated the never-used modem's clock requests and lights the screen about half a
second after Power (Wi-Fi/Bluetooth follow in the background); see the
[17 report](validation/Y2-PLATFORM-V1-POWER-FINAL-17.md). Baseline 16 added stock sleep parity from the Y2's own stock kernel (display power domain,
stock clock gating, golden sleep entry, stock fuel gauge, USB-after-wake and
charging fixes) to Baseline 15 (newest release of every component, Linux 6.18.56).
First night: 16 h of clean sleep at about 8.6 mA (stock: about 1.3 mA). See the
[16 report](validation/Y2-PLATFORM-V1-POWER-FINAL-16.md) and the
[stock suspend ledger](knowledge/stock-suspend-re-ledger.md).

| Need | Start here |
| --- | --- |
| Build it yourself | [BUILDING.md](BUILDING.md) |
| Flash it, connect, update, go back to stock | [INSTALL.md](INSTALL.md) |
| What works, what doesn't, latest hardware results | [Current platform state](CURRENT_PLATFORM_STATE.md) |
| What 24 back to 13 changed | [24 frame pacing](validation/Y2-PLATFORM-V1-POWER-FINAL-24.md), [23 Cover Flow and Genres](validation/Y2-PLATFORM-V1-POWER-FINAL-23.md), [22 dark DSI hand-over](validation/Y2-PLATFORM-V1-POWER-FINAL-22.md), [21 quiet display power](validation/Y2-PLATFORM-V1-POWER-FINAL-21.md), [20 UART1 clock](validation/Y2-PLATFORM-V1-POWER-FINAL-20.md), [19 PMIC_WRAP clock](validation/Y2-PLATFORM-V1-POWER-FINAL-19.md), [18 stock PMIC sleep settings](validation/Y2-PLATFORM-V1-POWER-FINAL-18.md), [17 modem gate and faster wake](validation/Y2-PLATFORM-V1-POWER-FINAL-17.md), [16 stock sleep parity](validation/Y2-PLATFORM-V1-POWER-FINAL-16.md), [15 dependency update](validation/Y2-PLATFORM-V1-POWER-FINAL-15.md), [14 diagnostics](validation/Y2-PLATFORM-V1-POWER-FINAL-14.md), [13 stock power parity](validation/Y2-PLATFORM-V1-POWER-FINAL-13.md) |
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
