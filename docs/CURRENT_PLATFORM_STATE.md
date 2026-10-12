# Current Y2Linux platform state

## POWER-FINAL-16 stock sleep parity installed — 2026-10-12 (latest)

`out/y2linux-platform-v1-power-final-candidate-16/` (Linux `a4e9c3b`, Reborn `f68e088` unchanged, root
`2026.08-platform-v1.46`; BOOTIMG `2f1cd1c0…debf`, Y2ROOT `bd4a12a0…3d9f`), fallback 15. Built from the Y2's own stock
kernel analysed with REA ([ledger](knowledge/stock-suspend-re-ledger.md)): USB-after-wake re-arm, stock 450 mA on any
PC port and sleep with an idle cable, display power domain off at screen-off and in sleep, stock DCM, golden sleep
entry (PLLs, muxes, unused clock gates, exact restore), read-only PMIC golden capture, stock fuel-gauge profile.
Offline: container suite 676, exit 0; package checks PASS. **Physical (boot `0b0e8a77`):** display off/on 5/5, Wi-Fi,
Bluetooth, MTP, SSH, audio up; one 36-min sleep clean and **USB worked after the wake** (first time since 13; cause not
yet proven); golden SoC differences 26 → 11, PMIC 15/44. Live test: the AP may gate the never-used modem's clock
requests (planned for 17). **Overnight drain: running.** Details: [16 report](validation/Y2-PLATFORM-V1-POWER-FINAL-16.md).
Readiness remains **MORE_WORK_REQUIRED**.

## POWER-FINAL-15 dependency-update candidate sealed — 2026-10-12

`out/y2linux-platform-v1-power-final-candidate-15/` (Linux `be1aac2`, Reborn `f68e088`, root `2026.08-platform-v1.45`;
BOOTIMG `86dc957a…844d`, Y2ROOT `0b14b794…20ae`) is 14 rebuilt on the newest release of every component:
Linux 6.18.56 (the owner kept the 6.18 line), Buildroot 2026.08, Bootlin GCC 15.3/glibc 2.44, Rust 1.99, Mesa
26.2.4, OpenSSL 4.0.3, Python 3.15.0 and the rest. Offline: container suite 664 cases, exit 0; package, ELF,
ARM, inventory and privacy checks PASS. **Not flashed; physical NOT_RUN.** The display (panel `prepare_prev_first`,
Mesa 26/Lima) needs checking first. Details: [15 report](validation/Y2-PLATFORM-V1-POWER-FINAL-15.md).
Readiness remains **MORE_WORK_REQUIRED**.

## POWER-FINAL-14 diagnostics candidate sealed — 2026-10-11

`out/y2linux-platform-v1-power-final-candidate-14/` (Linux `9d06ac4`, Reborn `63ac4a7` with code identical to 13, root
v1.44; BOOTIMG `273dc927…3e5a`, Y2ROOT `78203697…14b9`) is 13 plus persistent sleep and USB diagnostics:
`/data/system/platform/sleep-diagnostics.jsonl` rows at each suspend stage and around USB state changes, and the USB/network
snapshot in every power-journal row. **Not flashed; physical NOT_RUN.** Why: the USB-after-wake defect (Defect B)
recurred at 18:39 and 20:56 on 13. The only recovery is a hold-Power restart, which erased 13's in-memory counters.
Details: [14 report](validation/Y2-PLATFORM-V1-POWER-FINAL-14.md). Readiness remains **MORE_WORK_REQUIRED**.

## Baseline 13 (POWER-FINAL-13) installed and published — 2026-10-11

**Image:** build `Y2LINUX-PLATFORM-V1-POWER-FINAL-13`, kernel `6.18.0-y2linux-platform-v1-power-final-13`, root
`2025.02.18-platform-v1.43`, release `1.0.0-platform-v1-power-final-candidate.13`; compiled from Linux `47c1cf2` and
Reborn 0.3.0 `71ddb0d`. BOOTIMG `f73c24da…c178`, Y2ROOT `e62cb6c7…1915`. Git tag `baseline-13` (both repositories)
is this source plus the tests, the `package.py --stock` packaging fix and documentation. Build and install:
[BUILDING](BUILDING.md), [INSTALL](INSTALL.md).

**What 12 and 13 changed:** 12 made device suspend synchronous (the intermittent pre-SPM stall did not recur over a
5.5 h night, 34 suspends) and added a real charger "Full" state. 13 fixed the sleep guard that blocked all sleep
after a radio-quiesce race (Defect A). It also applied the stock firmware's suspend settings, taken from the Y2's own
stock kernel: VPROC 0.85 V while asleep, LP_SEL on VMC/VMCH/VEMC3V3, USB PHY save-current, click-wheel controller
sleep, and a 30-min maintenance wake. Each one can be switched off at run time. Details:
[13 report](validation/Y2-PLATFORM-V1-POWER-FINAL-13.md).

**Hardware results on 13 (2026-10-11):** first check healthy (taint 0, every new switch active). First unplugged
sleep: 15:17 to 18:39, 12,104 s suspended in 7 kernel suspends with 6 clean 1800 s maintenance wakes, Power-button
wake, restore result 0. Battery 76% to 76% (4.036 V to about 4.007 V) over 3.4 h. That is one short run, and the
percentage comes from voltage; 12's overnight drain was about 2.2 points/h. **USB networking failed after that wake:**
the gadget enumerated 5 s after the wake and the device reported it configured, but the host received 0 bytes for
3 min (same symptom as 12's "Defect B"; this time without a preceding sleep failure). Power off and on recovered it.
That restart lost the in-memory counters for the new features (VPROC, PHY, wheel, INFRA power-down, golden entry
capture), so the run does not show whether they worked as intended.

**Open, in priority order:** (1) USB traffic after a wake (Defect B). (2) Repeat the sleep test and read the new
counters and the `golden` capture at sleep entry, then an overnight drain. (3) A warm reboot leaves the panel dark
(`flip_done timed out`); use power off and on only. (4) Screen-off while awake keeps the display pipeline running
(about 4.9 points/h). (5) PLL/clock-gating parity at sleep entry, eMMC supply in suspend, VGP2/DAC rail, panel deep
standby. No current sensor exists, so no mA figure is claimed. Readiness: **MORE_WORK_REQUIRED** (developer preview).

## POWER-FINAL-11 remaining-screens candidate sealed — 2026-10-11

`out/y2linux-platform-v1-power-final-candidate-11/` (Linux build `5741d16`, Reborn 0.3.0 `abbb203`, root v1.41; BOOTIMG `1482316d…ee08`, Y2ROOT `4773d90d…d73c`) is 10 plus the computer, pairing, download, scanning and battery screens and a redrawn offline charging screen; **not flashed, physical NOT_RUN**.
The installed image is 10. Kernel and drivers unchanged; the rescue charger's decision logic is untouched (display only). Details: [validation](validation/Y2-PLATFORM-V1-POWER-FINAL-11-SCREENS.md), [scope audit](planning/roadmap-gap-audit.md). Readiness remains **MORE_WORK_REQUIRED**.

## POWER-FINAL-10 Reborn UI v3 candidate sealed — 2026-10-10

`out/y2linux-platform-v1-power-final-candidate-10/` (Linux build `04aa8f9`, Reborn 0.3.0 `f31c94c`, root v1.40; BOOTIMG `9d1f00a5…0ca`, Y2ROOT `77a41a33…16`) is 09 plus the redesigned Reborn UI, startup screen and shutdown animation; **not flashed, physical NOT_RUN**.
The installed image is 09. Kernel, drivers and partitions are unchanged. Details: [validation](validation/Y2-PLATFORM-V1-POWER-FINAL-10-UI.md), [scope audit](planning/roadmap-gap-audit.md), Reborn `docs/ui/REBORN-PRODUCT-UI-V3.md`. Readiness remains **MORE_WORK_REQUIRED**.

## POWER-FINAL-08 cumulative candidate sealed — 2026-10-10

`out/y2linux-platform-v1-power-final-candidate-08/` (Linux `d9fd5a7`, Reborn `ac5502e`, root v1.38; BOOTIMG `ad39788a…efb1`, Y2ROOT `e79bac96…c71a`) is the one image containing 06 (deep-sleep power-down bring-up), 07 (charging policy)
and 08 (internal storage). **Not flashed; physical NOT_RUN.** The installed image is 06. 08 turns the stock FAT partition into ext4 Y2Media (`/media/internal`), exports it as MTP Internal Storage and adds explicit SD `format`/`grow`; the one-time
provisioning runs only after the owner flashes. Details: [storage](knowledge/internal-storage.md), [policy](knowledge/charging-current-policy.md), [handoff](planning/NEXT-SESSION-HANDOFF.md). Readiness remains **MORE_WORK_REQUIRED**.

## POWER-FINAL-07 charging candidate sealed — 2026-10-10

`out/y2linux-platform-v1-power-final-candidate-07/` (Linux `551baad`, Reborn `97ff8c3` unchanged, root v1.37; BOOTIMG `65a1daf4…a3001`, Y2ROOT `83a61c1e…e66`) is 06 plus the full vendor charging policy and is built and offline-qualified;
**it is not flashed (physical NOT_RUN)**. The installed image is 06 (healthy at first check, power-down cycle still to run). The stock 16-step `CS_VTH` table and per-source requests (DCP/nonstandard 1100, Apple 800, CDP 650, SDP 450) are
implemented behind one decision function with PMIC-die derating; the default ceiling stays 650 mA and nonstandard stays 70 mA because no cell charge rating, pack temperature or independent current measurement exists.
Details: [policy](knowledge/charging-current-policy.md), [validation](validation/Y2-PLATFORM-V1-POWER-FINAL-07-CHARGING.md) (on branch `codex/platform-v1-power-final-07`), [handoff](planning/NEXT-SESSION-HANDOFF.md). Readiness remains **MORE_WORK_REQUIRED**.

## POWER-FINAL-06 bring-up candidate sealed — 2026-10-09

`out/y2linux-platform-v1-power-final-candidate-06/` (Linux `c1ef37a`, Reborn `97ff8c3` unchanged, root v1.36; BOOTIMG `64a91628…7869f`, Y2ROOT `e1c0bcd3…c23e4be`) is built and
offline-qualified; **it is not flashed (physical NOT_RUN) and not production**. Correction: Y2Linux already ran the vendor 597-word `pcm_suspend`; the 05 report's "480-word dpidle" was the runtime-idle line. The real
difference from stock is `infra_pdn=0`; 06 enables the vendor `infra_pdn=1` (INFRASYS/DDRPHY power-down) with a verified PERICFG restore, an automatic retained-mode fallback and a boot-to-boot guard. The 05
overnight defects are addressed: the MUSB L1 interrupt guard no longer storms on an unowned PHY level bit, and a terminal USB stop parks the controller instead of unregistering it (the Wi-Fi-time Oops was a dangling
`usb0` parent, not `wlan0`). A 9 h idle capture of 05 (archive 89) showed 95.6% in SPM sleep with no recurrence (single run). Next: owner flashes 06, read-only check, first power-down cycle, repeated cycles, overnight drain
vs. 05's about 2.1 points/h (voltage-derived); production cleanup only after hardware qualification. Details: [handoff](planning/NEXT-SESSION-HANDOFF.md). Readiness remains **MORE_WORK_REQUIRED**.

## POWER-FINAL-05 overnight result — 2026-10-09

The first overnight unplugged run on 05 (archive 88, same boot `3cae62f2`, taint 0) suspended **38,052 s of 38,235 s (99.5%)** across 64 cycles and 63 600 s maintenance wakes, 88%→66% (voltage-derived, about 2.1
points/h, indicative only, no current sensor). It also exposed two **new defects**: (1) a terminal `Y2USB IRQ overflow` at 01:34 CEST with no cable, after which USB did not enumerate or charge until reboot, and (2) a kernel
NULL-dereference Oops (`rtnl_fill_ifinfo`; later shown to be the `usb0` netdev's dangling parent after the 01:34 terminal USB stop, not `wlan0`) at the first Wi-Fi restore after the Power-button wake, followed by `kernel_sleep_unavailable` refusals (link unverified). Nothing was
changed on the device by that analysis; the fixes are in 06. Details: [handoff](planning/NEXT-SESSION-HANDOFF.md), [data](validation/data/y2-power05-overnight-20261009.json). Readiness remains **MORE_WORK_REQUIRED**.

## POWER-FINAL-05 installed — 2026-10-08

The owner flashed POWER-FINAL-05 (Linux `837b614`, Reborn `97ff8c3`, root v1.35; BOOTIMG `0137a855…44117`, Y2ROOT `9175185f…99a4d`). It is DEEPSLEEP-FINAL-04 plus the vendor MT6323 `LP_SEL` low-power
select on five always-on LDOs (VA, VIO28, VUSB, VM, VIO18) with a root runtime revert at `/sys/firmware/y2_pmic/lp_sel`. Installed and probed: same boot, taint 0, 1573 s asleep with two maintenance wakes,
SPM 3/3, vendor golden-table differences at suspend entry 22→17. **No battery or current benefit is claimed** (no current sensor, unknown capacity, voltage-derived SOC). Overnight drain, Power/RTC wake and early-boot
on 05 are next. Details: [handoff](planning/NEXT-SESSION-HANDOFF.md), [report §40](validation/Y2-PLATFORM-V1-DEEP-SLEEP-FINAL.md#40-power-final-05-suspend-power-campaign-2026-10-08). Readiness remains **MORE_WORK_REQUIRED**.

## DEEPSLEEP-FINAL-04 installed — 2026-10-08

The owner flashed the diagnostic successor DEEPSLEEP-FINAL-04 (Linux `5e26757`, Reborn `97ff8c3`, root v1.34, BOOTIMG
`4738de48…ace5f6`, Y2ROOT `b0e66751…c041`). It differs from 03 only by retained per-device `WAIT`/`LOCK` records and a built-in
device-phase stall sampler. Normal automatic suspend then ran cleanly on the first owner trial (469 s) and a one-hour unplugged trial
(3805 s suspended, six maintenance wakes, SPM 9/9 entries/resumes, taint 0, ext4 errors 0). This does **not** resolve the intermittent
pre-SPM stall (nine clean entries; timing perturbation possible). Next: owner reboot with an early unplug, then an overnight drain
test. Readiness remains **MORE_WORK_REQUIRED**. See the [handoff](planning/NEXT-SESSION-HANDOFF.md) and
[report §39](validation/Y2-PLATFORM-V1-DEEP-SLEEP-FINAL.md#39-diagnostic-successor-04--analysis-build-and-physical-trials-2026-10-08).

## DEEPSLEEP-FINAL-03 late analysis — 2026-10-08

Local analysis of archives65/66 against the exact03 suspend code finds the device-phase
failure stops in a step the retained callback ring cannot record, about half a
minute before the reset (consistent with the 30 s backstop). A diagnostic
successor source (per-device `WAIT`/`LOCK` records and a built-in stall sampler)
is prepared and unit/cross-compile tested but **not built, flashed or run**. The
installed image, the pending recovery guard and all evidence are unchanged. See the
[handoff](planning/NEXT-SESSION-HANDOFF.md). Readiness remains **MORE_WORK_REQUIRED**.

## DEEPSLEEP-FINAL-03 evening follow-up — 2026-10-08

Archive67 shows an orderly user-requested poweroff around09:55:39 CEST after
the morning inspection, then a new03 boot about16 seconds later. Its retained guard still
prevents full suspend (SPM0/0,421 refusals before USB return). The current
boot's provisional journal estimate fell57%→32% across roughly seven hours
unplugged; the 17:00 connected reading is Charging31% with no reported charger
fault. Exact03 hashes and basic application/filesystem health remain sound.
The earlier pre-SPM failure is unresolved. See the
[handoff](planning/NEXT-SESSION-HANDOFF.md) and
[audit](planning/roadmap-gap-audit.md#clean-corrective-image-physical-admission).
Readiness remains **MORE_WORK_REQUIRED**.

## DEEPSLEEP-FINAL-03 morning observation — 2026-10-08

Current installed image is DEEPSLEEP-FINAL-03, Linux `cfb7e09` / Reborn `97ff8c3`,
rootv1.33. The owner reports about88%→55% over approximately six unplugged hours
and no manual restart. Archived logs confirm a failed automatic suspend attempt
on boot0132fb21, retained DPM_PREPARED/seq8, and an unclean reboot to81dce40c.
The new boot records no full-system suspend and380 recovery-guard refusals.
Runtime CPU0 DORMANT did run; it does not qualify whole-system sleep.

Morning read-only SSH confirms the same03 files, taint0, responsive/paused player,
closed PCM, no scan, radios off, ext4 errors/warnings0 and fault-free charging.
Pre-cable55% is preserved separately from connected samples. Exact reset cause
and battery capacity/current remain unknown. The pending03 guard is preserved;
no new trial, deployment or flash occurred. **MORE_WORK_REQUIRED**; the recurring
device-phase suspend failure precedes further endurance acceptance. See the
[current handoff](planning/NEXT-SESSION-HANDOFF.md),
[overnight report](validation/Y2-PLATFORM-V1-DEEP-SLEEP-FINAL.md#32-overnight-result--2026-10-08)
and [audit](planning/roadmap-gap-audit.md#clean-corrective-image-physical-admission).
The dated entries below retain historical states.

## USB02 power investigation / POWER01 owner installation next — 2026-10-05

The actually installed pair is USB-FINAL-02 Linux `0cb7792` / Reborn `2444e0f`,
root v1.26, not the older baseline identities below. Last night's recorded
3.400268 V orderly shutdown is real; the owner's 88% UI and retained maximum
3.920141 V/full=0 do not prove a full starting pack. No system sleep occurred.
Current recovery boot `e043cb75…` has DRM WARN/taint512, frozen display and safe
C3 quarantine. A 30-minute PC window gains 3.881469→3.937500 V at the validated
450 mA configured ceiling/fault0; C2 85.7193%, C3 zero. Original components and
saved Wi-Fi state are restored; MTP/ECM Ready. Battery capacity/health/current/NTC
remain unproven.

One source-bound preserving POWER-FINAL-01 candidate is software validated:
Linux `fedc005ba68b3f5020a45258e38d641aa191b12a` / Reborn
`ccf450ac1388228dbd859318a05e13adf667c9aa`, kernel
`6.18.0-y2linux-platform-v1-power-final-01`, root v1.27. It corrects runtime PCM
PMIC slots, charging C3 admission, first display takeover and measured polling,
and adds a bounded power/idle journal. Canonical location:
`out/y2linux-platform-v1-power-final-candidate/`. BOOTIMG/ANDROID only; DATA is
preserved. No flash/push/main merge has occurred. Full suspend, warning-free
new-image idle, near-full charge and endurance remain open: **MORE_WORK_REQUIRED**.
See [the final power report](validation/Y2-PLATFORM-V1-POWER-BATTERY-FINAL.md),
[machine windows](validation/data/y2-platform-v1-power-final.json) and
[handoff audit](planning/roadmap-gap-audit.md#power-candidate-owner-handoff--2026-10-05).
Resume this investigation immediately after the owner confirms installation.

## Baseline01 physical gate interrupted / USB diagnosis pending — 2026-10-04

Exact installed Baseline01 Linux `98daf3f` / Reborn `9cd12bae`, kernel baseline-01
and root v1.24 passes original machine/owner smoke on boot `ef2c8f2f…`, taint 0.
All-four-core C1, 18 hotplug transitions, five OPP/voltage readbacks and natural
parking/C2 pass; C2 has 4,857 entries and 85.4572% residency in 60.05534 seconds,
zero restore faults. Eight scratch hash rounds each on DATA/SD after C2 pass.
The owner restarted after an overlong deliberate USB-off C3 topology wait;
C3 has no recorded armed/entered cycle and remains unqualified, not a proven
C3 crash. Recovered boot `9d4d0245…` logs a DRM WARNING; automatic C3 correctly
reports Skipped. Earlier post-flash USB disconnects remain independently open.
Host ECM static-IP/autoconnect matching is corrected and saved; the host harness
now keeps USB attached during parking and bounds its offline window to 180 s.
Thirty affected host tests pass; installed firmware/images are unchanged.
The owner prioritizes the separate wired-audio session holding the shared lock;
USB diagnosis waits for its completion. No further CPU/transfer/suspend stress.
Full Power and RTC wake remain separately NOT_RUN, historical Baseline02 RTC FAIL
stays open, and endurance/electrical/distribution gates remain unqualified.
See [the physical receipt](validation/Y2-PLATFORM-V1-BASELINE-PHYSICAL.md).
All 233 feature identities are retained; sealed package metadata remains its
seal-time record. No main merge, push, flash or public/physical promotion.

## Newest independent Platform 1.0 baseline — 2026-10-04

`Y2LINUX-PLATFORM-V1-BASELINE-01`: compiled Linux `98daf3f0220f4a1580bb4893094ee9f0e02362a5` / Reborn `9cd12baeeb70b204e08299bd4c91c8c35604c304`;
root `2025.02.18-platform-v1.24`, kernel `6.18.0-y2linux-platform-v1-baseline-01`.
SOFTWARE_VALIDATED / INTEGRATED_PHYSICAL_NOT_RUN; owner-local physical qualification
ready, public distribution not ready. Baseline02 RTC FAIL remains open; UART01
CPU evidence/fallback is historical. Owner main and earlier candidates preserved.
Canonical candidate `/home/luca/Dokumente/Code/Y2Linux/out/y2linux-platform-v1-baseline-candidate`. Details in `docs/release/Y2-PLATFORM-V1-BASELINE.md`.
Older current/next labels below belong to their recorded observation times.

## Integrated Platform 1.0 software candidate — 2026-10-04

**READY_FOR_PLATFORM_V1_PHYSICAL_QUALIFICATION**. All eleven source handoffs are
composed on paired codex/platform-v1-integration branches. One sealed candidate:
`/home/luca/Dokumente/Code/worktrees/platform-v1-integration/Y2Linux/out/y2linux-platform-v1-integration-candidate`. Compiled Linux `4c72466f2f27ddf9f0ca18ba8ddc4d89c52599d2` / Reborn `dd73dcc3243045cd33e319dda2f76918ed37ea31`; kernel `6.18.0-y2linux-platform-v1-integration-01`, root `2025.02.18-platform-v1.23`.
Broad source/kernel/ARM/QEMU/ELF/package/privacy/source checks PASS; integrated
hardware/endurance NOT_RUN and public distribution blocked. See the [master](release/Y2-PLATFORM-V1-MASTER.md),
[233-feature matrix](release/Y2-COMMUNITY-BETA-FEATURES.json) and [one physical plan](release/Y2-PLATFORM-V1-PHYSICAL-QUALIFICATION.md).

Latest owner-installed receipts remain Baseline02 Linux8584ccd8/Rebornb71b4688,
boot88b85fa3/taint0 after a failed full RTC trial. Temporary optimized binaries
were restored to stock. UART01 remains the protected bounded CPU-idle authority.
No new integrated image has run on hardware. Older dated sections below retain
their original scope; a documentation HEAD is separate from compiled identity.


## Parallel integration observation — 2026-10-04

[Master status](release/Y2-PLATFORM-V1-MASTER.md): **INTEGRATION_IN_PROGRESS**.
All eleven source-frozen handoffs are composed on isolated paired master branches; no final
Platform 1.0 integration candidate exists. New Bluetooth/Wi-Fi owner receipts
identify installed Baseline02 (Linux `8584ccd8`, Reborn `b71b4688`, root v1.21,
boot `27e6d684-3794-4490-95db-a489027cd4f4`, taint 0). Their locations and
limitations are recorded in the [live inventory](release/Y2-PLATFORM-V1-INTEGRATION-STATUS.md).
This supersedes the older awaiting-installation identity below; it does not
qualify automatic cold-boot C3 or the changed subsystem binaries. UART01 remains
the exact-image physical authority for bounded C1/C2/C3. The dated Baseline02
seal and historical evidence remain intact. No master device access occurred.

Later owner RTC full-sleep evidence on the same installed Baseline02 is **FAIL**:
watchdog recovery changes boot `27e6d684` to
`88b85fa3-2282-4d93-b0b8-818a105ddd0a`, taint 0; retained journal stops at
DEVICES_RESUMING (wake 0x20, full PCM 596, reset stamp 0x59325253), with no
complete/exit proof. Direct scratch hashes and zero ext4 counters after reboot
prove recovery only. New suspend source was not installed. Preserve prior
UART01 C1/C2/C3 evidence; full resume and automatic C3 remain separate gates.
Master archives the raw failure receipts offline and neither repeats the trial
nor closes any milestone. Review the source-bound owner handoff before integration.
2026-10-04 [wired precision source/evidence update](validation/Y2-PLATFORM-V1-HIGHRES-AUDIO.md):
locked read-only access now observes installed Baseline02 Linux8584ccd8 /
Rebornb71b4688, boot27e6d684-3794-4490-95db-a489027cd4f4, taint0. This supersedes
the earlier installed-image identity below, while UART01 remains the retained
CPU hardware qualification. No new cold-boot/CPU qualification follows from the
identity read. Native wired admission remains S16_LE stereo44100/48000,
16 meaningful bits in32-bit slots; the MT6582 silicon maximum is unresolved.
Precision diagnostics/quantization/fixtures are validated in isolated worktrees,
not installed; fresh playback and CPU costs are NOT_RUN due to device-lock
contention. No flash, push, merge or hardware milestone closure.

Updated 2026-10-03 from the sealed Baseline02 receipts and retained UART01
hardware evidence. This synchronization changes documentation only; it does
not build, flash, push or run a new physical qualification.

## Retained Baseline02 seal and installed evidence

| Field | Sealed Baseline02 |
| --- | --- |
| Build | `Y2LINUX-BASELINE-02` |
| Candidate | `out/y2linux-baseline-02-candidate/` |
| Kernel | `6.18.0-y2linux-baseline-02` |
| Rootfs / release | `2025.02.18-platform-v1.21` / `1.0.0-baseline-candidate.2` |
| Compiled Linux | `8584ccd85f052f351fe51650b2348c83ca894ed4` |
| Compiled Reborn | `b71b468860233faa0a42b8448ec5777fa952b8e3` |
| ABI / feature contract / layout / data | 1 / 2 / 1 / 1 |
| Software / package | PASS |
| New-image hardware / automatic cold boot | PHYSICAL_NOT_RUN |

The protected bounded CPU-idle hardware receipt is **UART01**, kernel
`6.18.0-y2linux-cpu-c3-uart-01`, Linux `e9e8d63f9c94232c2b6627881e0967583e202dac`,
Reborn `b71b468860233faa0a42b8448ec5777fa952b8e3`, root
`2025.02.18-platform-v1.20`, boot
`fd955840-35d9-47db-83e0-ff47d6bb2d2b`, taint 0.
C1, C2 and C3 are physically working on that image. Baseline02 retains that
kernel architecture; its new image and automatic cold-boot activation remain
**PHYSICAL_NOT_RUN** until owner installation and the guarded checks.

See the [sealed receipt](validation/Y2-BASELINE-02.md),
[exact candidate and fallback identities](knowledge/candidate-index.md) and
[authoritative hardware report](validation/Y2-CPU-C3-UART-PHYSICAL.md).
Compiled source identity comes from the manifest; a later documentation HEAD
or published branch tip does not identify the installed kernel/rootfs.

## CPU hardware results carried forward

| Behavior | Exact UART01 bounded result |
| --- | --- |
| C1 WFI | All four CPUs enabled; entry/residency advance; rejected 0; 400 bounded wakes |
| C2 SLIDLE | +6,971 entries; 50.654676 s / 60.054881 s = 84.3473%; clock restore failures 0 |
| C3 DORMANT | 21 guarded reset-and-return trials, then +3,624 entries; 39.204662 s / 60.088344 s = 65.2450% |
| Final C3 accounting | 3,647 entries = resumes = successes = UART ACKs; timer/context/CIRQ/clock restore failures 0 |
| Core parking | Natural CPU0-only topology; owned mask 0xe; both secondary power status copies 0 |
| Hotplug | 18 supported transitions; park 3→2→1, restore 1→2→3 |
| Timers | GPT6, GPT4 sole broadcast, 13 MHz CNTFRQ, PPI29 on all cores, highres and NO_HZ pass |
| DVFS | 598 / 747.5 / 1040 / 1196 / 1300 MHz guarded readback before and after C3 passes |
| Storage | eMMC and inserted SD: eight fsynced checksum rounds each after C2 and after C3; ext4 errors 0 |
| Wake and I/O | Workload/screen demand restore, real FFmpeg/ALSA playback, bounded USB transfer and independent Wi-Fi observer pass |

UART1's retained clock is handled by the exact MT6582 UART sleep request/ACK
contract and Linux UART ownership. It is no longer an unresolved C3 blocker.
No forced UART peripheral gate or weakened admission guard was used.

## Baseline02 boot policy

Baseline02 enables qualified **CPU0 C3 automatically after boot** through
`S05y2-cpu-idle`. The kernel initially registers C3 disabled with budget 0.
The once-per-boot service checks identity, taint and static SPM/CIRQ/timer/context
foundations, sets budget -1, enables CPU0 state2 and reads both controls back.
Failures roll back; CPU1–3 C3 remains disabled. Dynamic topology, frequency,
screen/workload/radio/USB, clock/domain, future-deadline, UART ACK and restore
fault guards remain intact. The service does not force parking or gate UART1.

`y2-platform cpu-idle-policy stop` disables C3 for the current boot and prevents
another start from overriding that choice. Recovery boot options
`y2.deep_idle=off` and `y2.cpu_safe=1` retain the safe fallback. Runtime C3 is
separate from full system suspend.

## Software validation and release limits

Fresh kernel/config/DT/module/ABI, Buildroot ARM and Reborn ARM checks pass.
The integrated suite has **391 cases: 386 passed and 5 dependency skips**;
27 native filesystem/GIO and 3 ALSA checks plus installed ARM checks cover the
missing minimal-environment dependencies. All **125 focused source tests** and
**238 Reborn tests**, formatting/lint, Cortex-A7 QEMU, installed ARM applications,
ELF/dependencies and preserving-package checks pass. These are retained build
receipts, not tests rerun by this documentation update.

Full system suspend with same-boot Power/RTC wake remains open. This pass does
not qualify additional CIRQ edge injection, long endurance, electrical battery
savings, native 24-bit/high-rate wired output, optional Bluetooth peer/codec
behavior, USB host/VBUS, a calibrated battery gauge or public binary distribution.
All five guarded active OPPs remain available; a C3 entry cap of 747.5 MHz does
not lower the active CPU ceiling.

Source/license collection passed with recorded collector limitations. The
package remains owner-local; successful collection is not redistribution
permission or a byte-identical rebuild demonstration. The
[community feature audit](release/Y2-COMMUNITY-BETA-FEATURE-AUDIT.md) retains
233 features and the separate unresolved release gates.

## Next owner boundary

Verify the sealed package and use `MT6582_preserve_data_scatter.txt` in
Download Only mode, selecting **BOOTIMG and ANDROID/Y2ROOT only**. Preserve
USRDATA/Y2DATA and every protected partition. After owner installation, the
packaged SSH harness verifies exact identity and real cold-boot activation,
quarantines C3 for foundation tests, runs one guarded C3 trial plus 20 cycles,
and checks normal runtime, wake and I/O regressions. No installation is inferred
from the user's earlier confirmation for UART01.


## Historical snapshots

The following text retains earlier dated decisions and results. Its “current”,
“next” and candidate labels belong to those sessions; the Baseline02 summary
above takes precedence. Historical failures and seal-time NOT_RUN receipts
remain evidence for their exact images.

---

# Current Y2Linux platform state

## Baseline02 sealed precedence — 2026-10-03

New latest-source preserving candidate is sealed at `out/y2linux-baseline-02-candidate/`:
Linux`8584ccd85f052f351fe51650b2348c83ca894ed4`, Reborn`b71b468860233faa0a42b8448ec5777fa952b8e3`,
kernel6.18.0-y2linux-baseline-02/rootv1.21. Fresh build,391 production cases,
source/native/Reborn/ARM/QEMU/ELF/config/DT/ABI/package checks pass. Owner-selected
automatic qualified CPU0 C3 boot policy is included; all existing guards remain.
Only BOOTIMG/Y2ROOT; preserve Y2DATA and protected partitions. New-image hardware/
cold-boot qualification NOT_RUN. Installed UART01 still proves C1/C2/C3 working,
3647 real C3 returns, same boot/taint0 and zero restore failures. Earlier summaries
below are historical. See [sealed baseline record](validation/Y2-BASELINE-02.md).
No flash or push; owner installation is the next boundary.

## Baseline02 preparation precedence — 2026-10-03

Installed UART01 is physically qualified for C1/C2/C3 on Linuxe9e8d63/Rebornb71b4688,
with3647 real C3 returns and clean restores, same boot/taint0. Earlier summaries
below are historical. Owner requests a latest integrated Baseline02 preserving
candidate and selects automatic qualified C3 boot policy. Source tests/live ARM
control transaction pass; fresh build/seal and new-image physical checks are
separate boundaries. See [Baseline02](validation/Y2-BASELINE-02.md) and
[UART01 hardware](validation/Y2-CPU-C3-UART-PHYSICAL.md).

## Current audit precedence — 2026-10-02

The [community beta master audit](release/Y2-COMMUNITY-BETA-FEATURE-AUDIT.md) now reconciles source, builds and hardware across both repositories; the [RC1 plan](release/Y2-COMMUNITY-BETA-PLAN.md) defines the shortest proposed beta path. At its17:49:54 CEST cutoff: Linux `dcbd7d1` candidate4 source/build activity, Reborn `b92d312`; latest sealed/reported installed candidate3, with narrow SD characterization in a concurrently edited draft; latest broad physical report remains Fix02. The exact baseline and conflicting older “unflashed” text are documented there. Earlier summaries below are historical and must not override that baseline. No hardware acceptance is created by this documentation update.

Updated 2026-09-29 from the **CPU Final Fix02 physical qualification**. This
documentation update made no source repair, build or flash.

**Working development baseline; FAIL for normal CPU-platform acceptance.**
The awake CPU platform is substantially qualified: timers, QoS, MMC runtime
gating, automatic parking and 1196/1300-MHz voltage DVFS pass. Remaining gates
are full-suspend resume completion, the SLIDLE bus-DCM predicate and loaded
USB upload. The [Fix02 physical report](validation/Y2-CPU-FINAL-FIX02-PHYSICAL-QUALIFICATION.md)
is authoritative for actual behavior, ahead of software receipts.

**Storage ceiling candidate 2, 2026-10-01 (the candidate to flash):**
`out/y2linux-storage-ceiling-02-candidate/`, Linux `4db6d6de`, kernel
`6.18.0-y2linux-storage-ceiling-02`, BOOTIMG `5c17f744…`, Y2ROOT `dc611011…`.
Candidate 1 booted: eMMC ran HS200 cleanly (~133 MB/s read), but no SD card
initialised because the PMIC write gate refused the SD rail writes.
Candidate 2 admits exactly those fields. SD at the ceiling is not yet
observed on hardware.

**Storage ceiling candidate 1, 2026-10-01 (superseded):** `out/y2linux-storage-ceiling-candidate/` is the Product
UI v2 candidate plus the storage hardware ceiling pass. eMMC goes from 50 MHz
HS52 to **HS200** (8-bit, 200 MHz, fixed 1.8 V VIO18 IO, CMD21 tuning). SD goes
from 50 MHz SD HS at 3.3 V to **UHS-I up to SDR104** (4-bit, 200 MHz, MT6323
VMC 3.3→1.8 V switch, CMD19 tuning). Both have automatic fallback ladders and
readback verification. Linux `540ae029`, Reborn `b92d312c`, kernel
`6.18.0-y2linux-storage-ceiling`, root `2025.02.18-platform-v1.11`, BOOTIMG
`4332d4f2…`, Y2ROOT `72eab34a…`. Software-validated; **not flashed or
physically qualified; no mode above 50 MHz has run on a Y2 yet**. See the
[storage ceiling record](validation/Y2-STORAGE-CEILING.md).

**Product candidate, 2026-10-01 (superseded by the storage ceiling candidate):**
`out/y2linux-reborn-product-ui-v2-candidate/` is the Fix03 platform (same
kernel) plus Reborn Product UI v2, a Reborn-mark splash and a platform
backlight-off step before power-down. Linux `5cfe04cb`, Reborn `bd8436dd`,
root `2025.02.18-platform-v1.10`, BOOTIMG `8a974cb5…`, Y2ROOT `a5c2914e…`.
Software-validated; **not flashed or physically qualified**. See the
[Product UI v2 receipt](validation/Y2-REBORN-PRODUCT-UI-V2.md).

**Software candidate, 2026-10-01:** one CPU Final Fix03 preserving candidate
(Linux `76a5d41d`, Reborn `77cf83e0`, BOOTIMG `c55b2640…`, Y2ROOT `04cafd4b…`)
is built and software-validated, but **not flashed or physically qualified**.
It reconciles the SLIDLE bus-DCM baseline and makes the USB storm guard
progress-aware. It fixes wake escalation, SD identity and the DVFS label, and
instruments the resume window so the next RTC attempt names the stalled call.
See the [Fix03 receipt](validation/Y2-CPU-FINAL-FIX03.md). The Fix02 result
below remains the latest observed hardware state.

## Latest physically observed identity

| Field | Exact identity, observed 2026-09-29 |
| --- | --- |
| Linux compiled source | `1a1a6693dcd82f62daecd4c1491ef512823a86c5` |
| Reborn compiled source | `77cf83e09a18f82a867040e72d35b6e70b26fa85` |
| Kernel | `6.18.0-y2linux-cpu-final-fix02` |
| Rootfs | `2025.02.18-platform-v1.8` |
| Release / build | `1.0.0-cpu-final-fix02-candidate.1` / `Y2LINUX-CPU-FINAL-FIX02` |
| Final boot | `6bb70fad-29a7-4a8e-a1a1-b69884434127` |

Later documentation HEADs are not compiled source identities. The report retains
all four boot IDs and the retained-journal capture. No fresh device observation
is implied by the date of a documentation commit.

## Physical coverage

| Area | Status | Observed scope |
| --- | --- | --- |
| GPT6/GPT4/PPI29, highres/NO_HZ | PASS | 13-MHz CNTFRQ all CPUs, sole GPT4 broadcast, PPI29 on CPU0–3, ~1.09-ms 1-ms sleeps |
| Hotplug, schedutil, workload QoS, thermal override | PASS | eight classes, real input/playback/scan/transfer/maintenance producers, screen-off interaction release |
| C1 WFI | PASS | entries/residency advance, rejected 0 |
| MMC runtime clock gating | PASS | eMMC/SD gated at rest, CCF counts 0, 16/16 hash rounds, no errors or mismatches |
| C2 SLIDLE | FAIL | clock mask 0 with radios off, but TOPCKGEN+4 reads `0x0`, not the required `0x0f` |
| Automatic parking / restore | PASS | 3→2→1 at 5-s pacing, display restore 0.63 s; wake counted as pressure restore |
| High OPP / voltage DVFS | PASS | PWRAP `0x7f` ready; 1196 @ 1.20 V, 1300 @ 1.25 V readback; sampled ordering; integrity 0 errors |
| C3 / CIRQ deadline handoff | NOT_TESTED | preflight unmet: topology, frequency, domains, clocks, bus |
| SRAM journal | PASS | awake self-test; warm-reboot retention; valid records after backstop reset |
| Charger refusal / staged PM | PASS | active-charging `-EBUSY` clean unwind; freezer/devices/platform/processors/core same boot |
| Full RTC suspend | FAIL | SPM return and resume vector proven; reset by 30-s backstop after device resume, before PM exit |
| Power wake / RTC cycles / restoration | NOT_TESTED | no same-boot full resume |
| USB loaded transfer | FAIL | 0/10; EP1 RX DMA channel 5 IRQ storm, twice, UI alive, Wi-Fi-observed |
| Wi-Fi / CONSYS | PASS, bounded | 4 × 1-MiB SHA roundtrips; radio restore after quiesce |
| SD media lifecycle | FAIL (non-CPU) | kernfs inode/ctime inventory remounts `/media/sd` after reclaim |

Screen-off idle, parked: 2.71 % of four cores (Fix01 9.74 %), 171 IRQ/s (391),
355 context switches/s (504). This is a CPU idle improvement, not a measured
battery improvement. Owner actions: USB unplug and reconnect only.

## Enabled software and unfinished qualification

- S16 stereo 44.1/48 output is enabled. Native S24/S32/preserved 24-bit and
  88.2/96-kHz output remain gated; decoding high-rate sources is separate.
- Optional AAC/aptX/aptX-HD/LDAC encoders are included in the private experiment
  build. Normal runtime disables their endpoints; SBC is baseline and Auto
  retains qualification/distribution gates. Fix01 peer audio is NOT_TESTED.
- Schema-2 low-voltage policy is enabled and provisional: critical/warning/
  recovery 3.4/3.5/3.6 V. Estimated SOC is not measured current, coulomb count
  or calibrated capacity. Pack thermal and discharge/reserve/full-cycle charging
  acceptance remain open. See the [power contract](architecture/platform-power-v1.md).
- Automatic deep sleep, C3 promotion, AP watchdog recovery, USB host/VBUS/UAC
  and NCM activation remain unqualified/gated. Screen-off is not system sleep.
- Root-only OTA/recovery/maintenance software exists; production trust,
  distribution/provisioning, recovery/endurance and byte-identical image
  reproducibility remain separate gates. Automatic BOOTIMG OTA is excluded.

The [capability ledger](validation/Y2-HARDWARE-FINAL-CAPABILITIES.md) separates
latest observations from historical build flags. Runtime status determines
actual admission/faults. [Hardware gates](knowledge/platform-v1-hardware-gates.md)
and [Reborn state](https://github.com/SchulzCode/Y2Reborn/blob/main/docs/CURRENT_REBORN_STATE.md) retain other limits.

## Next smallest correction boundary

**CPU Final Fix03 is an implemented, unflashed candidate.** The owner's single
Fix03 run (prepared in [Fix03 physical qualification](validation/Y2-CPU-FINAL-FIX03-PHYSICAL-QUALIFICATION.md))
checks the regression gate, SLIDLE with radios off, USB 10 × 1 MiB, then
RTC → Power → 5 cycles. If resume still stalls, the timed ring names the one
call to correct next. The Fix02 EP1 "IRQ storm" was legitimate throughput
tripping the guard, not a re-arm defect. Preserve all Fix02 physical passes. Do not
bypass guards or restart CPU architecture. The
[roadmap](planning/platform-v1-roadmap.md) and
[standing audit](planning/roadmap-gap-audit.md#standing-milestone-boundary-rule)
govern implementation and acceptance; this page does not authorize new scope.

## Candidate, fallback and evidence

Latest candidate: `out/y2linux-cpu-final-fix02-candidate/`, already owner-flashed
before qualification. Preserve-data payload is BOOTIMG/Y2ROOT only. Exact
known-good fallback is **Hardware02**, kernel `6.18.0-y2linux-hardware-02` /
root `2025.02.18-platform-v1.4`. The [candidate index](knowledge/candidate-index.md)
holds full hashes and identity; [reconstruction](build/platform-v1-reconstruction.md)
uses the built pair rather than later docs HEADs.

Private evidence: `out/cpu-final-fix02-physical-qualification/20260929T152328Z/`,
460 sealed files (Fix01: `out/cpu-final-fix01-physical-qualification/20260927T205514Z/`). Raw secrets, firmware and calibration
are not published. [Documentation index](README.md), [catalog](DOCUMENTATION_CATALOG.md)
and [knowledge rules](KNOWLEDGE_BASE.md) identify current contracts versus history.
Older candidate/evidence reports preserve their original scope and failures.
